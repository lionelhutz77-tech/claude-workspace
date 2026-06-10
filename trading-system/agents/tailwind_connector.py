"""
Tailwind Connector
Laedt die Signale des Tailwind Scanners und integriert sie als Zusatz-Punkte
in die taeglich Analyse des Trading-Systems.

Datenfluss:
  tailwind-scanner/data/latest_signals.json
    ↓ (lokal oder via GitHub raw URL)
  tailwind_connector.lade_tailwind_signale()
    ↓
  wende_tailwind_bonus_an(signal)  — wird auf jedes aggregierte Signal angewendet

Score-Einfluss:
  STARK   (≥ 55/100) → +3 Gesamtpunkte + Begruendung
  MODERAT (≥ 30/100) → +1 Gesamtpunkt  + Begruendung
  SCHWACH            → kein Einfluss
"""

import json
import os
import urllib.request
from datetime import datetime
from pathlib import Path

# Lokaler Pfad zur JSON-Datei (wenn Scanner auf diesem PC laeuft)
_SCANNER_DIR  = Path("C:/Users/HP/Documents/Claude/tailwind-scanner")
_JSON_LOKAL   = _SCANNER_DIR / "data" / "latest_signals.json"

# GitHub raw URL als Fallback (GitHub Actions committed die Datei taeglich)
_GITHUB_URL = (
    "https://raw.githubusercontent.com/lionelhutz77-tech/tailwind-scanner"
    "/main/data/latest_signals.json"
)

# Wie alt darf die JSON-Datei maximal sein? (in Tagen)
_MAX_ALTER_TAGE = 3

# Bonus-Punkte die auf gesamt_punkte addiert werden
_BONUS_STARK   = 3
_BONUS_MODERAT = 1


def lade_tailwind_signale() -> dict[str, dict]:
    """
    Laedt die Tailwind-Signale aus der JSON-Datei.
    Prioritaet: 1. lokale Datei  2. GitHub raw  3. leeres Dict (graceful)
    Gibt {ticker: signal_dict} zurueck.
    """
    daten = _lade_lokal()
    if not daten:
        daten = _lade_github()
    if not daten:
        print("  [Tailwind] Keine Signale verfuegbar — wird uebersprungen.")
        return {}

    # Flaches Ticker-Dict aufbauen
    signale: dict[str, dict] = {}
    for signal in daten.get("signals", []):
        ticker = signal.get("ticker", "")
        if ticker:
            signale[ticker] = signal

    meta = daten.get("meta", {})
    datum = meta.get("scan_datum", "?")
    stark = meta.get("stark_count", 0)
    mod   = meta.get("moderat_count", 0)
    print(f"  [Tailwind] {len(signale)} Ticker geladen (Scan: {datum}) — "
          f"{stark} STARK / {mod} MODERAT")
    return signale


def _lade_lokal() -> dict | None:
    """Laedt JSON von lokalem Dateisystem. None wenn nicht vorhanden oder zu alt."""
    if not _JSON_LOKAL.exists():
        return None
    try:
        alter_sek = datetime.now().timestamp() - _JSON_LOKAL.stat().st_mtime
        alter_tage = alter_sek / 86400
        if alter_tage > _MAX_ALTER_TAGE:
            print(f"  [Tailwind] Lokale Datei zu alt ({alter_tage:.1f} Tage) — versuche GitHub.")
            return None
        with open(_JSON_LOKAL, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"  [Tailwind] Lokale Datei Fehler: {e}")
        return None


def _lade_github() -> dict | None:
    """Laedt JSON direkt von GitHub raw. None bei Fehler."""
    try:
        with urllib.request.urlopen(_GITHUB_URL, timeout=15) as r:
            daten = json.loads(r.read().decode("utf-8"))
        print(f"  [Tailwind] Signale von GitHub geladen.")
        return daten
    except Exception as e:
        print(f"  [Tailwind] GitHub-Fetch fehlgeschlagen: {e}")
        return None


def wende_tailwind_bonus_an(signal: dict, tailwind_signale: dict[str, dict]) -> dict:
    """
    Prueft ob das Asset im Tailwind-Scanner als STARK/MODERAT eingestuft wurde.
    Wenn ja: addiert Bonuspunkte und ergaenzt die Begruendung.
    Gibt das (ggf. angepasste) Signal-Dict zurueck.
    """
    ticker = signal.get("asset", "")
    if not ticker or ticker not in tailwind_signale:
        return signal

    tw    = tailwind_signale[ticker]
    stufe = tw.get("signal_stufe", "SCHWACH")
    score = tw.get("gesamt_score", 0)
    thema = tw.get("thema", "Unbekannt")

    if stufe == "STARK":
        bonus = _BONUS_STARK
    elif stufe == "MODERAT":
        bonus = _BONUS_MODERAT
    else:
        return signal  # SCHWACH = kein Einfluss

    # Signal-Dict kopieren und anpassen
    signal = dict(signal)
    signal["gesamt_punkte"] = round(signal.get("gesamt_punkte", 0) + bonus, 2)

    # Kontext fuer KI-Analyse
    abstand = tw.get("kurs_info", {}).get("abstand_ath_prozent", 0)
    call_put = tw.get("details", {}).get("options", {}).get("call_put_ratio", 0)
    revisions = tw.get("details", {}).get("revisions", {}).get("bull_analysten", 0)

    beschreibung = (
        f"Tailwind [{stufe}]: {thema} — "
        f"Score {score}/100 | "
        f"{abstand:.0f}% unter 52W-Hoch"
    )
    if call_put:
        beschreibung += f" | Call/Put {call_put:.1f}"
    if revisions:
        beschreibung += f" | {revisions} Bull-Analysten"

    signal.setdefault("begruendung", []).append(beschreibung)

    # Tailwind-Metadaten fuer Report
    signal["tailwind_signal"] = stufe
    signal["tailwind_thema"]  = thema
    signal["tailwind_score"]  = score

    return signal


def hole_tailwind_universe(tailwind_signale: dict[str, dict], min_score: int = 55) -> list[str]:
    """
    Gibt eine Liste der starksten Tailwind-Ticker zurueck.
    Kann dem Universe Scanner uebergeben werden um zusaetzliche Kandidaten einzuschleusen.
    """
    kandidaten = [
        (ticker, s["gesamt_score"])
        for ticker, s in tailwind_signale.items()
        if s.get("gesamt_score", 0) >= min_score
    ]
    # Nach Score sortieren, nur Ticker zurueckgeben
    return [t for t, _ in sorted(kandidaten, key=lambda x: -x[1])]


# ---------------------------------------------------------------------------
# Standalone-Test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Tailwind Connector — Test\n")
    signale = lade_tailwind_signale()
    if signale:
        top = sorted(signale.values(), key=lambda x: x.get("gesamt_score", 0), reverse=True)[:10]
        print(f"\nTop-10 Tailwind-Ticker:")
        for s in top:
            print(f"  {s['ticker']:6s}  {s['gesamt_score']:3d}/100  [{s['signal_stufe']:7s}]  {s['thema']}")

        stark_ticker = hole_tailwind_universe(signale)
        print(f"\nSTARK-Kandidaten fuer Universe Scanner ({len(stark_ticker)}): {stark_ticker}")
    else:
        print("Keine Signale geladen.")
        print(f"Erwarteter Pfad: {_JSON_LOKAL}")
        print("Tailwind Scanner einmal lokal ausfuehren um Datei zu erzeugen.")
