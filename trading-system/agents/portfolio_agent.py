"""
Musterdepot / Paper-Trading Agent
Verwaltet ein virtuelles Depot mit echten Empfehlungen des Systems.
Kein echtes Geld — aber echte Kurse und echte Buchführung.

Kapital-Logik:
  - Startkapital: 1.000 EUR (konfigurierbar)
  - Alle KAUFEN-Empfehlungen eines Tages teilen sich das verfuegbare Kapital
  - Gleichmaessige Verteilung, leicht gewichtet nach Signal-Staerke
  - Wenn kein Kapital frei: keine neuen Positionen bis eine schliesst
  - Maximale Einzelposition: 40% des Gesamtkapitals (Klumpenrisiko)

Kosten: 0.2% pro Seite (Spread + Ordergebuehr), realistisch fuer CFD/ETF
"""

import sys
import os
import sqlite3
from datetime import datetime, timedelta
from dataclasses import dataclass

import yfinance as yf

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

DB_PFAD = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "portfolio.db")

# ---------------------------------------------------------------------------
# Konfiguration
# ---------------------------------------------------------------------------

STARTKAPITAL        = 1_000.0    # EUR — realistischer Testbetrag
KOSTEN_PRO_SEITE    = 0.002      # 0.2% pro Seite (Spread + Ordergebuehr)
MAX_EINZELPOS_PCT   = 0.40       # Max. 40% des Gesamtkapitals in einer Position
MIN_POSITION_EUR    = 20.0       # Mindest-Positionsgroesse (unter 20 EUR kein Trade)
WAEHRUNG            = "EUR"


# ---------------------------------------------------------------------------
# Datenstrukturen
# ---------------------------------------------------------------------------

@dataclass
class Position:
    id: int
    asset: str
    asset_typ: str
    eroeffnet_am: str
    einstieg_preis: float
    anzahl_einheiten: float
    investiert_eur: float
    ziel_preis: float
    stop_loss_preis: float
    status: str              # "offen", "gewinn", "verlust", "abgelaufen"
    schluss_preis: float = 0.0
    schluss_datum: str = ""
    pnl_eur: float = 0.0
    pnl_pct: float = 0.0


# ---------------------------------------------------------------------------
# Datenbanksetup
# ---------------------------------------------------------------------------

def _verbindung() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PFAD), exist_ok=True)
    conn = sqlite3.connect(DB_PFAD)
    conn.row_factory = sqlite3.Row
    return conn


def initialisiere_portfolio():
    with _verbindung() as conn:
        conn.executescript(f"""
        CREATE TABLE IF NOT EXISTS depot_config (
            schluessel  TEXT PRIMARY KEY,
            wert        TEXT
        );

        CREATE TABLE IF NOT EXISTS positionen (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            asset               TEXT NOT NULL,
            asset_typ           TEXT,
            eroeffnet_am        TEXT,
            einstieg_preis      REAL,
            anzahl_einheiten    REAL,
            investiert_eur      REAL,
            ziel_preis          REAL,
            stop_loss_preis     REAL,
            status              TEXT DEFAULT 'offen',
            schluss_preis       REAL DEFAULT 0,
            schluss_datum       TEXT DEFAULT '',
            pnl_eur             REAL DEFAULT 0,
            pnl_pct             REAL DEFAULT 0,
            system_empfehlung   TEXT,
            notiz               TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS depot_verlauf (
            datum       TEXT PRIMARY KEY,
            depotwert   REAL,
            cash        REAL,
            positionen  INTEGER,
            tagesrendite REAL
        );

        INSERT OR IGNORE INTO depot_config VALUES ('startkapital', '{STARTKAPITAL}');
        INSERT OR IGNORE INTO depot_config VALUES ('cash', '{STARTKAPITAL}');
        INSERT OR IGNORE INTO depot_config VALUES ('erstellt_am', '{datetime.now().strftime("%Y-%m-%d")}');
        """)


def _hole_cash() -> float:
    with _verbindung() as conn:
        row = conn.execute(
            "SELECT wert FROM depot_config WHERE schluessel = 'cash'"
        ).fetchone()
        return float(row["wert"]) if row else STARTKAPITAL


def _setze_cash(betrag: float):
    with _verbindung() as conn:
        conn.execute(
            "UPDATE depot_config SET wert = ? WHERE schluessel = 'cash'",
            (str(round(betrag, 2)),)
        )


def _anzahl_offene_positionen() -> int:
    with _verbindung() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM positionen WHERE status = 'offen'"
        ).fetchone()[0]


# ---------------------------------------------------------------------------
# Positionen oeffnen
# ---------------------------------------------------------------------------

def berechne_positionsgroessen(signale: list[dict]) -> dict[str, float]:
    """
    Verteilt das verfuegbare Kapital auf alle KAUFEN-Signale eines Tages.
    Gewichtung: staerkere Signale (hoehere gesamt_punkte) erhalten etwas mehr.

    Regeln:
      - Nur Signale mit empfehlung == KAUFEN
      - Keine doppelten Positionen (bereits offen)
      - Gleichmaessig verteilt, leicht gewichtet nach Signal-Staerke
      - Einzelposition max. MAX_EINZELPOS_PCT des Gesamtkapitals
      - Mindestgroesse: MIN_POSITION_EUR

    Gibt Dict {asset: investitionsbetrag_EUR} zurueck.
    """
    initialisiere_portfolio()
    cash         = _hole_cash()
    gesamtwert   = berechne_depotwert()
    max_einzeln  = gesamtwert * MAX_EINZELPOS_PCT

    # Nur neue KAUFEN-Signale (keine offenen Positionen fuer dieses Asset)
    with _verbindung() as conn:
        offene_assets = {
            row["asset"] for row in
            conn.execute("SELECT asset FROM positionen WHERE status = 'offen'").fetchall()
        }

    kandidaten = [
        s for s in signale
        if s.get("finale", {}).get("empfehlung") == "KAUFEN"
        and s["asset"] not in offene_assets
    ]

    if not kandidaten or cash < MIN_POSITION_EUR:
        return {}

    # Gewichtung nach Signal-Staerke (gesamt_punkte, Minimum 0.1)
    gewichte = []
    for s in kandidaten:
        punkte = max(float(s.get("gesamt_punkte") or 1.0), 0.1)
        gewichte.append(punkte)

    summe_gewichte = sum(gewichte)
    verteilung = {}

    for s, gew in zip(kandidaten, gewichte):
        anteil      = gew / summe_gewichte
        betrag      = cash * anteil
        betrag      = min(betrag, max_einzeln)   # Klumpenrisiko-Cap
        betrag      = round(betrag, 2)
        if betrag >= MIN_POSITION_EUR:
            verteilung[s["asset"]] = betrag

    return verteilung


def oeffne_positionen_tagesbatch(signale: list[dict]) -> list[str]:
    """
    Oeffnet alle Positionen fuer den heutigen Tag auf einmal.
    Verteilt Kapital optimal auf alle KAUFEN-Empfehlungen.
    Gibt Liste der eroeffneten Assets zurueck.
    """
    initialisiere_portfolio()
    verteilung = berechne_positionsgroessen(signale)

    if not verteilung:
        return []

    eroeffnet = []
    for signal in signale:
        asset = signal["asset"]
        if asset not in verteilung:
            continue

        f          = signal.get("finale", {})
        investition = verteilung[asset]
        einstieg   = float(f.get("einstieg", signal.get("preis", 0)))
        ziel       = float(f.get("ziel",      einstieg * 1.10))
        stop       = float(f.get("stop_loss", einstieg * 0.95))

        if einstieg <= 0:
            continue

        kosten         = investition * KOSTEN_PRO_SEITE
        invest_netto   = investition - kosten
        einheiten      = invest_netto / einstieg

        with _verbindung() as conn:
            conn.execute("""
            INSERT INTO positionen
                (asset, asset_typ, eroeffnet_am, einstieg_preis, anzahl_einheiten,
                 investiert_eur, ziel_preis, stop_loss_preis, status, system_empfehlung)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'offen', ?)
            """, (
                asset,
                signal.get("asset_typ", "aktie"),
                datetime.now().strftime("%Y-%m-%d"),
                round(einstieg,  4),
                round(einheiten, 6),
                round(investition, 2),
                round(ziel,  4),
                round(stop,  4),
                "KAUFEN",
            ))

        _setze_cash(_hole_cash() - investition)
        eroeffnet.append(asset)

    return eroeffnet


# Rueckwaertskompatibilitaet fuer Einzelaufruf
def oeffne_position(signal: dict) -> bool:
    """Einzelposition oeffnen (wird intern durch oeffne_positionen_tagesbatch ersetzt)."""
    result = oeffne_positionen_tagesbatch([signal])
    return len(result) > 0


# ---------------------------------------------------------------------------
# Positionen aktualisieren und schliessen
# ---------------------------------------------------------------------------

def _aktueller_kurs(asset: str, asset_typ: str) -> float | None:
    """Holt den aktuellen Kurs fuer ein Asset."""
    try:
        if asset_typ == "krypto":
            from crypto_analyst import lade_aktuellen_preis
            daten = lade_aktuellen_preis(asset)
            return daten.get("preis")
        else:
            ticker = yf.Ticker(asset)
            hist   = ticker.history(period="2d")
            if not hist.empty:
                return float(hist["Close"].iloc[-1])
    except Exception:
        pass
    return None


def aktualisiere_positionen() -> list[dict]:
    """
    Prueft alle offenen Positionen gegen aktuelle Kurse.
    Schliesst Positionen die Ziel oder Stop erreicht haben.
    Gibt eine Liste der geschlossenen Positionen zurueck.
    """
    initialisiere_portfolio()

    with _verbindung() as conn:
        offene = conn.execute(
            "SELECT * FROM positionen WHERE status = 'offen'"
        ).fetchall()

    geschlossen = []
    for pos in offene:
        kurs = _aktueller_kurs(pos["asset"], pos["asset_typ"] or "aktie")
        if kurs is None:
            continue

        status        = None
        schluss_preis = kurs

        # Maximal-Haltezeit: 20 Handelstage
        eroeffnet = datetime.strptime(pos["eroeffnet_am"], "%Y-%m-%d")
        haltetage = (datetime.now() - eroeffnet).days

        if kurs >= pos["ziel_preis"]:
            status        = "gewinn"
            schluss_preis = pos["ziel_preis"]
        elif kurs <= pos["stop_loss_preis"]:
            status        = "verlust"
            schluss_preis = pos["stop_loss_preis"]
        elif haltetage >= 20:
            status        = "abgelaufen"
            schluss_preis = kurs

        if status:
            # Kosten Verkauf einrechnen
            erloese        = pos["anzahl_einheiten"] * schluss_preis
            kosten_verkauf = erloese * KOSTEN_PRO_SEITE
            erloese_netto  = erloese - kosten_verkauf
            pnl_eur        = erloese_netto - pos["investiert_eur"]
            pnl_pct        = (pnl_eur / pos["investiert_eur"]) * 100

            with _verbindung() as conn:
                conn.execute("""
                UPDATE positionen
                SET status = ?, schluss_preis = ?, schluss_datum = ?,
                    pnl_eur = ?, pnl_pct = ?
                WHERE id = ?
                """, (
                    status,
                    round(schluss_preis, 4),
                    datetime.now().strftime("%Y-%m-%d"),
                    round(pnl_eur, 2),
                    round(pnl_pct, 2),
                    pos["id"],
                ))

            _setze_cash(_hole_cash() + erloese_netto)
            geschlossen.append({
                "asset": pos["asset"],
                "status": status,
                "pnl_eur": round(pnl_eur, 2),
                "pnl_pct": round(pnl_pct, 2),
            })

    return geschlossen


# ---------------------------------------------------------------------------
# Depotwert berechnen
# ---------------------------------------------------------------------------

def berechne_depotwert() -> float:
    """Berechnet den aktuellen Gesamtdepotwert (Cash + offene Positionen)."""
    initialisiere_portfolio()
    cash = _hole_cash()

    with _verbindung() as conn:
        offene = conn.execute(
            "SELECT * FROM positionen WHERE status = 'offen'"
        ).fetchall()

    positions_wert = 0.0
    for pos in offene:
        kurs = _aktueller_kurs(pos["asset"], pos["asset_typ"] or "aktie")
        if kurs:
            positions_wert += pos["anzahl_einheiten"] * kurs
        else:
            positions_wert += pos["investiert_eur"]  # Fallback: Einstiegswert

    return round(cash + positions_wert, 2)


def speichere_tageswert():
    """Speichert den heutigen Depotwert fuer den Verlauf."""
    depotwert = berechne_depotwert()
    cash      = _hole_cash()
    offene    = _anzahl_offene_positionen()
    heute     = datetime.now().strftime("%Y-%m-%d")

    with _verbindung() as conn:
        # Gestrigen Wert fuer Tagesrendite
        gestern = conn.execute("""
            SELECT depotwert FROM depot_verlauf
            ORDER BY datum DESC LIMIT 1
        """).fetchone()

        tagesrendite = 0.0
        if gestern and gestern["depotwert"]:
            tagesrendite = (depotwert / gestern["depotwert"] - 1) * 100

        conn.execute("""
        INSERT OR REPLACE INTO depot_verlauf
            (datum, depotwert, cash, positionen, tagesrendite)
        VALUES (?, ?, ?, ?, ?)
        """, (heute, depotwert, cash, offene, round(tagesrendite, 3)))


# ---------------------------------------------------------------------------
# Statistiken
# ---------------------------------------------------------------------------

def hole_statistiken() -> dict:
    """Berechnet vollstaendige Portfolio-Statistiken."""
    initialisiere_portfolio()

    with _verbindung() as conn:
        alle       = conn.execute("SELECT * FROM positionen").fetchall()
        offene     = [p for p in alle if p["status"] == "offen"]
        geschl     = [p for p in alle if p["status"] != "offen"]
        gewinn_p   = [p for p in geschl if p["pnl_eur"] > 0]
        verlust_p  = [p for p in geschl if p["pnl_eur"] <= 0]
        verlauf    = conn.execute(
            "SELECT * FROM depot_verlauf ORDER BY datum"
        ).fetchall()

    depotwert   = berechne_depotwert()
    startkapital= STARTKAPITAL
    gesamt_pnl  = depotwert - startkapital
    gesamt_pct  = (gesamt_pnl / startkapital) * 100

    trefferquote = (len(gewinn_p) / len(geschl) * 100) if geschl else 0
    avg_gewinn   = sum(p["pnl_pct"] for p in gewinn_p)  / len(gewinn_p)  if gewinn_p  else 0
    avg_verlust  = sum(p["pnl_pct"] for p in verlust_p) / len(verlust_p) if verlust_p else 0

    # Profit Factor: Summe Gewinne / Summe Verluste
    sum_gewinn  = sum(p["pnl_eur"] for p in gewinn_p)
    sum_verlust = abs(sum(p["pnl_eur"] for p in verlust_p))
    profit_factor = round(sum_gewinn / sum_verlust, 2) if sum_verlust > 0 else 0

    return {
        "startkapital":    startkapital,
        "depotwert":       depotwert,
        "cash":            _hole_cash(),
        "gesamt_pnl_eur":  round(gesamt_pnl, 2),
        "gesamt_pnl_pct":  round(gesamt_pct, 2),
        "trades_gesamt":   len(geschl),
        "trades_offen":    len(offene),
        "trades_gewinn":   len(gewinn_p),
        "trades_verlust":  len(verlust_p),
        "trefferquote":    round(trefferquote, 1),
        "avg_gewinn_pct":  round(avg_gewinn,  2),
        "avg_verlust_pct": round(avg_verlust, 2),
        "profit_factor":   profit_factor,
        "offene_positionen": [dict(p) for p in offene],
        "letzten_trades":    [dict(p) for p in geschl[-10:]],
        "verlauf":           [dict(p) for p in verlauf],
    }


# ---------------------------------------------------------------------------
# Ausgabe
# ---------------------------------------------------------------------------

def drucke_depot_status():
    stats = hole_statistiken()
    pnl_farbe = "+" if stats["gesamt_pnl_eur"] >= 0 else ""

    print("\n" + "=" * 62)
    print("  MUSTERDEPOT — AKTUELLER STAND")
    print("=" * 62)
    print(f"  Startkapital   : {stats['startkapital']:>10,.2f} {WAEHRUNG}")
    print(f"  Depotwert      : {stats['depotwert']:>10,.2f} {WAEHRUNG}")
    print(f"  Gesamt P&L     : {pnl_farbe}{stats['gesamt_pnl_eur']:>9,.2f} {WAEHRUNG}  "
          f"({pnl_farbe}{stats['gesamt_pnl_pct']:.2f}%)")
    print(f"  Cash verfuegbar: {stats['cash']:>10,.2f} {WAEHRUNG}")
    print()
    print(f"  Trades abgesch.: {stats['trades_gesamt']}")
    print(f"  Trefferquote   : {stats['trefferquote']:.1f}%")
    print(f"  Ø Gewinn       : +{stats['avg_gewinn_pct']:.2f}%")
    print(f"  Ø Verlust      :  {stats['avg_verlust_pct']:.2f}%")
    print(f"  Profit Factor  : {stats['profit_factor']:.2f}"
          + (" ✓" if stats["profit_factor"] > 1.5 else " (Ziel: >1.5)"))

    if stats["offene_positionen"]:
        print(f"\n  Offene Positionen ({len(stats['offene_positionen'])}):")
        for p in stats["offene_positionen"]:
            print(f"    {p['asset']:<6}  Einstieg: ${p['einstieg_preis']:>8,.2f}"
                  f"  Inv: {p['investiert_eur']:>7,.0f} {WAEHRUNG}"
                  f"  seit {p['eroeffnet_am']}")

    if stats["letzten_trades"]:
        print(f"\n  Letzte abgeschlossene Trades:")
        for p in reversed(stats["letzten_trades"][-5:]):
            symbol = "✓" if p["pnl_eur"] > 0 else "✗"
            print(f"    {symbol} {p['asset']:<6}  {p['schluss_datum']}  "
                  f"P&L: {p['pnl_eur']:>+7,.2f} {WAEHRUNG}  ({p['pnl_pct']:>+.1f}%)  "
                  f"[{p['status']}]")

    print("=" * 62)


# ---------------------------------------------------------------------------
# Einstiegspunkt
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    print("Trading Intelligence System — Musterdepot")
    initialisiere_portfolio()

    # Offene Positionen aktualisieren
    print("\nAktualisiere offene Positionen...")
    geschlossen = aktualisiere_positionen()
    if geschlossen:
        for g in geschlossen:
            symbol = "✓ GEWINN" if g["pnl_eur"] > 0 else "✗ VERLUST"
            print(f"  {symbol}: {g['asset']}  {g['pnl_eur']:+.2f} EUR ({g['pnl_pct']:+.1f}%)")
    else:
        print("  Keine Positionen geschlossen.")

    # Test: Simuliere eine Empfehlung
    print("\nTest-Position eroeffnen (MSFT)...")
    test_signal = {
        "asset": "MSFT", "asset_typ": "aktie",
        "preis": 443.90,
        "finale": {
            "empfehlung": "KAUFEN",
            "einstieg":  443.90,
            "ziel":      488.29,
            "stop_loss": 421.70,
        }
    }
    eroeffnet = oeffne_position(test_signal)
    print(f"  Position eroeffnet: {eroeffnet}")

    speichere_tageswert()
    drucke_depot_status()
