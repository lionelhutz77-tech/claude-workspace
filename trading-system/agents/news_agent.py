"""
News-Agent -- Phase 3
Liest Finanznachrichten aus RSS-Feeds (Reuters, Yahoo Finance, CNBC, CoinDesk),
erkennt welche Assets betroffen sind und bewertet das Sentiment je Nachricht.
"""

import sys
import time
import re
from datetime import datetime, timezone
from dataclasses import dataclass, field

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import feedparser


# ---------------------------------------------------------------------------
# Datenstrukturen
# ---------------------------------------------------------------------------

@dataclass
class Nachricht:
    titel: str
    zusammenfassung: str
    quelle: str
    url: str
    datum: datetime
    betroffene_assets: list[str] = field(default_factory=list)
    sentiment: str = "neutral"       # "bullish", "bearish", "neutral"
    sentiment_punkte: int = 0
    sentiment_begruendung: str = ""


# ---------------------------------------------------------------------------
# RSS-Quellen
# ---------------------------------------------------------------------------

RSS_QUELLEN = {
    "Reuters Business": "https://feeds.reuters.com/reuters/businessNews",
    "Reuters Finance":  "https://feeds.reuters.com/reuters/financialNews",
    "Yahoo Finance":    "https://finance.yahoo.com/news/rssindex",
    "CNBC Top News":    "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "CNBC Finance":     "https://www.cnbc.com/id/10000664/device/rss/rss.html",
    "CoinDesk":         "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "CoinTelegraph":    "https://cointelegraph.com/rss",
    "Seeking Alpha":    "https://seekingalpha.com/market_currents.xml",
}

# ---------------------------------------------------------------------------
# Asset-Erkennung: Keywords die auf ein Asset hinweisen
# ---------------------------------------------------------------------------

ASSET_KEYWORDS = {
    "BTC":   ["bitcoin", "btc", "satoshi", "crypto", "cryptocurrency", "digital currency"],
    "ETH":   ["ethereum", "eth", "ether", "defi", "smart contract", "erc-20"],
    "SOL":   ["solana", "sol"],
    "XRP":   ["ripple", "xrp"],
    "BNB":   ["binance", "bnb"],
    "DOGE":  ["dogecoin", "doge"],
    "AAPL":  ["apple", "aapl", "iphone", "tim cook", "app store", "mac", "ipad"],
    "MSFT":  ["microsoft", "msft", "azure", "windows", "satya nadella", "xbox"],
    "NVDA":  ["nvidia", "nvda", "gpu", "jensen huang", "cuda", "geforce", "ai chips"],
    "TSLA":  ["tesla", "tsla", "elon musk", "electric vehicle", "ev", "cybertruck"],
    "AMZN":  ["amazon", "amzn", "aws", "jeff bezos", "prime"],
    "GOOGL": ["google", "googl", "alphabet", "youtube", "sundar pichai", "android"],
    "META":  ["meta", "facebook", "instagram", "mark zuckerberg", "whatsapp"],
    "SPY":   ["s&p 500", "s&p500", "spy", "stock market", "wall street", "nasdaq", "dow jones",
              "federal reserve", "fed", "interest rate", "inflation", "recession", "gdp"],
    "GOLD":  ["gold", "xau", "precious metals", "safe haven"],
    "OIL":   ["oil", "crude", "opec", "petroleum", "barrel", "energy"],
}

# ---------------------------------------------------------------------------
# Sentiment-Analyse: Keywords die positives/negatives Sentiment signalisieren
# ---------------------------------------------------------------------------

BULLISH_KEYWORDS = [
    "surge", "soar", "rally", "gain", "rise", "jump", "climb", "record high",
    "all-time high", "ath", "bullish", "buy", "upgrade", "beat expectations",
    "strong earnings", "profit", "growth", "expansion", "partnership",
    "adoption", "investment", "accumulate", "breakout", "recovery",
    "steigt", "steigen", "anstieg", "rekordhoch", "kaufen", "gewinne",
    "wachstum", "erholung", "kursanstieg",
]

BEARISH_KEYWORDS = [
    "crash", "plunge", "drop", "fall", "decline", "tumble", "sink", "dump",
    "bearish", "sell", "downgrade", "miss expectations", "loss", "layoff",
    "bankruptcy", "regulation", "ban", "hack", "exploit", "fraud", "fine",
    "investigation", "lawsuit", "recession", "inflation", "rate hike",
    "faellt", "fallen", "absturz", "verlust", "bankrott", "betrug",
    "regulierung", "verbot", "hack", "klage",
]


# ---------------------------------------------------------------------------
# Kernfunktionen
# ---------------------------------------------------------------------------

def lade_nachrichten(max_pro_quelle: int = 10) -> list[Nachricht]:
    """Laedt Nachrichten aus allen RSS-Quellen."""
    alle_nachrichten = []

    for quelle_name, url in RSS_QUELLEN.items():
        try:
            feed = feedparser.parse(url)
            eintraege = feed.entries[:max_pro_quelle]

            for eintrag in eintraege:
                # Datum parsen (verschiedene Formate je Quelle)
                datum = datetime.now(timezone.utc)
                if hasattr(eintrag, "published_parsed") and eintrag.published_parsed:
                    try:
                        datum = datetime(*eintrag.published_parsed[:6], tzinfo=timezone.utc)
                    except Exception:
                        pass

                zusammenfassung = ""
                if hasattr(eintrag, "summary"):
                    # HTML-Tags entfernen
                    zusammenfassung = re.sub(r"<[^>]+>", "", eintrag.summary)[:500]

                nachricht = Nachricht(
                    titel=eintrag.get("title", ""),
                    zusammenfassung=zusammenfassung,
                    quelle=quelle_name,
                    url=eintrag.get("link", ""),
                    datum=datum,
                )
                alle_nachrichten.append(nachricht)

        except Exception as e:
            print(f"  [Warnung] Fehler beim Laden von {quelle_name}: {e}")

    # Neueste zuerst
    alle_nachrichten.sort(key=lambda n: n.datum, reverse=True)
    return alle_nachrichten


def erkenne_assets(nachricht: Nachricht) -> list[str]:
    """Findet alle Assets die in Titel oder Zusammenfassung erwaehnt werden."""
    text = (nachricht.titel + " " + nachricht.zusammenfassung).lower()
    gefunden = []
    for asset, keywords in ASSET_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            gefunden.append(asset)
    return gefunden


def bewerte_sentiment(nachricht: Nachricht) -> tuple[str, int, str]:
    """
    Bewertet das Sentiment einer Nachricht.
    Gibt zurueck: (sentiment_label, punkte, begruendung)
    """
    text = (nachricht.titel + " " + nachricht.zusammenfassung).lower()

    gefundene_bullish = [kw for kw in BULLISH_KEYWORDS if kw in text]
    gefundene_bearish = [kw for kw in BEARISH_KEYWORDS if kw in text]

    punkte = len(gefundene_bullish) - len(gefundene_bearish)

    if punkte >= 2:
        label = "bullish"
    elif punkte <= -2:
        label = "bearish"
    else:
        label = "neutral"

    begruendung = ""
    if gefundene_bullish:
        begruendung += f"Positive Signalwoerter: {', '.join(gefundene_bullish[:3])}. "
    if gefundene_bearish:
        begruendung += f"Negative Signalwoerter: {', '.join(gefundene_bearish[:3])}."

    return label, punkte, begruendung.strip()


def analysiere_nachrichten(max_pro_quelle: int = 10) -> list[Nachricht]:
    """Hauptfunktion: Laedt alle Nachrichten und reichert sie mit Asset & Sentiment an."""
    print("  Lade Nachrichten aus RSS-Feeds...")
    nachrichten = lade_nachrichten(max_pro_quelle)
    print(f"  {len(nachrichten)} Nachrichten geladen.")

    for n in nachrichten:
        n.betroffene_assets = erkenne_assets(n)
        n.sentiment, n.sentiment_punkte, n.sentiment_begruendung = bewerte_sentiment(n)

    return nachrichten


def filtere_nach_asset(nachrichten: list[Nachricht], asset: str) -> list[Nachricht]:
    """Gibt nur Nachrichten zurueck, die ein bestimmtes Asset betreffen."""
    return [n for n in nachrichten if asset in n.betroffene_assets]


def erstelle_asset_zusammenfassung(nachrichten: list[Nachricht], asset: str) -> dict:
    """Fasst das Sentiment aller Nachrichten zu einem Asset zusammen."""
    relevante = filtere_nach_asset(nachrichten, asset)

    if not relevante:
        return {"asset": asset, "anzahl": 0, "gesamt_sentiment": "neutral",
                "bullish": 0, "bearish": 0, "neutral": 0, "nachrichten": []}

    zaehler = {"bullish": 0, "bearish": 0, "neutral": 0}
    for n in relevante:
        zaehler[n.sentiment] += 1

    gesamt_punkte = sum(n.sentiment_punkte for n in relevante)
    if gesamt_punkte >= 2:
        gesamt_sentiment = "bullish"
    elif gesamt_punkte <= -2:
        gesamt_sentiment = "bearish"
    else:
        gesamt_sentiment = "neutral"

    return {
        "asset": asset,
        "anzahl": len(relevante),
        "gesamt_sentiment": gesamt_sentiment,
        "gesamt_punkte": gesamt_punkte,
        "bullish": zaehler["bullish"],
        "bearish": zaehler["bearish"],
        "neutral": zaehler["neutral"],
        "nachrichten": relevante[:5],  # Top 5 fuer den Bericht
    }


# ---------------------------------------------------------------------------
# Ausgabe
# ---------------------------------------------------------------------------

def drucke_asset_bericht(zusammenfassung: dict):
    """Gibt die Nachrichten-Zusammenfassung fuer ein Asset aus."""
    asset = zusammenfassung["asset"]
    anzahl = zusammenfassung["anzahl"]

    print("\n" + "=" * 60)
    print(f"  NEWS-ANALYSE: {asset}  ({anzahl} relevante Artikel)")
    print("=" * 60)

    if anzahl == 0:
        print("  Keine relevanten Nachrichten gefunden.")
        return

    s = zusammenfassung["gesamt_sentiment"].upper()
    punkte = zusammenfassung["gesamt_punkte"]
    print(f"  Gesamt-Sentiment : {s}  (Punkte: {punkte:+d})")
    print(f"  Bullish / Bearish / Neutral: "
          f"{zusammenfassung['bullish']} / {zusammenfassung['bearish']} / {zusammenfassung['neutral']}")

    print("\n  Top-Nachrichten:")
    for i, n in enumerate(zusammenfassung["nachrichten"], 1):
        sentiment_symbol = {"bullish": "[+]", "bearish": "[-]", "neutral": "[ ]"}
        print(f"\n  {i}. {sentiment_symbol.get(n.sentiment, '[ ]')} [{n.quelle}]")
        print(f"     {n.titel[:80]}")
        if n.sentiment_begruendung:
            print(f"     -> {n.sentiment_begruendung[:100]}")

    print("=" * 60)


# ---------------------------------------------------------------------------
# Einstiegspunkt
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Trading Intelligence System - Phase 3")
    print("News-Agent startet...\n")

    nachrichten = analysiere_nachrichten(max_pro_quelle=15)

    # Berichte fuer ausgewaehlte Assets
    assets_zu_pruefen = ["BTC", "ETH", "NVDA", "AAPL", "TSLA", "SPY"]
    for asset in assets_zu_pruefen:
        zusammenfassung = erstelle_asset_zusammenfassung(nachrichten, asset)
        drucke_asset_bericht(zusammenfassung)
