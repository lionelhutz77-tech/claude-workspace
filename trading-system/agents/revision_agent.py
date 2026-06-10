"""
Revisions-Agent -- KI-gestuetzt (Groq / Llama 3.3 70B)
Nimmt das aggregierte Signal eines Assets und erstellt eine tiefgehende,
strukturierte Analyse mit Begruendung und finaler Empfehlung.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """Du bist ein erfahrener Finanzanalyst mit 20 Jahren Erfahrung
in technischer Analyse, Fundamentalanalyse und Marktpsychologie. Du analysierst
Aktien und Kryptowaehrungen und gibst klare, begruendete Handelsempfehlungen.

Deine Antworten sind:
- Praezise und faktenbasiert
- Klar strukturiert
- Ehrlich ueber Risiken
- Niemals blumig oder uebertrieben optimistisch

Du gibst KEINE allgemeinen Finanzberatungen. Du analysierst konkrete Daten
und leitest daraus eine Meinung ab. Der Nutzer trifft die finale Entscheidung selbst."""


def _lade_lehren() -> str:
    """Laedt aktive Erkenntnisse aus dem Lern-Agent (graceful fallback)."""
    try:
        from learning_agent import hole_aktive_lehren_als_text
        return hole_aktive_lehren_als_text(4)
    except Exception:
        return ""


def erstelle_analyse_prompt(signal: dict) -> str:
    """Erstellt den Prompt fuer die KI-Analyse aus einem aggregierten Signal."""
    lehren_block = _lade_lehren()
    lehren_text  = f"\n{lehren_block}\n" if lehren_block else ""
    return f"""Analysiere folgendes Asset und gib eine strukturierte Einschaetzung:
{lehren_text}

ASSET: {signal['asset']} ({signal['asset_typ'].upper()})
AKTUELLER PREIS: ${signal['preis']:,.2f}

TECHNISCHE ANALYSE:
- Signal: {signal['technisches_signal']}
- RSI: {signal.get('rsi', 'n/a')}
- Trend: {signal.get('trend', 'n/a')}
- Technische Punkte: {signal['technische_punkte']:+d}

NEWS-SENTIMENT:
- Gesamt: {signal['news_sentiment'].upper()}
- Anzahl relevanter Artikel: {signal['news_anzahl']}
- News-Punkte: {signal['news_punkte']:+d}

VORLAEUFIGE EMPFEHLUNG: {signal['empfehlung']}
GESAMTPUNKTE: {signal['gesamt_punkte']:+.2f}

BEGRUENDUNGEN BISHER:
{chr(10).join(f"- {b}" for b in signal['begruendung'])}

Bitte antworte in folgendem Format:

LAGE: [2-3 Saetze zur aktuellen Marktsituation dieses Assets]

STAERKEN: [Bullet-Liste der positiven Faktoren]

RISIKEN: [Bullet-Liste der Risiken und Gefahren]

FAZIT: [1 klarer Satz mit der Empfehlung und Begruendung]

EMPFEHLUNG: [NUR eines von: KAUFEN / VERKAUFEN / ABWARTEN]"""


def analysiere_mit_ki(signal: dict) -> dict:
    """
    Schickt ein aggregiertes Signal an die KI und bekommt eine
    strukturierte Analyse zurueck.
    """
    prompt = erstelle_analyse_prompt(signal)

    for versuch in range(3):
        try:
            response = _client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": prompt},
                ],
                max_tokens=600,
                temperature=0.3,
            )
            break
        except Exception as e:
            if "429" in str(e) and versuch < 2:
                import time
                wartezeit = 30 * (versuch + 1)
                print(f" [Rate-Limit, warte {wartezeit}s]", end="", flush=True)
                time.sleep(wartezeit)
            else:
                raise

    analyse_text = response.choices[0].message.content.strip()

    # Finale Empfehlung aus dem Text extrahieren
    empfehlung = signal["empfehlung"]  # Fallback
    for zeile in analyse_text.splitlines():
        if zeile.strip().startswith("EMPFEHLUNG:"):
            wert = zeile.split(":", 1)[-1].strip().upper()
            if "KAUFEN" in wert:
                empfehlung = "KAUFEN"
            elif "VERKAUFEN" in wert:
                empfehlung = "VERKAUFEN"
            else:
                empfehlung = "ABWARTEN"

    # TECHNISCHES VETO: Wenn TA klar VERKAUFEN zeigt, darf KI nicht auf KAUFEN
    # ueberstimmen — das war der Fehler beim BTC-Drop am 31.05.2026
    if signal.get("technisches_signal") == "VERKAUFEN" and empfehlung == "KAUFEN":
        empfehlung = "ABWARTEN"

    return {
        **signal,
        "ki_analyse": analyse_text,
        "ki_empfehlung": empfehlung,
    }


def drucke_ki_analyse(ergebnis: dict):
    """Gibt die vollstaendige KI-Analyse aus."""
    breite = 65
    print("\n" + "=" * breite)
    typ = "AKTIE" if ergebnis["asset_typ"] == "aktie" else "KRYPTO"
    print(f"  [{typ}] {ergebnis['asset']}  --  ${ergebnis['preis']:,.2f}")
    print("=" * breite)
    print(ergebnis["ki_analyse"])
    print("-" * breite)
    empf = ergebnis["ki_empfehlung"]
    if empf == "KAUFEN":
        print(f"  >> {empf} <<   |  Ziel: ${ergebnis['ziel']:,.2f}  |  Stop: ${ergebnis['stop_loss']:,.2f}")
    else:
        print(f"  -- {empf} --")
    print("=" * breite)


# ---------------------------------------------------------------------------
# Einstiegspunkt (Standalone-Test)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Testdaten -- simuliert ein Aggregator-Ergebnis
    test_signal = {
        "asset": "MSFT",
        "asset_typ": "aktie",
        "preis": 440.27,
        "technisches_signal": "KAUFEN",
        "technische_punkte": 3,
        "rsi": 67.84,
        "trend": "Aufwaertstrend (Preis > MA20 > MA50)",
        "news_sentiment": "neutral",
        "news_punkte": 0,
        "news_anzahl": 0,
        "gesamt_punkte": 1.5,
        "empfehlung": "KAUFEN",
        "stop_loss": 418.26,
        "ziel": 484.30,
        "begruendung": [
            "Technisch: KAUFEN (RSI=67.84, MACD=positiv)",
            "News (0 Artikel): Sentiment NEUTRAL",
        ],
    }

    print("Trading Intelligence System - Revisions-Agent (KI)")
    print("Analysiere MSFT mit Llama 3.3 70B...\n")

    ergebnis = analysiere_mit_ki(test_signal)
    drucke_ki_analyse(ergebnis)
