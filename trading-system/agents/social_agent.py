"""
Social Media Agent -- Phase 4
Wertet drei kostenfreie Quellen aus:
  1. Google Trends   -- Suchinteresse fuer Assets (pytrends)
  2. Reddit RSS      -- Stimmung in r/wallstreetbets, r/CryptoCurrency etc.
  3. StockTwits API  -- Dediziertes Finanz-Sentiment (Bull/Bear-Verhaeltnis)
"""

import sys
import time
import re
import requests
import feedparser
from dataclasses import dataclass, field
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


# ---------------------------------------------------------------------------
# Datenstruktur
# ---------------------------------------------------------------------------

@dataclass
class SocialSignal:
    asset: str
    google_trend_score: int          # 0-100 (Suchinteresse relativ)
    google_trend_richtung: str       # "steigend", "fallend", "neutral"
    reddit_posts: int                # Anzahl relevanter Posts heute
    reddit_sentiment: str            # "bullish", "bearish", "neutral"
    reddit_punkte: int
    stocktwits_bullish_pct: float    # Anteil Bullen in % (0-100)
    stocktwits_bearish_pct: float
    stocktwits_sentiment: str        # "bullish", "bearish", "neutral"
    gesamt_sentiment: str
    gesamt_punkte: float
    quellen: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Asset-Konfiguration
# ---------------------------------------------------------------------------

# Google Trends Suchbegriffe pro Asset
TRENDS_BEGRIFFE = {
    "BTC":   "Bitcoin",
    "ETH":   "Ethereum",
    "SOL":   "Solana crypto",
    "XRP":   "XRP Ripple",
    "DOGE":  "Dogecoin",
    "AAPL":  "Apple stock",
    "MSFT":  "Microsoft stock",
    "NVDA":  "Nvidia stock",
    "TSLA":  "Tesla stock",
    "AMZN":  "Amazon stock",
}

# StockTwits Symbole (Aktien mit $, Krypto ohne Aenderung)
STOCKTWITS_SYMBOLE = {
    "BTC":  "BTC.X",
    "ETH":  "ETH.X",
    "SOL":  "SOL.X",
    "XRP":  "XRP.X",
    "DOGE": "DOGE.X",
    "AAPL": "AAPL",
    "MSFT": "MSFT",
    "NVDA": "NVDA",
    "TSLA": "TSLA",
    "AMZN": "AMZN",
}

# Reddit-Subreddits nach Kategorie
REDDIT_QUELLEN = {
    "aktie":  ["wallstreetbets", "stocks", "investing", "StockMarket"],
    "krypto": ["CryptoCurrency", "Bitcoin", "ethereum", "CryptoMarkets"],
}

# Sentiment-Keywords (wiederverwendet aus news_agent-Logik)
BULLISH_KW = [
    "moon", "bull", "buy", "long", "surge", "rally", "pump", "gain",
    "breakout", "all time high", "ath", "bullish", "calls", "yolo",
    "to the moon", "hold", "hodl", "accumulate", "dip buy",
]
BEARISH_KW = [
    "crash", "bear", "sell", "short", "dump", "drop", "fall", "panic",
    "rekt", "loss", "puts", "bearish", "correction", "bubble", "scam",
    "rug", "dead", "avoid", "overvalued",
]


# ---------------------------------------------------------------------------
# 1. Google Trends
# ---------------------------------------------------------------------------

def hole_google_trends(asset: str) -> tuple[int, str]:
    """
    Gibt (Score 0-100, Richtung) zurueck.
    Score = aktuelles Interesse relativ zum Jahreshoch.
    Richtung = Vergleich letzte 3 Tage vs. vorherige 3 Tage.
    """
    try:
        from pytrends.request import TrendReq
        trends = TrendReq(hl="de-DE", tz=60, timeout=(10, 25))
        suchbegriff = TRENDS_BEGRIFFE.get(asset, asset)
        trends.build_payload([suchbegriff], timeframe="today 3-m", geo="")
        df = trends.interest_over_time()

        if df.empty or suchbegriff not in df.columns:
            return 0, "neutral"

        werte = df[suchbegriff].dropna()
        if len(werte) < 7:
            return int(werte.iloc[-1]), "neutral"

        aktuell  = werte.iloc[-3:].mean()
        vorher   = werte.iloc[-7:-3].mean()
        score    = int(werte.iloc[-1])

        if aktuell > vorher * 1.15:
            richtung = "steigend"
        elif aktuell < vorher * 0.85:
            richtung = "fallend"
        else:
            richtung = "neutral"

        return score, richtung

    except Exception as e:
        return 0, "neutral"


# ---------------------------------------------------------------------------
# 2. Reddit RSS
# ---------------------------------------------------------------------------

def hole_reddit_posts(asset: str, asset_typ: str = "aktie") -> tuple[int, str, int]:
    """
    Liest Reddit-Posts der letzten 24h via RSS und bewertet das Sentiment.
    Gibt (anzahl_posts, sentiment_label, punkte) zurueck.
    """
    subreddits = REDDIT_QUELLEN.get(asset_typ, REDDIT_QUELLEN["aktie"])
    keywords   = [asset.lower(), TRENDS_BEGRIFFE.get(asset, asset).lower().split()[0]]

    alle_titel = []
    for sub in subreddits:
        try:
            url  = f"https://www.reddit.com/r/{sub}/hot.json?limit=25"
            resp = requests.get(url, headers={"User-Agent": "trading-bot/1.0"}, timeout=10)
            if resp.status_code != 200:
                # Fallback auf RSS
                feed = feedparser.parse(f"https://www.reddit.com/r/{sub}/.rss")
                titel = [e.get("title", "") for e in feed.entries[:25]]
            else:
                daten = resp.json().get("data", {}).get("children", [])
                titel = [d["data"].get("title", "") for d in daten]

            alle_titel.extend(titel)
            time.sleep(0.5)
        except Exception:
            continue

    # Nur Posts die unser Asset erwaehnen
    relevante = [t for t in alle_titel if any(kw in t.lower() for kw in keywords)]

    if not relevante:
        return 0, "neutral", 0

    punkte = 0
    for titel in relevante:
        text = titel.lower()
        punkte += sum(1 for kw in BULLISH_KW if kw in text)
        punkte -= sum(1 for kw in BEARISH_KW if kw in text)

    if punkte >= 2:
        sentiment = "bullish"
    elif punkte <= -2:
        sentiment = "bearish"
    else:
        sentiment = "neutral"

    return len(relevante), sentiment, punkte


# ---------------------------------------------------------------------------
# 3. StockTwits
# ---------------------------------------------------------------------------

def hole_stocktwits(asset: str) -> tuple[float, float, str]:
    """
    Ruft die StockTwits-Sentiment-Daten ab.
    Gibt (bullish_pct, bearish_pct, sentiment_label) zurueck.
    """
    symbol = STOCKTWITS_SYMBOLE.get(asset, asset)
    url    = f"https://api.stocktwits.com/api/2/streams/symbol/{symbol}.json"

    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return 50.0, 50.0, "neutral"

        nachrichten = resp.json().get("messages", [])
        if not nachrichten:
            return 50.0, 50.0, "neutral"

        bullish = sum(1 for m in nachrichten
                      if m.get("entities", {}).get("sentiment", {}) and
                         m["entities"]["sentiment"].get("basic") == "Bullish")
        bearish = sum(1 for m in nachrichten
                      if m.get("entities", {}).get("sentiment", {}) and
                         m["entities"]["sentiment"].get("basic") == "Bearish")

        gesamt = bullish + bearish
        if gesamt == 0:
            return 50.0, 50.0, "neutral"

        bull_pct = round(bullish / gesamt * 100, 1)
        bear_pct = round(bearish / gesamt * 100, 1)

        if bull_pct >= 65:
            label = "bullish"
        elif bear_pct >= 65:
            label = "bearish"
        else:
            label = "neutral"

        return bull_pct, bear_pct, label

    except Exception:
        return 50.0, 50.0, "neutral"


# ---------------------------------------------------------------------------
# Gesamtbewertung
# ---------------------------------------------------------------------------

def bewerte_social(asset: str, asset_typ: str = "aktie") -> SocialSignal:
    """Fuehrt alle drei Quellen zusammen und gibt ein Gesamtsignal zurueck."""

    # Google Trends
    trend_score, trend_richtung = hole_google_trends(asset)
    time.sleep(1)

    # Reddit
    reddit_anzahl, reddit_sentiment, reddit_punkte = hole_reddit_posts(asset, asset_typ)
    time.sleep(1)

    # StockTwits
    bull_pct, bear_pct, stocktwits_sentiment = hole_stocktwits(asset)

    # Gesamtpunkte berechnen
    punkte = 0.0
    quellen = []

    # Google Trends: steigende Suchen = Aufmerksamkeit = leicht bullish
    if trend_richtung == "steigend" and trend_score > 30:
        punkte += 1.0
        quellen.append(f"Google Trends: {trend_score}/100, steigend")
    elif trend_richtung == "fallend":
        punkte -= 0.5
        quellen.append(f"Google Trends: {trend_score}/100, fallend")
    else:
        quellen.append(f"Google Trends: {trend_score}/100, neutral")

    # Reddit
    if reddit_sentiment == "bullish":
        punkte += 1.5
    elif reddit_sentiment == "bearish":
        punkte -= 1.5
    quellen.append(f"Reddit: {reddit_anzahl} Posts, {reddit_sentiment}")

    # StockTwits
    if stocktwits_sentiment == "bullish":
        punkte += 1.5
    elif stocktwits_sentiment == "bearish":
        punkte -= 1.5
    quellen.append(f"StockTwits: {bull_pct}% Bull / {bear_pct}% Bear")

    if punkte >= 1.5:
        gesamt = "bullish"
    elif punkte <= -1.5:
        gesamt = "bearish"
    else:
        gesamt = "neutral"

    return SocialSignal(
        asset=asset,
        google_trend_score=trend_score,
        google_trend_richtung=trend_richtung,
        reddit_posts=reddit_anzahl,
        reddit_sentiment=reddit_sentiment,
        reddit_punkte=reddit_punkte,
        stocktwits_bullish_pct=bull_pct,
        stocktwits_bearish_pct=bear_pct,
        stocktwits_sentiment=stocktwits_sentiment,
        gesamt_sentiment=gesamt,
        gesamt_punkte=round(punkte, 2),
        quellen=quellen,
    )


# ---------------------------------------------------------------------------
# Ausgabe
# ---------------------------------------------------------------------------

def drucke_social_bericht(sig: SocialSignal):
    breite = 62
    print("\n" + "=" * breite)
    print(f"  SOCIAL MEDIA ANALYSE: {sig.asset}")
    print("=" * breite)
    for q in sig.quellen:
        print(f"  {q}")
    print(f"\n  Gesamt-Sentiment : {sig.gesamt_sentiment.upper()}")
    print(f"  Gesamt-Punkte    : {sig.gesamt_punkte:+.2f}")
    print("=" * breite)


# ---------------------------------------------------------------------------
# Einstiegspunkt
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Trading Intelligence System - Social Media Agent")
    print("Analysiere: MSFT, TSLA, BTC, ETH\n")

    test_assets = [
        ("MSFT", "aktie"),
        ("TSLA", "aktie"),
        ("BTC",  "krypto"),
        ("ETH",  "krypto"),
    ]

    for asset, typ in test_assets:
        print(f"  -> {asset} ...", end=" ", flush=True)
        sig = bewerte_social(asset, typ)
        print("OK")
        drucke_social_bericht(sig)
