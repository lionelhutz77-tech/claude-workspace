"""
Bull/Bear-Debatte -- KI-gestuetzt (Groq / Llama 3.3 70B)
Zwei gegensaetzliche Agenten debattieren ueber ein Asset:
  - Bull-Agent: argumentiert fuer Kauf
  - Bear-Agent: argumentiert gegen Kauf
  - Portfolio-Manager: wertet die Debatte aus und faellt die finale Entscheidung
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
MODEL = "llama-3.3-70b-versatile"


# ---------------------------------------------------------------------------
# System-Prompts fuer die drei Rollen
# ---------------------------------------------------------------------------

BULL_SYSTEM = """Du bist ein aggressiver Growth-Investor mit 15 Jahren Erfahrung.
Du suchst aktiv nach Kaufgelegenheiten und argumentierst fuer Einstiege.
Du betonst Wachstumspotenzial, Momentum und positive Katalysatoren.
Sei ueberzeugend aber sachlich. Maximal 5 Stichpunkte, praezise und stark."""

BEAR_SYSTEM = """Du bist ein vorsichtiger Value-Investor und Risikoanalyst mit 15 Jahren Erfahrung.
Du hinterfragst Kaufempfehlungen kritisch und zeigst Risiken auf.
Du betonst Bewertung, Abwaertsrisiken und negative Szenarien.
Sei kritisch aber sachlich. Maximal 5 Stichpunkte, praezise und stark."""

PORTFOLIO_SYSTEM = """Du bist ein erfahrener Portfolio-Manager, der Bull- und Bear-Argumente
objektiv abwaegt und eine finale, risikobewusste Entscheidung trifft.
Du bewertest die Qualitaet der Argumente, nicht nur ihre Anzahl.
Deine Entscheidung ist klar, begruendet und enthalt konkrete Handlungsparameter."""


# ---------------------------------------------------------------------------
# Kernfunktionen
# ---------------------------------------------------------------------------

def _ki_aufruf(system: str, user_prompt: str, max_tokens: int = 400) -> str:
    """Einzelner KI-Aufruf mit gegebenem System-Prompt."""
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
                import time
                wartezeit = 30 * (versuch + 1)
                print(f" [Rate-Limit, warte {wartezeit}s]", end="", flush=True)
                time.sleep(wartezeit)
            else:
                raise


def bull_argument(signal: dict) -> str:
    """Bull-Agent argumentiert fuer das Asset."""
    prompt = f"""Asset: {signal['asset']} ({signal['asset_typ'].upper()}) -- Preis: ${signal['preis']:,.2f}

Daten:
- RSI: {signal.get('rsi', 'n/a')}
- Technisches Signal: {signal['technisches_signal']}
- News-Sentiment: {signal['news_sentiment']}
- 24h-Momentum: {signal.get('change_24h', 'n/a')}%

Liefere deine 5 staerksten Argumente FUER einen Kauf dieses Assets jetzt."""
    return _ki_aufruf(BULL_SYSTEM, prompt)


def bear_argument(signal: dict, bull_text: str) -> str:
    """Bear-Agent konter die Bull-Argumente."""
    prompt = f"""Asset: {signal['asset']} ({signal['asset_typ'].upper()}) -- Preis: ${signal['preis']:,.2f}

Daten:
- RSI: {signal.get('rsi', 'n/a')}
- Technisches Signal: {signal['technisches_signal']}
- News-Sentiment: {signal['news_sentiment']}

Der Bull-Analyst sagt:
{bull_text}

Widerlege diese Argumente und liefere deine 5 staerksten Gruende GEGEN einen Kauf jetzt."""
    return _ki_aufruf(BEAR_SYSTEM, prompt)


def portfolio_entscheidung(signal: dict, bull_text: str, bear_text: str) -> dict:
    """Portfolio-Manager faellt die finale Entscheidung nach der Debatte."""
    ta_signal = signal.get("technisches_signal", "")
    ta_warnung = ""
    if ta_signal == "VERKAUFEN":
        ta_warnung = (
            "\n⚠️ WICHTIG: Die technische Analyse zeigt klar VERKAUFEN. "
            "KAUFEN ist in diesem Fall VERBOTEN — entscheide zwischen VERKAUFEN oder ABWARTEN.\n"
        )

    # Aktive Erkenntnisse aus vergangenen Fehlern laden
    lehren_block = ""
    try:
        from learning_agent import hole_aktive_lehren_als_text
        lehren_raw = hole_aktive_lehren_als_text(3)
        if lehren_raw:
            lehren_block = f"\n{lehren_raw}\n"
    except Exception:
        pass

    prompt = f"""Asset: {signal['asset']} ({signal['asset_typ'].upper()}) -- Preis: ${signal['preis']:,.2f}
Technisches Signal (TA): {ta_signal}
Vorherige Empfehlung des Analyse-Systems: {signal['empfehlung']}
{ta_warnung}{lehren_block}
BULL-ARGUMENTE:
{bull_text}

BEAR-ARGUMENTE:
{bear_text}

Triff eine finale Entscheidung. Wenn das technische Signal positiv ist und die Bull-Argumente ueberwiegen, empfiehl KAUFEN — auch bei leicht gemischten Signalen.
ABWARTEN nur wenn wirklich beide Seiten gleichstark sind. VERKAUFEN nur bei klar negativen Signalen.
Antworte in exakt diesem Format:

GEWINNER: [BULL oder BEAR oder UNENTSCHIEDEN]
BEGRUENDUNG: [2-3 Saetze warum]
EMPFEHLUNG: [KAUFEN oder VERKAUFEN oder ABWARTEN]
EINSTIEG: [aktueller Preis in USD, z.B. {signal['preis']:,.2f}]
ZIEL: [Kursziel in USD — muss hoeher als Einstieg sein bei KAUFEN]
STOP_LOSS: [Stop-Loss in USD — muss niedriger als Einstieg sein bei KAUFEN]
RISIKO: [NIEDRIG oder MITTEL oder HOCH]"""

    text = _ki_aufruf(PORTFOLIO_SYSTEM, prompt, max_tokens=300)

    # Felder aus dem Text parsen
    def extrahiere(label: str, fallback: str) -> str:
        for zeile in text.splitlines():
            if zeile.strip().upper().startswith(label + ":"):
                return zeile.split(":", 1)[-1].strip()
        return fallback

    empfehlung_roh = extrahiere("EMPFEHLUNG", signal["empfehlung"]).upper()
    if "KAUFEN" in empfehlung_roh:
        empfehlung = "KAUFEN"
    elif "VERKAUFEN" in empfehlung_roh:
        empfehlung = "VERKAUFEN"
    else:
        empfehlung = "ABWARTEN"

    # TECHNISCHES VETO: TA-VERKAUFEN kann nicht zu KAUFEN werden
    # Verhindert Wiederholung des BTC-Fehlers vom 31.05.2026
    if signal.get("technisches_signal") == "VERKAUFEN" and empfehlung == "KAUFEN":
        empfehlung = "ABWARTEN"

    def parse_preis(label: str, fallback: float) -> float:
        wert = extrahiere(label, str(fallback))
        try:
            # Entferne $, Leerzeichen, Kommas; behalte Punkt als Dezimaltrennzeichen
            bereinigt = wert.replace("$", "").replace(",", "").strip().split()[0]
            wert_float = float(bereinigt)
            # Plausibilitaetspruefung: Wert darf nicht um Faktor 10+ vom Fallback abweichen
            if fallback > 0 and (wert_float / fallback > 10 or wert_float / fallback < 0.1):
                return fallback
            return wert_float
        except Exception:
            return fallback

    einstieg  = parse_preis("EINSTIEG", signal["preis"])
    ziel      = parse_preis("ZIEL",     signal["ziel"])
    stop      = parse_preis("STOP_LOSS", signal["stop_loss"])

    # Plausibilitaetspruefung: Ziel muss ueber Einstieg, Stop darunter
    if empfehlung == "KAUFEN":
        if ziel <= einstieg:
            ziel = round(einstieg * 1.10, 2)   # Fallback: +10%
        if stop >= einstieg:
            stop = round(einstieg * 0.95, 2)   # Fallback: -5%

    return {
        "gewinner":      extrahiere("GEWINNER", "UNENTSCHIEDEN"),
        "begruendung":   extrahiere("BEGRUENDUNG", ""),
        "empfehlung":    empfehlung,
        "einstieg":      einstieg,
        "ziel":          ziel,
        "stop_loss":     stop,
        "risiko":        extrahiere("RISIKO", "MITTEL"),
        "volltext":      text,
    }


def debatte(signal: dict) -> dict:
    """Fuehrt die komplette Bull/Bear-Debatte durch und gibt das Ergebnis zurueck."""
    ta_signal  = signal.get("technisches_signal", "")
    agg_signal = signal.get("empfehlung", "")

    # Fruehzeitiger Ausstieg: Wenn TA klar VERKAUFEN und Aggregator auch negativ,
    # spart das 2-3 Groq-API-Calls und verhindert faelschliches Ueberstimmen
    if ta_signal == "VERKAUFEN" and agg_signal in ("VERKAUFEN", "HALTEN / ABWARTEN"):
        finale_empf = agg_signal if agg_signal == "VERKAUFEN" else "ABWARTEN"
        return {
            **signal,
            "bull_argumente": "Debatte uebersprungen — TA zeigt klar VERKAUFEN.",
            "bear_argumente": "Technischer Abwaertstrend bestätigt.",
            "finale": {
                "gewinner":    "BEAR",
                "begruendung": "Technische Analyse zeigt klaren Abwaertstrend — Einstieg abgelehnt.",
                "empfehlung":  finale_empf,
                "einstieg":    signal["preis"],
                "ziel":        signal.get("ziel",      signal["preis"] * 1.10),
                "stop_loss":   signal.get("stop_loss", signal["preis"] * 0.95),
                "risiko":      "HOCH",
                "volltext":    "Technisches Veto — Debatte nicht gestartet.",
            },
        }

    bull  = bull_argument(signal)
    bear  = bear_argument(signal, bull)
    fazit = portfolio_entscheidung(signal, bull, bear)

    return {
        **signal,
        "bull_argumente":  bull,
        "bear_argumente":  bear,
        "finale":          fazit,
    }


# ---------------------------------------------------------------------------
# Ausgabe
# ---------------------------------------------------------------------------

def drucke_debatte(ergebnis: dict):
    """Gibt die vollstaendige Debatte strukturiert aus."""
    breite = 65
    asset = ergebnis["asset"]
    preis = ergebnis["preis"]
    fazit = ergebnis["finale"]

    print("\n" + "#" * breite)
    typ = "AKTIE" if ergebnis["asset_typ"] == "aktie" else "KRYPTO"
    print(f"  BULL/BEAR-DEBATTE: [{typ}] {asset}  --  ${preis:,.2f}")
    print("#" * breite)

    print("\n  --- BULL-ARGUMENTE (PRO KAUF) ---")
    for zeile in ergebnis["bull_argumente"].splitlines():
        print(f"  {zeile}")

    print("\n  --- BEAR-ARGUMENTE (CONTRA KAUF) ---")
    for zeile in ergebnis["bear_argumente"].splitlines():
        print(f"  {zeile}")

    print("\n  --- PORTFOLIO-MANAGER ENTSCHEIDUNG ---")
    print(f"  Gewinner   : {fazit['gewinner']}")
    print(f"  Begruendung: {fazit['begruendung']}")
    print(f"  Risiko     : {fazit['risiko']}")
    print()

    empf = fazit["empfehlung"]
    if empf == "KAUFEN":
        print(f"  >> FINALE EMPFEHLUNG: {empf} <<")
        print(f"  Einstieg   : ${fazit['einstieg']:,.2f}")
        print(f"  Ziel       : ${fazit['ziel']:,.2f}")
        print(f"  Stop-Loss  : ${fazit['stop_loss']:,.2f}")
    else:
        print(f"  -- FINALE EMPFEHLUNG: {empf} --")

    print("#" * breite)


# ---------------------------------------------------------------------------
# Einstiegspunkt (Standalone-Test)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    test_signal = {
        "asset":              "TSLA",
        "asset_typ":          "aktie",
        "preis":              430.80,
        "technisches_signal": "KAUFEN",
        "technische_punkte":  3,
        "rsi":                50.94,
        "change_24h":         None,
        "news_sentiment":     "bullish",
        "news_punkte":        5,
        "news_anzahl":        13,
        "gesamt_punkte":      2.10,
        "empfehlung":         "KAUFEN",
        "stop_loss":          409.26,
        "ziel":               473.88,
        "begruendung": [
            "Technisch: KAUFEN (RSI=50.94, MACD=positiv)",
            "News (13 Artikel): Sentiment BULLISH",
        ],
    }

    print("Trading Intelligence System - Bull/Bear-Debatte")
    print("Starte Debatte fuer TSLA...\n")

    ergebnis = debatte(test_signal)
    drucke_debatte(ergebnis)
