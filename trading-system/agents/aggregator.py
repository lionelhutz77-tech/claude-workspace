"""
Aggregator-Agent -- Phase 5 (erste Version)
Fuehrt die Signale aus Technischer Analyse (Aktien/Krypto) und News zusammen
und berechnet ein gewichtetes Gesamtsignal pro Asset.

Gewichtung:
  Technische Analyse  : 50%
  News-Sentiment      : 30%
  24h-Momentum (Krypto): 20%  (nur fuer Krypto-Assets)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import time
from dataclasses import dataclass

from stock_analyst  import analysiere_aktie
from crypto_analyst import analysiere_krypto
from news_agent     import analysiere_nachrichten, erstelle_asset_zusammenfassung
from social_agent   import bewerte_social


# ---------------------------------------------------------------------------
# Datenstruktur fuer das Gesamtsignal
# ---------------------------------------------------------------------------

@dataclass
class Gesamtsignal:
    asset: str
    asset_typ: str              # "aktie" oder "krypto"
    preis: float
    technisches_signal: str     # "KAUFEN" / "HALTEN / ABWARTEN" / "VERKAUFEN"
    technische_punkte: int
    news_sentiment: str         # "bullish" / "bearish" / "neutral"
    news_punkte: int
    news_anzahl: int
    gesamt_punkte: float
    empfehlung: str             # finale Empfehlung
    stop_loss: float
    ziel: float
    begruendung: list[str]


# ---------------------------------------------------------------------------
# Gewichtung & Scoring
# ---------------------------------------------------------------------------

TECHNISCH_GEWICHT   = 0.30
NEWS_GEWICHT        = 0.18
SOCIAL_GEWICHT      = 0.17
EMAIL_GEWICHT       = 0.12
VOLUME_GEWICHT      = 0.13   # Volume & Marktstruktur (OBV, Order Blocks)
MOMENTUM_GEWICHT    = 0.10   # nur Krypto

# Umrechnungstabelle: Text-Signal -> Zahlenwert
SIGNAL_WERT = {
    "KAUFEN":            +3,
    "HALTEN / ABWARTEN":  0,
    "VERKAUFEN":         -3,
    "bullish":           +2,
    "neutral":            0,
    "bearish":           -2,
}

AKTIEN_LISTE = [
    "AAPL", "MSFT", "NVDA", "TSLA", "AMZN", "GOOGL", "META",
    "RHM.DE", "EVK.DE", "ALV.DE", "MC.PA",
    "AMD", "LMT", "SMCI", "XOM",
]
KRYPTO_LISTE = ["BTC", "ETH", "SOL", "BNB", "XRP"]


def berechne_stop_loss(preis: float, empfehlung: str, volatil: bool = False) -> float:
    """Berechnet einen konservativen Stop-Loss."""
    prozent = 0.07 if volatil else 0.05
    return round(preis * (1 - prozent), 2)


def berechne_ziel(preis: float, empfehlung: str, volatil: bool = False) -> float:
    """Berechnet ein realistisches Kursziel."""
    prozent = 0.15 if volatil else 0.10
    return round(preis * (1 + prozent), 2)


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def aggregiere_aktie(ticker: str, nachrichten_cache: list, social_cache: dict = None, email_cache: dict = None) -> Gesamtsignal:
    """Aggregiert alle Signale fuer eine Aktie."""
    ta   = analysiere_aktie(ticker)
    news = erstelle_asset_zusammenfassung(nachrichten_cache, ticker)

    # Social Signal -- aus Cache oder neu laden
    if social_cache and ticker in social_cache:
        social = social_cache[ticker]
    else:
        social = bewerte_social(ticker, "aktie")

    tech_wert   = SIGNAL_WERT.get(ta["empfehlung"], 0)
    news_wert   = SIGNAL_WERT.get(news["gesamt_sentiment"], 0)
    social_wert = SIGNAL_WERT.get(social.gesamt_sentiment, 0) if hasattr(social, "gesamt_sentiment") else 0

    # Email-Signal
    email_info  = (email_cache or {}).get(ticker, {})
    email_sent  = email_info.get("sentiment", "neutral")
    email_wert  = SIGNAL_WERT.get(email_sent, 0)

    gesamt = (tech_wert   * TECHNISCH_GEWICHT +
              news_wert   * NEWS_GEWICHT       +
              social_wert * SOCIAL_GEWICHT     +
              email_wert  * EMAIL_GEWICHT)

    begruendung = []
    begruendung.append(f"Technisch: {ta['empfehlung']} (RSI={ta['rsi']}, MACD={'positiv' if ta['macd'] > 0 else 'negativ'})")
    begruendung.append(f"News ({news['anzahl']} Artikel): Sentiment {news['gesamt_sentiment'].upper()}")
    begruendung.append(f"Social: {social.gesamt_sentiment.upper()} (Trends={social.google_trend_score}, Reddit={social.reddit_posts} Posts)")
    if email_info:
        begruendung.append(f"Email-Report: {email_sent.upper()} — '{email_info.get('betreff','')[:50]}'")

    # Technisches Veto: Wenn TA klar VERKAUFEN zeigt, kein KAUFEN moeglich
    if ta["empfehlung"] == "VERKAUFEN":
        empfehlung = "VERKAUFEN"
    elif gesamt >= 1.2:
        empfehlung = "KAUFEN"
    elif gesamt <= -1.2:
        empfehlung = "VERKAUFEN"
    else:
        empfehlung = "HALTEN / ABWARTEN"

    return Gesamtsignal(
        asset=ticker,
        asset_typ="aktie",
        preis=ta["preis"],
        technisches_signal=ta["empfehlung"],
        technische_punkte=ta["punkte"],
        news_sentiment=news["gesamt_sentiment"],
        news_punkte=news.get("gesamt_punkte", 0),
        news_anzahl=news["anzahl"],
        gesamt_punkte=round(gesamt, 3),
        empfehlung=empfehlung,
        stop_loss=berechne_stop_loss(ta["preis"], empfehlung),
        ziel=berechne_ziel(ta["preis"], empfehlung),
        begruendung=begruendung,
    )


def aggregiere_krypto(symbol: str, nachrichten_cache: list, social_cache: dict = None, email_cache: dict = None) -> Gesamtsignal:
    """Aggregiert alle Signale fuer eine Kryptowaehrung."""
    try:
        ta = analysiere_krypto(symbol)
        time.sleep(3)   # CoinGecko Rate-Limit
    except Exception as e:
        print(f"  [Warnung] Krypto-Daten fuer {symbol} nicht verfuegbar: {e}")
        return None

    news = erstelle_asset_zusammenfassung(nachrichten_cache, symbol)

    # Social Signal -- aus Cache oder neu laden
    if social_cache and symbol in social_cache:
        social = social_cache[symbol]
    else:
        social = bewerte_social(symbol, "krypto")

    tech_wert     = SIGNAL_WERT.get(ta["empfehlung"], 0)
    news_wert     = SIGNAL_WERT.get(news["gesamt_sentiment"], 0)
    social_wert   = SIGNAL_WERT.get(social.gesamt_sentiment, 0) if hasattr(social, "gesamt_sentiment") else 0
    momentum_wert = 1 if ta.get("change_24h", 0) > 2 else (-1 if ta.get("change_24h", 0) < -2 else 0)

    email_info  = (email_cache or {}).get(symbol, {})
    email_sent  = email_info.get("sentiment", "neutral")
    email_wert  = SIGNAL_WERT.get(email_sent, 0)

    gesamt = (tech_wert     * TECHNISCH_GEWICHT +
              news_wert     * NEWS_GEWICHT       +
              social_wert   * SOCIAL_GEWICHT     +
              email_wert    * EMAIL_GEWICHT       +
              momentum_wert * MOMENTUM_GEWICHT)

    begruendung = []
    begruendung.append(f"Technisch: {ta['empfehlung']} (RSI={ta['rsi']})")
    begruendung.append(f"24h-Momentum: {ta.get('change_24h', 0):+.2f}%")
    begruendung.append(f"News ({news['anzahl']} Artikel): Sentiment {news['gesamt_sentiment'].upper()}")
    begruendung.append(f"Social: {social.gesamt_sentiment.upper()} (Trends={social.google_trend_score}, Reddit={social.reddit_posts} Posts)")
    if email_info:
        begruendung.append(f"Email-Report: {email_sent.upper()} — '{email_info.get('betreff','')[:50]}'")

    # Technisches Veto: Wenn TA klar VERKAUFEN zeigt, kein KAUFEN moeglich
    if ta["empfehlung"] == "VERKAUFEN":
        empfehlung = "VERKAUFEN"
    elif gesamt >= 1.2:
        empfehlung = "KAUFEN"
    elif gesamt <= -1.2:
        empfehlung = "VERKAUFEN"
    else:
        empfehlung = "HALTEN / ABWARTEN"

    return Gesamtsignal(
        asset=symbol,
        asset_typ="krypto",
        preis=ta["preis"],
        technisches_signal=ta["empfehlung"],
        technische_punkte=ta["punkte"],
        news_sentiment=news["gesamt_sentiment"],
        news_punkte=news.get("gesamt_punkte", 0),
        news_anzahl=news["anzahl"],
        gesamt_punkte=round(gesamt, 3),
        empfehlung=empfehlung,
        stop_loss=berechne_stop_loss(ta["preis"], empfehlung, volatil=True),
        ziel=berechne_ziel(ta["preis"], empfehlung, volatil=True),
        begruendung=begruendung,
    )


# ---------------------------------------------------------------------------
# Ausgabe
# ---------------------------------------------------------------------------

def drucke_gesamtsignal(sig: Gesamtsignal):
    breite = 62
    print("\n" + "=" * breite)
    typ_label = "AKTIE" if sig.asset_typ == "aktie" else "KRYPTO"
    print(f"  [{typ_label}] {sig.asset}  --  ${sig.preis:,.2f}")
    print("-" * breite)
    print(f"  Technische Analyse : {sig.technisches_signal}")
    print(f"  News-Sentiment     : {sig.news_sentiment.upper()}  ({sig.news_anzahl} Artikel)")
    print(f"  Gesamtpunkte       : {sig.gesamt_punkte:+.2f}")
    print("-" * breite)
    for z in sig.begruendung:
        print(f"  * {z}")
    print("-" * breite)
    empf_symbol = ">>" if sig.empfehlung == "KAUFEN" else ("<<" if sig.empfehlung == "VERKAUFEN" else "--")
    print(f"  EMPFEHLUNG : {empf_symbol} {sig.empfehlung} {empf_symbol}")
    if sig.empfehlung == "KAUFEN":
        print(f"  Einstieg   : ${sig.preis:,.2f}")
        print(f"  Ziel       : ${sig.ziel:,.2f}  ({'+10%' if sig.asset_typ == 'aktie' else '+15%'})")
        print(f"  Stop-Loss  : ${sig.stop_loss:,.2f}  ({'-5%' if sig.asset_typ == 'aktie' else '-7%'})")
    print("=" * breite)


def drucke_tagesbericht(signale: list[Gesamtsignal]):
    """Gibt eine kompakte Uebersichtstabelle aller Signale aus."""
    kaufen    = [s for s in signale if s.empfehlung == "KAUFEN"]
    verkaufen = [s for s in signale if s.empfehlung == "VERKAUFEN"]
    halten    = [s for s in signale if s.empfehlung == "HALTEN / ABWARTEN"]

    print("\n" + "#" * 62)
    print("  TAGES-ZUSAMMENFASSUNG")
    print("#" * 62)

    if kaufen:
        print(f"\n  KAUFEN ({len(kaufen)}):")
        for s in kaufen:
            print(f"    {s.asset:<6} ${s.preis:>10,.2f}  |  Ziel: ${s.ziel:>10,.2f}  |  SL: ${s.stop_loss:>10,.2f}")

    if verkaufen:
        print(f"\n  VERKAUFEN ({len(verkaufen)}):")
        for s in verkaufen:
            print(f"    {s.asset:<6} ${s.preis:>10,.2f}")

    if halten:
        halten_namen = ", ".join(s.asset for s in halten)
        print(f"\n  ABWARTEN: {halten_namen}")

    print("\n" + "#" * 62)


# ---------------------------------------------------------------------------
# Einstiegspunkt
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Trading Intelligence System - Aggregator")
    print("=" * 62)
    print("\nSchritt 1: Nachrichten laden...")
    nachrichten = analysiere_nachrichten(max_pro_quelle=15)

    print(f"\nSchritt 2: Aktien analysieren ({len(AKTIEN_LISTE)} Assets)...")
    alle_signale = []

    for ticker in AKTIEN_LISTE:
        print(f"  -> {ticker}")
        try:
            sig = aggregiere_aktie(ticker, nachrichten)
            alle_signale.append(sig)
        except Exception as e:
            print(f"  [Fehler] {ticker}: {e}")

    print(f"\nSchritt 3: Krypto analysieren ({len(KRYPTO_LISTE)} Assets)...")
    for symbol in KRYPTO_LISTE:
        print(f"  -> {symbol}")
        sig = aggregiere_krypto(symbol, nachrichten)
        if sig:
            alle_signale.append(sig)

    print("\nSchritt 4: Detailberichte...")
    for sig in alle_signale:
        drucke_gesamtsignal(sig)

    drucke_tagesbericht(alle_signale)
