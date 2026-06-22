"""
Fear & Greed Agent
Holt den globalen Markt-Stimmungsindex (0–100) aus zwei kostenlosen Quellen:
  - CNN Fear & Greed Index   → Aktienmarkt
  - Alternative.me Index     → Krypto

Interpretation:
  0–20   Extreme Angst  → historisch beste Kaufgelegenheit
  21–40  Angst          → tendenziell günstige Einstiege
  41–60  Neutral        → kein starkes Signal
  61–80  Gier           → vorsichtig, Rücksetzer möglich
  81–100 Extreme Gier   → Überhitzung, defensiv positionieren
"""

import sys
import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

CNN_URL    = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
KRYPTO_URL = "https://api.alternative.me/fng/"


def _label_de(score: int) -> str:
    if score <= 20: return "Extreme Angst"
    if score <= 40: return "Angst"
    if score <= 60: return "Neutral"
    if score <= 80: return "Gier"
    return "Extreme Gier"


def hole_fear_greed_aktien() -> dict:
    """CNN Fear & Greed Index für den Aktienmarkt."""
    try:
        r = requests.get(
            CNN_URL,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
            timeout=10,
        )
        d = r.json()["fear_and_greed"]
        score = round(d["score"])
        return {"score": score, "label": _label_de(score), "quelle": "CNN"}
    except Exception as e:
        return {"score": 50, "label": "Neutral", "quelle": "fallback", "fehler": str(e)}


def hole_fear_greed_krypto() -> dict:
    """Alternative.me Krypto Fear & Greed Index."""
    try:
        r = requests.get(KRYPTO_URL, timeout=10)
        d = r.json()["data"][0]
        score = int(d["value"])
        return {"score": score, "label": _label_de(score), "quelle": "Alternative.me"}
    except Exception as e:
        return {"score": 50, "label": "Neutral", "quelle": "fallback", "fehler": str(e)}


def fear_greed_punkte(fg_aktien: dict) -> tuple[int, str]:
    """
    Wandelt den Aktienmarkt-Score in Trading-Punkte und Begründung um.
    Gegensätzlich zum Preis: Extreme Angst = Kaufchance.
    """
    s = fg_aktien["score"]
    if s <= 20: return +3, f"Extreme Angst ({s}/100) — historisch beste Kaufgelegenheit"
    if s <= 40: return +1, f"Angst ({s}/100) — guter Einstiegszeitpunkt"
    if s <= 60: return  0, f"Neutral ({s}/100)"
    if s <= 80: return -1, f"Gier ({s}/100) — Vorsicht bei Neukäufen"
    return -2, f"Extreme Gier ({s}/100) — Rücksetzer wahrscheinlich"


def drucke_fear_greed(fg_aktien: dict, fg_krypto: dict):
    punkte, beschreibung = fear_greed_punkte(fg_aktien)
    richtung = "+" if punkte > 0 else ""
    print(f"\n  MARKT-STIMMUNG (Fear & Greed):")
    print(f"  Aktien : {fg_aktien['score']:3d}/100  {fg_aktien['label']}  [{richtung}{punkte:+d} Trading-Punkte]")
    print(f"  Krypto : {fg_krypto['score']:3d}/100  {fg_krypto['label']}")
    print(f"  Signal : {beschreibung}")
