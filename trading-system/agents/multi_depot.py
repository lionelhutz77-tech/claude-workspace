"""
Multi-Depot — 4 Strategien im Vergleich
Jede Strategie laeuft mit eigenem virtuellen Kapital (je 1.000 EUR)
und wird nach denselben Regeln abgerechnet (Trade Republic Kosten).

Strategien:
  1. MOMENTUM   — kauft die trendstaerksten Assets (hoher Score + Momentum)
  2. VALUE      — kauft ueberverkaufte Assets (niedriger RSI, Contrarian)
  3. BALANCED   — unser Hauptsystem (alle Signale gewichtet)
  4. PATTERN    — nur Pattern-Agent Empfehlungen (Kerzen, Fib, Stochastik)
"""

import sys
import os
import sqlite3
import time
from datetime import datetime, timedelta
from dataclasses import dataclass

import yfinance as yf

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

DB_PFAD = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "multi_depot.db")

STARTKAPITAL     = 1_000.0
KOSTEN_PRO_SEITE = 0.002
MIN_POSITION     = 20.0
MAX_POSITION_PCT = 0.35

STRATEGIEN = ["MOMENTUM", "VALUE", "BALANCED", "PATTERN"]


# ---------------------------------------------------------------------------
# Datenbank
# ---------------------------------------------------------------------------

def initialisiere():
    os.makedirs(os.path.dirname(DB_PFAD), exist_ok=True)
    with sqlite3.connect(DB_PFAD) as conn:
        conn.executescript(f"""
        CREATE TABLE IF NOT EXISTS depots (
            strategie   TEXT PRIMARY KEY,
            cash        REAL DEFAULT {STARTKAPITAL},
            erstellt_am TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS positionen (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            strategie       TEXT NOT NULL,
            asset           TEXT NOT NULL,
            asset_typ       TEXT DEFAULT 'aktie',
            eroeffnet_am    TEXT,
            einstieg_preis  REAL,
            einheiten       REAL,
            investiert_eur  REAL,
            ziel_preis      REAL,
            stop_loss_preis REAL,
            status          TEXT DEFAULT 'offen',
            schluss_preis   REAL DEFAULT 0,
            schluss_datum   TEXT DEFAULT '',
            pnl_eur         REAL DEFAULT 0,
            pnl_pct         REAL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS verlauf (
            datum       TEXT,
            strategie   TEXT,
            depotwert   REAL,
            pnl_eur     REAL,
            pnl_pct     REAL,
            PRIMARY KEY (datum, strategie)
        );
        """)

        # Depots initialisieren
        for s in STRATEGIEN:
            conn.execute(
                "INSERT OR IGNORE INTO depots (strategie, cash) VALUES (?, ?)",
                (s, STARTKAPITAL)
            )


def hole_cash(strategie: str) -> float:
    with sqlite3.connect(DB_PFAD) as conn:
        row = conn.execute(
            "SELECT cash FROM depots WHERE strategie = ?", (strategie,)
        ).fetchone()
        return float(row[0]) if row else STARTKAPITAL


def setze_cash(strategie: str, betrag: float):
    with sqlite3.connect(DB_PFAD) as conn:
        conn.execute(
            "UPDATE depots SET cash = ? WHERE strategie = ?",
            (round(betrag, 2), strategie)
        )


# ---------------------------------------------------------------------------
# Strategie-Filter
# ---------------------------------------------------------------------------

def filtere_fuer_strategie(strategie: str, alle_signale: list[dict]) -> list[dict]:
    """
    Waehlt aus allen heutigen Signalen die passenden fuer jede Strategie.
    """
    kaufen = [s for s in alle_signale if s.get("finale", {}).get("empfehlung") == "KAUFEN"]

    if strategie == "MOMENTUM":
        # Hoechstes Momentum und RSI zwischen 50-70 (nicht ueberhitzt)
        kandidaten = [
            s for s in alle_signale
            if s.get("rsi", 50) < 70 and s.get("momentum_5d", 0) > 2
        ]
        return sorted(kandidaten, key=lambda x: x.get("momentum_5d", 0), reverse=True)[:5]

    elif strategie == "VALUE":
        # Ueberverkaufte Assets (RSI < 40) — Contrarian
        kandidaten = [
            s for s in alle_signale
            if s.get("rsi", 50) < 40
        ]
        return sorted(kandidaten, key=lambda x: x.get("rsi", 50))[:5]

    elif strategie == "BALANCED":
        # Unser Hauptsystem — alle KAUFEN-Signale
        return sorted(kaufen, key=lambda x: x.get("gesamt_punkte", 0), reverse=True)[:5]

    elif strategie == "PATTERN":
        # Nur Pattern-basierte Empfehlungen
        return [
            s for s in alle_signale
            if s.get("pattern_empfehlung") == "KAUFEN"
        ][:5]

    return []


# ---------------------------------------------------------------------------
# Positionen oeffnen
# ---------------------------------------------------------------------------

def oeffne_positionen(strategie: str, signale: list[dict]) -> list[str]:
    """Oeffnet Positionen fuer eine Strategie."""
    if not signale:
        return []

    initialisiere()
    cash      = hole_cash(strategie)
    depotwert = berechne_depotwert(strategie)

    # Pruefen welche Assets bereits offen sind
    with sqlite3.connect(DB_PFAD) as conn:
        offene = {
            row[0] for row in conn.execute(
                "SELECT asset FROM positionen WHERE strategie = ? AND status = 'offen'",
                (strategie,)
            ).fetchall()
        }

    neue = [s for s in signale if s["asset"] not in offene]
    if not neue or cash < MIN_POSITION:
        return []

    # Kapital gleichmaessig aufteilen
    anteil = min(cash / len(neue), depotwert * MAX_POSITION_PCT)
    eroeffnet = []

    for sig in neue:
        if anteil < MIN_POSITION:
            break

        f        = sig.get("finale", {})
        einstieg = float(f.get("einstieg", sig.get("preis", 0)))
        if einstieg <= 0:
            continue

        ziel = float(f.get("ziel", einstieg * 1.10))
        stop = float(f.get("stop_loss", einstieg * 0.95))

        # Kosten
        kosten   = anteil * KOSTEN_PRO_SEITE
        netto    = anteil - kosten
        einheiten = netto / einstieg

        with sqlite3.connect(DB_PFAD) as conn:
            conn.execute("""
            INSERT INTO positionen
                (strategie, asset, asset_typ, eroeffnet_am, einstieg_preis,
                 einheiten, investiert_eur, ziel_preis, stop_loss_preis)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                strategie,
                sig["asset"],
                sig.get("asset_typ", "aktie"),
                datetime.now().strftime("%Y-%m-%d"),
                round(einstieg, 4),
                round(einheiten, 6),
                round(anteil, 2),
                round(ziel, 4),
                round(stop, 4),
            ))

        setze_cash(strategie, hole_cash(strategie) - anteil)
        eroeffnet.append(sig["asset"])

    return eroeffnet


# ---------------------------------------------------------------------------
# Positionen aktualisieren
# ---------------------------------------------------------------------------

def aktualisiere_positionen() -> dict[str, list]:
    """Prueft alle offenen Positionen aller Strategien gegen aktuelle Kurse."""
    initialisiere()
    geschlossen = {s: [] for s in STRATEGIEN}

    with sqlite3.connect(DB_PFAD) as conn:
        conn.row_factory = sqlite3.Row
        offene = conn.execute(
            "SELECT * FROM positionen WHERE status = 'offen'"
        ).fetchall()

    for pos in offene:
        try:
            yf_sym = f"{pos['asset']}-USD" if pos["asset_typ"] == "krypto" else pos["asset"]
            ticker = yf.Ticker(yf_sym)
            hist   = ticker.history(period="2d")
            if hist.empty:
                continue

            kurs    = float(hist["Close"].iloc[-1])
            status  = None
            schluss = kurs

            haltetage = (datetime.now() - datetime.strptime(pos["eroeffnet_am"], "%Y-%m-%d")).days

            if kurs >= pos["ziel_preis"]:
                status = "gewinn"; schluss = pos["ziel_preis"]
            elif kurs <= pos["stop_loss_preis"]:
                status = "verlust"; schluss = pos["stop_loss_preis"]
            elif haltetage >= 20:
                status = "abgelaufen"; schluss = kurs

            if status:
                erloese     = pos["einheiten"] * schluss
                kosten_vk   = erloese * KOSTEN_PRO_SEITE
                netto       = erloese - kosten_vk
                pnl_eur     = netto - pos["investiert_eur"]
                pnl_pct     = pnl_eur / pos["investiert_eur"] * 100

                with sqlite3.connect(DB_PFAD) as conn:
                    conn.execute("""
                    UPDATE positionen SET status=?, schluss_preis=?,
                        schluss_datum=?, pnl_eur=?, pnl_pct=?
                    WHERE id=?
                    """, (status, round(schluss,4),
                          datetime.now().strftime("%Y-%m-%d"),
                          round(pnl_eur,2), round(pnl_pct,2), pos["id"]))

                setze_cash(pos["strategie"], hole_cash(pos["strategie"]) + netto)
                geschlossen[pos["strategie"]].append({
                    "asset": pos["asset"], "status": status,
                    "pnl_eur": round(pnl_eur,2), "pnl_pct": round(pnl_pct,2)
                })
        except Exception:
            continue
        time.sleep(0.1)

    return geschlossen


# ---------------------------------------------------------------------------
# Depotwert und Statistiken
# ---------------------------------------------------------------------------

def berechne_depotwert(strategie: str) -> float:
    cash = hole_cash(strategie)
    with sqlite3.connect(DB_PFAD) as conn:
        offene = conn.execute(
            "SELECT asset, asset_typ, einheiten, investiert_eur FROM positionen "
            "WHERE strategie = ? AND status = 'offen'", (strategie,)
        ).fetchall()

    pos_wert = 0.0
    for asset, typ, einh, inv in offene:
        try:
            yf_sym = f"{asset}-USD" if typ == "krypto" else asset
            hist   = yf.Ticker(yf_sym).history(period="2d")
            if not hist.empty:
                pos_wert += einh * float(hist["Close"].iloc[-1])
            else:
                pos_wert += inv
        except Exception:
            pos_wert += inv

    return round(cash + pos_wert, 2)


def hole_alle_statistiken() -> list[dict]:
    """Gibt Statistiken fuer alle Strategien zurueck."""
    initialisiere()
    ergebnisse = []

    for strategie in STRATEGIEN:
        depotwert = berechne_depotwert(strategie)
        cash      = hole_cash(strategie)
        pnl_eur   = depotwert - STARTKAPITAL
        pnl_pct   = pnl_eur / STARTKAPITAL * 100

        with sqlite3.connect(DB_PFAD) as conn:
            conn.row_factory = sqlite3.Row
            alle    = conn.execute(
                "SELECT * FROM positionen WHERE strategie = ?", (strategie,)
            ).fetchall()

        geschl   = [p for p in alle if p["status"] != "offen"]
        offene   = [p for p in alle if p["status"] == "offen"]
        gewinner = [p for p in geschl if p["pnl_eur"] > 0]
        verlierer= [p for p in geschl if p["pnl_eur"] <= 0]
        trefferq = len(gewinner) / len(geschl) * 100 if geschl else 0.0

        ergebnisse.append({
            "strategie":     strategie,
            "depotwert":     depotwert,
            "cash":          cash,
            "pnl_eur":       round(pnl_eur, 2),
            "pnl_pct":       round(pnl_pct, 2),
            "trades_gesamt": len(geschl),
            "trades_offen":  len(offene),
            "trefferquote":  round(trefferq, 1),
            "offene_pos":    [dict(p) for p in offene],
            "letzte_trades": [dict(p) for p in geschl[-5:]],
        })

    # Nach P&L sortieren (bestes Depot zuerst)
    ergebnisse.sort(key=lambda x: x["pnl_eur"], reverse=True)
    return ergebnisse


def speichere_tageswert():
    """Speichert den heutigen Depotwert aller Strategien."""
    initialisiere()
    heute = datetime.now().strftime("%Y-%m-%d")
    for strategie in STRATEGIEN:
        depotwert = berechne_depotwert(strategie)
        pnl_eur   = depotwert - STARTKAPITAL
        pnl_pct   = pnl_eur / STARTKAPITAL * 100
        with sqlite3.connect(DB_PFAD) as conn:
            conn.execute("""
            INSERT OR REPLACE INTO verlauf (datum, strategie, depotwert, pnl_eur, pnl_pct)
            VALUES (?, ?, ?, ?, ?)
            """, (heute, strategie, depotwert, round(pnl_eur,2), round(pnl_pct,2)))


# ---------------------------------------------------------------------------
# Ausgabe
# ---------------------------------------------------------------------------

def drucke_vergleich():
    stats = hole_alle_statistiken()
    breite = 65
    print("\n" + "=" * breite)
    print("  MULTI-DEPOT STRATEGIE-VERGLEICH")
    print("=" * breite)
    print(f"  {'Strategie':<12} {'Depotwert':>10} {'P&L EUR':>10} {'P&L %':>8} {'Treffer':>8} {'Offen':>6}")
    print("  " + "-" * 58)
    for s in stats:
        pnl_sym = "+" if s["pnl_eur"] >= 0 else ""
        print(f"  {s['strategie']:<12} "
              f"{s['depotwert']:>9,.2f}€ "
              f"{pnl_sym}{s['pnl_eur']:>8,.2f}€ "
              f"{pnl_sym}{s['pnl_pct']:>6.1f}% "
              f"{s['trefferquote']:>7.0f}% "
              f"{s['trades_offen']:>5}")
    print("=" * breite)


# ---------------------------------------------------------------------------
# Einstiegspunkt
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Multi-Depot — Initialisierung\n")
    initialisiere()

    # Test: Simuliere Positionen
    test_signale = [
        {"asset": "MSFT", "asset_typ": "aktie", "rsi": 69.0, "momentum_5d": 3.2,
         "gesamt_punkte": 2.1, "pattern_empfehlung": "KAUFEN",
         "finale": {"empfehlung": "KAUFEN", "einstieg": 443.90, "ziel": 488.0, "stop_loss": 421.0}},
        {"asset": "AMD",  "asset_typ": "aktie", "rsi": 63.0, "momentum_5d": 12.4,
         "gesamt_punkte": 1.8, "pattern_empfehlung": "ABWARTEN",
         "finale": {"empfehlung": "KAUFEN", "einstieg": 505.0, "ziel": 560.0, "stop_loss": 479.0}},
        {"asset": "BTC",  "asset_typ": "krypto", "rsi": 22.0, "momentum_5d": -0.4,
         "gesamt_punkte": 0.5, "pattern_empfehlung": "ABWARTEN",
         "finale": {"empfehlung": "KAUFEN", "einstieg": 61186.0, "ziel": 70000.0, "stop_loss": 56000.0}},
    ]

    for strategie in STRATEGIEN:
        kandidaten = filtere_fuer_strategie(strategie, test_signale)
        eroeffnet  = oeffne_positionen(strategie, kandidaten)
        print(f"  {strategie}: {eroeffnet if eroeffnet else 'keine neuen Positionen'}")

    speichere_tageswert()
    print()
    drucke_vergleich()
