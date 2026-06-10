"""
Memory Agent -- Historisches Marktgedaechtnis
Speichert vergangene Nachrichten-Ereignisse und deren tatsaechliche
Marktauswirkungen in einer SQLite-Datenbank.

Mit jedem Tageslauf lernt das System:
  - Welche News-Typen welche Kursbewegungen ausgeloest haben
  - Welche Signalkombinationen historisch am zuverlaessigsten waren
  - Wie aehnliche Situationen in der Vergangenheit geendet haben

Die Datenbank waechst taeglich und macht alle Agenten praeziser.
"""

import sys
import os
import sqlite3
import json
import re
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass

import yfinance as yf

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

DB_PFAD = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "market_memory.db")


# ---------------------------------------------------------------------------
# Datenstrukturen
# ---------------------------------------------------------------------------

@dataclass
class HistorischesEreignis:
    datum: str
    asset: str
    schlagzeile: str
    news_sentiment: str          # bullish / bearish / neutral
    signal_typ: str              # z.B. "RSI_UEBERKAUFT", "MACD_KREUZUNG", etc.
    preis_bei_signal: float
    rendite_1d: float            # tatsaechliche Rendite nach 1 Tag
    rendite_5d: float            # tatsaechliche Rendite nach 5 Tagen
    rendite_10d: float           # tatsaechliche Rendite nach 10 Tagen
    signal_war_korrekt: bool     # hat das Signal die richtige Richtung gezeigt?


@dataclass
class HistorischerKontext:
    asset: str
    aehnliche_ereignisse: int
    durchschn_rendite_5d: float
    trefferquote_pct: float
    staerkste_korrelation: str   # Welcher Faktor hat am besten vorhergesagt
    warnung: str                 # z.B. "Aehnliche Situation fuehrte oft zu Verlust"
    verstaerkung: str            # z.B. "Aehnliche Muster fuehrten zu +8% in 5 Tagen"


# ---------------------------------------------------------------------------
# Datenbank Setup
# ---------------------------------------------------------------------------

def _verbindung() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PFAD), exist_ok=True)
    conn = sqlite3.connect(DB_PFAD)
    conn.row_factory = sqlite3.Row
    return conn


def initialisiere_db():
    """Legt die Tabellen an falls sie nicht existieren."""
    with _verbindung() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS ereignisse (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            datum           TEXT NOT NULL,
            asset           TEXT NOT NULL,
            schlagzeile     TEXT,
            news_sentiment  TEXT,
            signal_typ      TEXT,
            preis_einstieg  REAL,
            rendite_1d      REAL,
            rendite_5d      REAL,
            rendite_10d     REAL,
            korrekt         INTEGER,
            erstellt_am     TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS tages_signale (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            datum           TEXT NOT NULL,
            asset           TEXT NOT NULL,
            empfehlung      TEXT,
            einstieg        REAL,
            ziel            REAL,
            stop_loss       REAL,
            tech_signal     TEXT,
            news_sentiment  TEXT,
            social_sentiment TEXT,
            gesamt_punkte   REAL,
            abgeschlossen   INTEGER DEFAULT 0,
            erstellt_am     TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_ereignisse_asset ON ereignisse(asset);
        CREATE INDEX IF NOT EXISTS idx_ereignisse_datum ON ereignisse(datum);
        CREATE INDEX IF NOT EXISTS idx_signale_asset    ON tages_signale(asset);
        """)


# ---------------------------------------------------------------------------
# Daten speichern
# ---------------------------------------------------------------------------

def speichere_signal(signal: dict):
    """Speichert das heutige Signal fuer spaeteres Tracking."""
    initialisiere_db()
    f = signal.get("finale", {})
    with _verbindung() as conn:
        conn.execute("""
        INSERT INTO tages_signale
            (datum, asset, empfehlung, einstieg, ziel, stop_loss,
             tech_signal, news_sentiment, social_sentiment, gesamt_punkte)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().strftime("%Y-%m-%d"),
            signal.get("asset"),
            f.get("empfehlung"),
            f.get("einstieg", signal.get("preis", 0)),
            f.get("ziel", 0),
            f.get("stop_loss", 0),
            signal.get("technisches_signal"),
            signal.get("news_sentiment"),
            signal.get("social_sentiment", "neutral"),
            signal.get("gesamt_punkte", 0),
        ))


def aktualisiere_vergangene_signale():
    """
    Prueft alle offenen Signale der letzten 15 Tage und ergaenzt
    die tatsaechlichen Kursveraenderungen (Rendite nach 1/5/10 Tagen).
    """
    initialisiere_db()
    grenze = (datetime.now() - timedelta(days=15)).strftime("%Y-%m-%d")

    with _verbindung() as conn:
        offene = conn.execute("""
            SELECT * FROM tages_signale
            WHERE abgeschlossen = 0 AND datum >= ?
        """, (grenze,)).fetchall()

    aktualisiert = 0
    for row in offene:
        asset = row["asset"]
        datum = row["datum"]
        einstieg = row["einstieg"]
        if not einstieg or einstieg == 0:
            continue

        try:
            seit = (datetime.now() - datetime.strptime(datum, "%Y-%m-%d")).days
            if seit < 1:
                continue

            ticker = yf.Ticker(asset)
            hist   = ticker.history(period="20d")
            if hist.empty:
                continue

            # Renditen berechnen
            preise = hist["Close"].values
            r1d  = ((preise[min(1,  len(preise)-1)] / preise[0]) - 1) * 100 if len(preise) > 1  else 0
            r5d  = ((preise[min(5,  len(preise)-1)] / preise[0]) - 1) * 100 if len(preise) > 5  else 0
            r10d = ((preise[min(10, len(preise)-1)] / preise[0]) - 1) * 100 if len(preise) > 10 else 0

            empfehlung = row["empfehlung"]
            korrekt    = 1 if (empfehlung == "KAUFEN" and r5d > 0) or \
                               (empfehlung == "VERKAUFEN" and r5d < 0) else 0

            # Als Ereignis speichern
            with _verbindung() as conn:
                conn.execute("""
                INSERT OR IGNORE INTO ereignisse
                    (datum, asset, news_sentiment, signal_typ,
                     preis_einstieg, rendite_1d, rendite_5d, rendite_10d, korrekt)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (datum, asset, row["news_sentiment"],
                      row["tech_signal"], einstieg,
                      round(r1d, 2), round(r5d, 2), round(r10d, 2), korrekt))

                conn.execute("""
                UPDATE tages_signale SET abgeschlossen = 1
                WHERE id = ?
                """, (row["id"],))

            aktualisiert += 1

        except Exception:
            continue

    return aktualisiert


# ---------------------------------------------------------------------------
# Historischen Kontext abrufen
# ---------------------------------------------------------------------------

def hole_historischen_kontext(
    asset: str,
    news_sentiment: str = "neutral",
    tech_signal: str    = "",
    min_ereignisse: int = 3,
) -> HistorischerKontext | None:
    """
    Sucht aehnliche vergangene Situationen und berechnet
    die durchschnittlichen Auswirkungen.
    """
    initialisiere_db()

    with _verbindung() as conn:
        # Exakt passendes Asset + Sentiment
        zeilen = conn.execute("""
            SELECT rendite_5d, rendite_10d, korrekt, signal_typ, schlagzeile
            FROM ereignisse
            WHERE asset = ? AND news_sentiment = ?
            ORDER BY datum DESC
            LIMIT 50
        """, (asset, news_sentiment)).fetchall()

        # Fallback: nur Asset
        if len(zeilen) < min_ereignisse:
            zeilen = conn.execute("""
                SELECT rendite_5d, rendite_10d, korrekt, signal_typ, schlagzeile
                FROM ereignisse
                WHERE asset = ?
                ORDER BY datum DESC
                LIMIT 50
            """, (asset,)).fetchall()

    if len(zeilen) < min_ereignisse:
        return None

    renditen_5d  = [r["rendite_5d"]  for r in zeilen if r["rendite_5d"]  is not None]
    renditen_10d = [r["rendite_10d"] for r in zeilen if r["rendite_10d"] is not None]
    korrekt_list = [r["korrekt"]     for r in zeilen if r["korrekt"]     is not None]

    if not renditen_5d:
        return None

    durchschn_5d    = sum(renditen_5d)  / len(renditen_5d)
    trefferquote    = (sum(korrekt_list) / len(korrekt_list) * 100) if korrekt_list else 0

    # Staerkste Korrelation bestimmen
    signal_typen = [r["signal_typ"] for r in zeilen if r["signal_typ"]]
    haeufigster  = max(set(signal_typen), key=signal_typen.count) if signal_typen else "–"

    warnung      = ""
    verstaerkung = ""

    if durchschn_5d < -3:
        warnung = f"Aehnliche Situationen fuehrten historisch zu {durchschn_5d:.1f}% in 5 Tagen — Vorsicht."
    elif durchschn_5d > 3:
        verstaerkung = f"Aehnliche Situationen fuehrten historisch zu +{durchschn_5d:.1f}% in 5 Tagen — positives Muster."

    if trefferquote < 35:
        warnung += f" Bisherige Trefferquote fuer {asset}: {trefferquote:.0f}% — Signal unzuverlaessig."
    elif trefferquote > 60:
        verstaerkung += f" Historische Trefferquote: {trefferquote:.0f}% — Signal zuverlaessig."

    return HistorischerKontext(
        asset=asset,
        aehnliche_ereignisse=len(zeilen),
        durchschn_rendite_5d=round(durchschn_5d, 2),
        trefferquote_pct=round(trefferquote, 1),
        staerkste_korrelation=haeufigster,
        warnung=warnung.strip(),
        verstaerkung=verstaerkung.strip(),
    )


# ---------------------------------------------------------------------------
# Statistik-Ausgabe
# ---------------------------------------------------------------------------

def drucke_statistik():
    """Gibt eine Uebersicht ueber alle gespeicherten Ereignisse aus."""
    initialisiere_db()
    with _verbindung() as conn:
        gesamt   = conn.execute("SELECT COUNT(*) FROM ereignisse").fetchone()[0]
        signale  = conn.execute("SELECT COUNT(*) FROM tages_signale").fetchone()[0]
        korrekt  = conn.execute("SELECT COUNT(*) FROM ereignisse WHERE korrekt = 1").fetchone()[0]
        assets   = conn.execute("SELECT DISTINCT asset FROM ereignisse").fetchall()

    print(f"\n  Marktgedaechtnis-Datenbank:")
    print(f"  Gespeicherte Ereignisse : {gesamt}")
    print(f"  Verfolgte Signale       : {signale}")
    print(f"  Korrekte Signale        : {korrekt} ({korrekt/gesamt*100:.0f}%)" if gesamt > 0 else "  Noch keine Ereignisse.")
    print(f"  Assets mit Geschichte   : {len(assets)}")


# ---------------------------------------------------------------------------
# Einstiegspunkt
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    initialisiere_db()

    print("Memory Agent — Datenbank initialisiert.")
    print(f"Pfad: {DB_PFAD}\n")

    # Vergangene Signale aktualisieren
    print("Aktualisiere vergangene Signale...")
    n = aktualisiere_vergangene_signale()
    print(f"{n} Signale aktualisiert.")

    drucke_statistik()

    # Beispiel-Abfrage
    kontext = hole_historischen_kontext("MSFT", "neutral")
    if kontext:
        print(f"\nHistorischer Kontext MSFT: {kontext}")
    else:
        print("\nNoch nicht genug Daten fuer MSFT — waechst mit jedem Tageslauf.")
