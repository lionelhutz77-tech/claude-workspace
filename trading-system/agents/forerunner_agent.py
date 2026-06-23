"""
Vorläufer-Scanner (Forerunner Agent)
Wöchentlicher Scan: Welche Aktien zeigen jetzt dasselbe frühe Muster
wie AMD 2016–2017 oder NVDA 2022 — bevor der Markt es eingepreist hat?

Frühindikatoren für explosive Kursläufe (aus historischer Analyse):
  1. Neue Technologie schlägt Marktführer in Benchmarks (konkret, nicht Roadmap)
  2. Erster Hyperscaler/Großkunde nennt Produkt öffentlich (Earnings Call)
  3. Neues Revenue-Segment taucht erstmals in Quartalsbericht auf
  4. Tech-Community-Diskurs vor Mainstream-Awareness (Reddit, HN)
  5. RSI 30–55: Momentum beginnt, noch nicht überhitzt
  6. Preis nähert sich MA50 von unten oder gerade darüber — frühe Trendwende
"""

import os
import sys
import time
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
MODEL = "llama-3.3-70b-versatile"


# ---------------------------------------------------------------------------
# Kandidaten-Universum
# ---------------------------------------------------------------------------

KANDIDATEN = [
    # KI-Halbleiter — nächste AMD/NVDA
    {"ticker": "MRVL",   "name": "Marvell Technology",    "sektor": "Halbleiter",
     "these": "Baut Custom AI Chips für Google, AWS und Microsoft — Hyperscaler wollen von NVIDIA unabhängig werden"},
    {"ticker": "LSCC",   "name": "Lattice Semiconductor", "sektor": "Halbleiter",
     "these": "Low-Power FPGAs für Edge-KI, Automotive, Sicherheit — Intel-Konkurrenz in spezialisierten Nischen"},
    {"ticker": "MPWR",   "name": "Monolithic Power Sys.", "sektor": "Halbleiter",
     "these": "Kritische Stromversorgungsinfrastruktur für KI-Chips — jeder H100/MI300 braucht ihre Chips"},
    {"ticker": "ARM",    "name": "ARM Holdings",          "sektor": "Halbleiter",
     "these": "Jeder Chip basiert auf ARM-Architektur — Apple, NVIDIA, Qualcomm zahlen Lizenzgebühren"},
    # KI-Infrastruktur
    {"ticker": "VRT",    "name": "Vertiv Holdings",       "sektor": "Rechenzentrum",
     "these": "Kühlsysteme und Stromversorgung für KI-Rechenzentren — zwingend notwendige Infrastruktur"},
    {"ticker": "DELL",   "name": "Dell Technologies",     "sektor": "Rechenzentrum",
     "these": "Baut und vertreibt KI-Server-Racks — profitiert direkt von jedem NVDA/AMD GPU-Verkauf"},
    {"ticker": "NET",    "name": "Cloudflare",            "sektor": "Netzwerk/KI",
     "these": "Netzwerk-Infrastruktur für KI-Workloads, Workers AI — jede KI-App läuft über ihr Netzwerk"},
    # KI-Software
    {"ticker": "PLTR",   "name": "Palantir Technologies", "sektor": "KI-Software",
     "these": "KI-Analyse für Unternehmen und Regierungen — einziger KI-Anbieter mit echter Regierungs-Pipeline"},
    {"ticker": "SNOW",   "name": "Snowflake",             "sektor": "Daten",
     "these": "Datenwolke — KI braucht Daten, alle KI-Modelle werden auf Snowflake-Daten trainiert"},
    # EU Halbleiter (günstigere Bewertungen)
    {"ticker": "IFX.DE", "name": "Infineon Technologies", "sektor": "EU-Halbleiter",
     "these": "Nach Automotive-Flaute möglicher Rebound: E-Auto-Chips, Industrie-KI, Sicherheitschips"},
    {"ticker": "STM",    "name": "STMicroelectronics",    "sektor": "EU-Halbleiter",
     "these": "EU-Chip-Hersteller für Automotive und IoT — profitiert von EU-Chip-Act"},
    # Wildcards
    {"ticker": "CEVA",   "name": "CEVA Inc.",             "sektor": "KI-IP",
     "these": "Lizenziert KI-IP-Cores — sitzt in jedem Mobilchip, kaum bekannt aber struktureller Moat"},
    # Ad-Tech / Antitrust-Nutzniesser (Lernquelle: Claude Portfolio $MGNI +32%)
    {"ticker": "MGNI",   "name": "Magnite",               "sektor": "Ad-Tech/Streaming",
     "these": "Groesste unabhaengige Streaming-TV-Anzeigenplattform; profitiert direkt von DOJ-Google-Antitrust (jeder 1% Marktanteil = ~$50M Umsatz); KI-Orchestrierung gestartet"},
    {"ticker": "TTD",    "name": "The Trade Desk",        "sektor": "Ad-Tech",
     "these": "Fuehrender programmatischer Werbemarkt; struktureller Nutzniesser wenn Google Ad-Tech aufgebrochen wird"},
    {"ticker": "PUBM",   "name": "PubMatic",              "sektor": "Ad-Tech",
     "these": "Unabhaengige Supply-Side-Plattform; guenstig bewertet, profitiert von Google-Antitrust-Entscheidung"},
]

# Referenzstories für die KI-Bewertung
REFERENZ_STORIES = """
Bewährte Vorläufer-Muster (historisch):
- AMD 2016 bei $2: Neue Zen-CPU-Architektur schlägt Intel → 2 Jahre später $30 (+1400%)
- NVDA 2020 bei $50: Data Center + Gaming Dominanz + Ampere GPU → $300 (+500%)
- TSLA 2019 bei $25: Erster profitabler Quartal, Model 3 Hochlauf → $400 (+1500%)
- MSFT 2016 bei $40: Azure-Cloud-Wachstum unter Satya Nadella → $300 (+650%)
- MGNI 2026 bei $14: Boring Franchise (13x forward earnings), DOJ-Google-Antitrust als
  uneingepreiste Optionalität ("jeder 1% Marktanteil = $50M Umsatz"), KI-Orchestration-Launch
  → +32% in 6 Wochen (bestätigt durch reales $50k-Claude-Portfolio-Experiment)

Gemeinsame Frühindikatoren aller dieser Fälle:
1. Struktureller Vorteil gegenüber etablierten Playern (Technologie, Kosten, Timing)
2. UNPRICED OPTIONALITY: Ein quantifizierbarer Katalysator den der Markt noch nicht eingepreist hat
3. Erster Großkunde bestätigt Produkt öffentlich → validierter Markt
4. Saubere Bilanz / Schuldenabbau / Kredit-Upgrade als Risikoreduktion
5. Wachstum in neuem Segment das Markt noch unterschätzt
6. Bewertung deutlich unter Sektor-Durchschnitt (z.B. 13x vs 25x übliches KGV)
"""


# ---------------------------------------------------------------------------
# Analyse-Funktionen
# ---------------------------------------------------------------------------

def _hole_ta_daten(ticker: str) -> dict | None:
    """Holt technische Daten für einen Kandidaten."""
    try:
        from stock_analyst import analysiere_aktie
        ta = analysiere_aktie(ticker)
        preis = ta["preis"]
        ma50  = ta["ma50"]
        ma20  = ta["ma20"]
        rsi   = ta["rsi"]

        # 52-Wochen-High/Low aus 1-Jahres-Historie (zuverlässiger als fast_info)
        import yfinance as yf
        try:
            df_1y    = yf.Ticker(ticker).history(period="1y")
            hoch_52w = round(float(df_1y["Close"].max()), 2)
            tief_52w = round(float(df_1y["Close"].min()), 2)
        except Exception:
            hoch_52w = tief_52w = preis

        vom_tief = round((preis / tief_52w - 1) * 100, 1) if tief_52w > 0 else 0
        vom_hoch = round((preis / hoch_52w - 1) * 100, 1) if hoch_52w > 0 else 0

        return {
            "preis":    preis,
            "rsi":      rsi,
            "ma20":     ma20,
            "ma50":     ma50,
            "hoch_52w": hoch_52w,
            "tief_52w": tief_52w,
            "vom_tief": vom_tief,
            "vom_hoch": vom_hoch,
            "ta_signal": ta["empfehlung"],
        }
    except Exception as e:
        return None


def _groq_score(kandidat: dict, ta: dict, news_sentiment: str, news_anzahl: int) -> dict:
    """Lässt Groq die AMD-Mustererkennung für einen Kandidaten durchführen."""
    ticker = kandidat["ticker"]
    preis  = ta["preis"]
    ma50   = ta["ma50"]
    abstand_ma50 = round((preis / ma50 - 1) * 100, 1) if ma50 > 0 else 0

    prompt = f"""Du bist ein Growth-Investor der früh in AMD (2016, $2), NVDA (2020, $50) und TSLA (2019, $25) investiert hat.

Analysiere jetzt: {ticker} ({kandidat['name']}) — Sektor: {kandidat['sektor']}
Investment-These: {kandidat['these']}

Aktuelle technische Daten:
- Preis: ${preis:.2f}
- RSI: {ta['rsi']:.1f}
- MA50: ${ma50:.2f} (Preis {abstand_ma50:+.1f}% vom MA50)
- 52W-Tief: ${ta['tief_52w']:.2f} (+{ta['vom_tief']}% darüber)
- 52W-Hoch: ${ta['hoch_52w']:.2f} ({ta['vom_hoch']}% davon)
- TA-Signal: {ta['ta_signal']}
- News-Sentiment: {news_sentiment} ({news_anzahl} Artikel diese Woche)

{REFERENZ_STORIES}

AUFGABE: Bewerte wie stark {ticker} dem Muster dieser historischen Vorläufer ähnelt.

Antworte EXAKT in diesem Format (nichts anderes):
SCORE: [1-10]
FRÜHINDIKATOR: [stärkster Frühindikator in einem Satz]
RISIKO: [Hauptrisiko in einem Satz]
TIMING: [Schätzung wann der Run beginnen könnte, z.B. "6-12 Monate" oder "bereits begonnen"]
VERGLEICH: [welchem historischen Vorläufer ähnelt es am meisten und warum]"""

    try:
        resp = _client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "Du erkennst Aktienmuster früher als der Markt. Sei präzise, nicht schwammig."},
                {"role": "user",   "content": prompt},
            ],
            max_tokens=300,
            temperature=0.25,
        )
        text = resp.choices[0].message.content.strip()

        def extrahiere(label: str) -> str:
            for zeile in text.splitlines():
                if zeile.strip().upper().startswith(label.upper() + ":"):
                    return zeile.split(":", 1)[-1].strip()
            return ""

        score_str = extrahiere("SCORE")
        try:
            score = int(score_str.split("/")[0].strip())
            score = max(1, min(10, score))
        except Exception:
            score = 5

        return {
            "score":          score,
            "fruehindikator": extrahiere("FRÜHINDIKATOR"),
            "risiko":         extrahiere("RISIKO"),
            "timing":         extrahiere("TIMING"),
            "vergleich":      extrahiere("VERGLEICH"),
        }
    except Exception as e:
        return {"score": 5, "fruehindikator": f"Fehler: {e}", "risiko": "", "timing": "", "vergleich": ""}


def analysiere_kandidat(kandidat: dict, nachrichten: list = None) -> dict | None:
    """Vollständige Analyse eines Kandidaten: TA + News + Groq."""
    ticker = kandidat["ticker"]
    if nachrichten is None:
        nachrichten = []

    ta = _hole_ta_daten(ticker)
    if ta is None:
        return None

    # News-Sentiment für diesen Ticker
    news_sentiment = "neutral"
    news_anzahl    = 0
    try:
        from news_agent import erstelle_asset_zusammenfassung
        news = erstelle_asset_zusammenfassung(nachrichten, ticker)
        news_sentiment = news.get("gesamt_sentiment", "neutral")
        news_anzahl    = news.get("anzahl", 0)
    except Exception:
        pass

    groq_result = _groq_score(kandidat, ta, news_sentiment, news_anzahl)

    return {
        "ticker":         ticker,
        "name":           kandidat["name"],
        "sektor":         kandidat["sektor"],
        "these":          kandidat["these"],
        **ta,
        "news_sentiment": news_sentiment,
        **groq_result,
    }


# ---------------------------------------------------------------------------
# Scan-Funktion
# ---------------------------------------------------------------------------

def scanne_vorlaeufer(nachrichten: list = None, kandidaten: list = None) -> list[dict]:
    """
    Scannt alle Kandidaten und gibt nach Score sortierte Liste zurück.
    """
    if nachrichten is None:
        nachrichten = []
    if kandidaten is None:
        kandidaten = KANDIDATEN

    ergebnisse = []
    print(f"\n  VORLÄUFER-SCANNER ({len(kandidaten)} Kandidaten):")
    print("  " + "-" * 50)

    for k in kandidaten:
        ticker = k["ticker"]
        print(f"    -> {ticker:10s} ...", end=" ", flush=True)
        try:
            ergebnis = analysiere_kandidat(k, nachrichten)
            if ergebnis:
                ergebnisse.append(ergebnis)
                print(f"Score {ergebnis['score']}/10  |  {ergebnis['timing'] or '?'}")
            else:
                print("ÜBERSPRUNGEN")
        except Exception as e:
            print(f"FEHLER: {e}")
        time.sleep(2)

    ergebnisse.sort(key=lambda x: x["score"], reverse=True)
    return ergebnisse


# ---------------------------------------------------------------------------
# Ausgabe
# ---------------------------------------------------------------------------

def drucke_vorlaeufer_bericht(ergebnisse: list[dict], top_n: int = 5):
    breite = 65
    print("\n" + "=" * breite)
    print("  VORLÄUFER-SCANNER — FRÜHE AMD/NVDA-MUSTER")
    print("  (Aktien die jetzt so aussehen könnten wie AMD 2016)")
    print("=" * breite)

    for i, e in enumerate(ergebnisse[:top_n], 1):
        score = e["score"]
        balken = "█" * score + "░" * (10 - score)
        print(f"\n  #{i}  {e['ticker']:8s}  {e['name']}")
        print(f"       Score:  {balken}  {score}/10")
        print(f"       Sektor: {e['sektor']}")
        print(f"       Preis:  ${e['preis']:,.2f}  |  RSI: {e['rsi']:.1f}  |  52W-Tief +{e['vom_tief']}%")
        print(f"       These:  {e['these'][:80]}...")
        print(f"       Früh:   {e['fruehindikator']}")
        print(f"       Risiko: {e['risiko']}")
        print(f"       Timing: {e['timing']}")
        print(f"       Ähnelt: {e['vergleich']}")

    if len(ergebnisse) > top_n:
        rest = ergebnisse[top_n:]
        print(f"\n  Weitere Kandidaten ({len(rest)}): " +
              ", ".join(f"{e['ticker']}({e['score']})" for e in rest))
    print("\n" + "=" * breite)


def vorlaeufer_als_telegram_text(ergebnisse: list[dict], top_n: int = 3) -> str:
    """Formatiert den Vorläufer-Bericht für Telegram."""
    jetzt = __import__("datetime").datetime.now().strftime("%d.%m.%Y")
    zeilen = [
        f"🔍 <b>VORLÄUFER-SCANNER — {jetzt}</b>",
        "Aktien mit frühem AMD/NVDA-Muster:\n",
    ]

    for i, e in enumerate(ergebnisse[:top_n], 1):
        score = e["score"]
        balken = "🟩" * score + "⬜" * (10 - score)
        zeilen.append(
            f"<b>#{i} {e['ticker']} — {e['name']}</b>\n"
            f"{balken} {score}/10\n"
            f"Preis: ${e['preis']:,.2f} | RSI: {e['rsi']:.1f}\n"
            f"📌 {e['fruehindikator']}\n"
            f"⚠️ {e['risiko']}\n"
            f"⏱ Timing: {e['timing']}\n"
        )

    zeilen.append("⚠️ Kein Anlageratschlag — Modell-Output des Systems.")
    return "\n".join(zeilen)
