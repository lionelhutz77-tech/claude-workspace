"""
Tiefen-Analyse (Deep Dive) fuer die Top-Kaufkandidaten.
Buendelt ALLE vorhandenen System-Signale (TA, Volume/FVG, Pattern, Bewertung,
SEC-Insider, Korrelation, Backtest, Bull/Bear) zu EINER strukturierten
Institutions-Analyse. Ein Groq-Call pro Asset, nur fuer die Top-N — budgetschonend.

Wichtig: Es werden AUSSCHLIESSLICH die vorhandenen Systemdaten synthetisiert,
keine Fundamentalzahlen erfunden (kein Pseudo-DCF). Faellt der Groq-Call aus,
wird das Asset still uebersprungen (Tagesbericht laeuft normal weiter).
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
MODEL = "llama-3.3-70b-versatile"

# Wie viele der staerksten KAUFEN-Signale bekommen eine Tiefen-Analyse?
DEEP_DIVE_TOP_N = 3


SYSTEM = """Du bist ein Senior Equity/Crypto-Analyst, der fuer ein Anlage-Komitee
eine praegnante Tiefen-Analyse schreibt. Du arbeitest AUSSCHLIESSLICH mit den dir
gelieferten Systemdaten und erfindest KEINE Zahlen (kein erfundenes DCF, keine
erfundenen Umsaetze). Wenn eine Information fehlt, sagst du das knapp.
Schreibe sachlich, dicht, auf Deutsch, ohne Werbe-Floskeln. Keine Anlageberatung."""


def _ki_aufruf(system: str, user_prompt: str, max_tokens: int = 600) -> str:
    """Einzelner Groq-Aufruf mit Retry bei Rate-Limit (wie bull_bear_debate)."""
    for versuch in range(3):
        try:
            response = _client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user",   "content": user_prompt},
                ],
                max_tokens=max_tokens,
                temperature=0.4,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            if "429" in str(e) and versuch < 2:
                wartezeit = 30 * (versuch + 1)
                print(f" [Rate-Limit, warte {wartezeit}s]", end="", flush=True)
                time.sleep(wartezeit)
            else:
                raise


def _baue_datenblatt(sig: dict) -> str:
    """Stellt aus den vorhandenen Signal-Feldern ein kompaktes Datenblatt zusammen.
    Nur tatsaechlich vorhandene Felder werden aufgenommen (defensiv via .get)."""
    f = sig.get("finale", {})
    zeilen = []

    def add(label, wert):
        if wert is None or wert == "" or wert == []:
            return
        zeilen.append(f"- {label}: {wert}")

    typ = "Aktie" if sig.get("asset_typ") == "aktie" else "Krypto"
    add("Asset", f"{sig.get('asset')} ({typ})")
    add("Preis", f"${sig.get('preis', 0):,.2f}")
    add("Vorlaeufige Empfehlung (System)", sig.get("empfehlung"))
    add("Finale Empfehlung (nach Debatte)", f.get("empfehlung"))
    add("Einstieg/Ziel/Stop", f"${f.get('einstieg',0):,.2f} / ${f.get('ziel',0):,.2f} / ${f.get('stop_loss',0):,.2f}")
    add("Risiko", f.get("risiko"))
    add("Strategie", f"{sig.get('strategie','')} (Haltezeit {sig.get('haltezeit_tage','?')} Tage)".strip())

    # Technik
    add("Technisches Signal", sig.get("technisches_signal"))
    add("RSI", sig.get("rsi"))
    add("Trend", sig.get("trend"))

    # Bewertung (P/E-Label aus valuation_agent)
    add("Fundamentalbewertung (P/E vs. Sektor)", sig.get("bewertung"))

    # News
    if sig.get("news_sentiment"):
        add("News-Sentiment", f"{sig.get('news_sentiment').upper()} ({sig.get('news_anzahl','?')} Artikel)")

    # Volume / Marktstruktur
    add("OBV-Trend", sig.get("obv_trend"))
    add("Relatives Volumen", sig.get("rel_volumen"))
    if sig.get("vol_divergenz"):
        add("Volumen-Divergenz", "JA — Kurs steigt ohne institutionelle Unterstuetzung")
    add("Order Blocks", sig.get("order_blocks"))

    # Pattern
    add("Kerzenmuster", sig.get("kerzenmuster"))
    add("Stochastik", sig.get("stoch_signal"))
    add("Bollinger-Position", sig.get("bb_position"))
    add("Fibonacci-Level", sig.get("fib_level"))

    # SEC Insider
    if sig.get("sec_punkte"):
        add("SEC/Insider-Signal", f"Punkte {sig.get('sec_punkte')}")

    # Korrelation
    warnungen = sig.get("korrelation_warnungen") or []
    if warnungen:
        add("Korrelations-Warnungen", "; ".join(str(w) for w in warnungen[:2]))
    verstaerkt = sig.get("korrelation_verstaerkt") or []
    if verstaerkt:
        add("Verstaerkende Korrelationen", "; ".join(str(v) for v in verstaerkt[:2]))

    # Bull/Bear-Debatte
    add("Debatten-Gewinner", f.get("gewinner"))
    add("Unpriced Optionality (laut Debatte)", f.get("optionalitaet"))
    if sig.get("bull_argumente"):
        zeilen.append(f"- Bull-Argumente:\n{sig['bull_argumente']}")
    if sig.get("bear_argumente"):
        zeilen.append(f"- Bear-Argumente:\n{sig['bear_argumente']}")

    return "\n".join(zeilen)


def deep_dive(sig: dict) -> str:
    """Erzeugt die strukturierte Tiefen-Analyse fuer EIN Asset (ein Groq-Call)."""
    datenblatt = _baue_datenblatt(sig)
    prompt = f"""SYSTEMDATEN zum Asset (nur diese verwenden, nichts erfinden):
{datenblatt}

Erstelle daraus eine strukturierte Tiefen-Analyse in genau diesen Abschnitten:

1. INVESTMENT-THESE (2-3 Saetze: warum jetzt interessant)
2. BEWERTUNGS-CHECK (teuer/fair anhand der P/E-Einordnung; falls keine Daten: sagen)
3. KATALYSATOREN & OPTIONALITAET (was den Kurs treiben kann; uneingepreiste Punkte)
4. RISIKEN / BEAR-CASE (konkrete Abwaerts-Szenarien aus den Daten)
5. HANDLUNG (Einstieg/Ziel/Stop + Strategie/Haltezeit in einem Satz)

Schliesse mit einer Zeile:
FAZIT: <ein praegnanter Satz, max. 160 Zeichen>"""
    return _ki_aufruf(SYSTEM, prompt, max_tokens=600)


def waehle_top_kaufen(ergebnisse: list, n: int = DEEP_DIVE_TOP_N) -> list:
    """Waehlt die n staerksten KAUFEN-Signale (nach gesamt_punkte)."""
    kaufen = [e for e in ergebnisse
              if e.get("finale", {}).get("empfehlung") == "KAUFEN"]
    kaufen.sort(key=lambda e: e.get("gesamt_punkte", 0), reverse=True)
    return kaufen[:n]


def hole_fazit(deep_text: str) -> str:
    """Extrahiert die FAZIT-Zeile fuer den kompakten Telegram-Teaser."""
    for zeile in deep_text.splitlines():
        if zeile.strip().upper().startswith("FAZIT:"):
            return zeile.split(":", 1)[-1].strip()
    # Fallback: erste nicht-leere Zeile gekuerzt
    for zeile in deep_text.splitlines():
        if zeile.strip():
            return zeile.strip()[:160]
    return ""


# ---------------------------------------------------------------------------
# Standalone-Test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    test = {
        "asset": "NVDA", "asset_typ": "aktie", "preis": 178.50,
        "empfehlung": "KAUFEN", "gesamt_punkte": 2.4,
        "technisches_signal": "KAUFEN", "rsi": 58.2, "trend": "Aufwaertstrend",
        "bewertung": "FAIR", "news_sentiment": "bullish", "news_anzahl": 11,
        "obv_trend": "steigend", "rel_volumen": 1.3, "order_blocks": 2,
        "kerzenmuster": "bullish engulfing", "stoch_signal": "neutral",
        "bb_position": "Mitte", "fib_level": "0.618", "sec_punkte": 3,
        "strategie": "Medium", "haltezeit_tage": 20,
        "bull_argumente": "- KI-Nachfrage ungebrochen\n- Datacenter-Wachstum",
        "bear_argumente": "- Hohe Erwartungen\n- Bewertung anspruchsvoll",
        "finale": {
            "empfehlung": "KAUFEN", "einstieg": 178.50, "ziel": 205.0,
            "stop_loss": 168.0, "risiko": "MITTEL", "gewinner": "BULL",
            "optionalitaet": "Neue Inferenz-Chips noch nicht eingepreist",
        },
    }
    print("=== Tiefen-Analyse NVDA (Test) ===\n")
    txt = deep_dive(test)
    print(txt)
    print("\n=== FAZIT-Extraktion ===")
    print(hole_fazit(txt))
