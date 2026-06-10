"""
Krypto-Analyst Agent -- Phase 1
Holt Kursdaten von CoinGecko (kostenlos, kein API-Key noetig) und
berechnet dieselben technischen Indikatoren wie der Aktien-Agent.
"""

import sys
import time
import requests
import pandas as pd
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


COINGECKO_BASE = "https://api.coingecko.com/api/v3"

# Mapping: lesbarer Name -> CoinGecko-ID
KRYPTO_IDS = {
    "BTC":  "bitcoin",
    "ETH":  "ethereum",
    "SOL":  "solana",
    "BNB":  "binancecoin",
    "XRP":  "ripple",
    "ADA":  "cardano",
    "DOGE": "dogecoin",
}


def _netzwerk_verfuegbar() -> bool:
    import socket
    try:
        socket.setdefaulttimeout(5)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
        return True
    except Exception:
        return False


def _get_mit_retry(url: str, params: dict, versuche: int = 3) -> requests.Response:
    """GET-Anfrage mit automatischem Retry bei Rate-Limit (429)."""
    for versuch in range(versuche):
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 429:
            wartezeit = 15 * (versuch + 1)
            print(f"    Rate-Limit erreicht, warte {wartezeit}s...")
            time.sleep(wartezeit)
            continue
        response.raise_for_status()
        return response
    raise Exception("Rate-Limit nach mehreren Versuchen nicht ueberwunden.")


def lade_kursdaten(symbol: str, tage: int = 90) -> pd.DataFrame:
    """Laedt taegl. Schlusskurse von CoinGecko fuer die letzten `tage` Tage."""
    coin_id = KRYPTO_IDS.get(symbol.upper(), symbol.lower())
    url = f"{COINGECKO_BASE}/coins/{coin_id}/market_chart"
    params = {"vs_currency": "usd", "days": tage, "interval": "daily"}

    response = _get_mit_retry(url, params)

    # Liefert: {"prices": [[timestamp, preis], ...], ...}
    preise = response.json()["prices"]
    df = pd.DataFrame(preise, columns=["timestamp", "Close"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)
    # OHLC simulieren (vereinfacht -- Open = vorheriger Close)
    df["Open"] = df["Close"].shift(1)
    df["High"] = df["Close"]
    df["Low"] = df["Close"]
    return df


def lade_aktuellen_preis(symbol: str) -> dict:
    """Holt den aktuellen Preis, 24h-Veraenderung und Marktkapitalisierung."""
    coin_id = KRYPTO_IDS.get(symbol.upper(), symbol.lower())
    url = f"{COINGECKO_BASE}/simple/price"
    params = {
        "ids": coin_id,
        "vs_currencies": "usd",
        "include_24hr_change": "true",
        "include_market_cap": "true",
    }
    response = _get_mit_retry(url, params)
    daten = response.json().get(coin_id, {})
    return {
        "preis": daten.get("usd", 0),
        "change_24h": daten.get("usd_24h_change", 0),
        "marktkapitalisierung": daten.get("usd_market_cap", 0),
    }


def berechne_indikatoren(df: pd.DataFrame) -> pd.DataFrame:
    """Berechnet RSI, MACD und Moving Averages (identisch zum Aktien-Agent)."""
    df["MA20"] = df["Close"].rolling(window=20).mean()
    df["MA50"] = df["Close"].rolling(window=50).mean()

    delta = df["Close"].diff()
    gewinn = delta.clip(lower=0)
    verlust = -delta.clip(upper=0)
    avg_gewinn = gewinn.rolling(window=14).mean()
    avg_verlust = verlust.rolling(window=14).mean()
    rs = avg_gewinn / avg_verlust
    df["RSI"] = 100 - (100 / (1 + rs))

    ema12 = df["Close"].ewm(span=12, adjust=False).mean()
    ema26 = df["Close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = ema12 - ema26
    df["MACD_Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()

    return df


def erstelle_einschaetzung(symbol: str, df: pd.DataFrame, live: dict) -> dict:
    """Erstellt die Einschaetzung -- nutzt Live-Preis fuer Genauigkeit."""
    letzter = df.iloc[-1]
    preis = live["preis"]
    change_24h = live["change_24h"]
    rsi = letzter["RSI"]
    macd = letzter["MACD"]
    macd_signal = letzter["MACD_Signal"]
    ma20 = letzter["MA20"]
    ma50 = letzter["MA50"]

    signale = []
    punkte = 0

    # 24h Momentum
    if change_24h > 5:
        signale.append(f"Starkes 24h-Momentum +{change_24h:.1f}% => bullish")
        punkte += 1
    elif change_24h < -5:
        signale.append(f"Starker 24h-Rueckgang {change_24h:.1f}% => bearish")
        punkte -= 1
    else:
        signale.append(f"24h-Veraenderung: {change_24h:.1f}% (neutral)")

    # RSI
    if rsi < 30:
        signale.append(f"RSI ueberverkauft ({rsi:.1f}) => bullishes Signal")
        punkte += 2
    elif rsi > 70:
        signale.append(f"RSI ueberkauft ({rsi:.1f}) => bearishes Signal")
        punkte -= 2
    else:
        signale.append(f"RSI neutral ({rsi:.1f})")

    # MACD
    if macd > macd_signal:
        signale.append("MACD ueber Signal-Linie => bullishes Signal")
        punkte += 1
    else:
        signale.append("MACD unter Signal-Linie => bearishes Signal")
        punkte -= 1

    # Moving Averages
    if preis > ma20 > ma50:
        signale.append("Preis ueber MA20 & MA50 => Aufwaertstrend")
        punkte += 2
    elif preis < ma20 < ma50:
        signale.append("Preis unter MA20 & MA50 => Abwaertstrend")
        punkte -= 2
    else:
        signale.append("Moving Averages gemischt => Seitwärtstrend")

    if punkte >= 3:
        empfehlung = "KAUFEN"
    elif punkte <= -3:
        empfehlung = "VERKAUFEN"
    else:
        empfehlung = "HALTEN / ABWARTEN"

    # Einfacher Stop-Loss: 5% unter aktuellem Preis
    stop_loss = round(preis * 0.95, 2)
    ziel = round(preis * 1.10, 2)  # Ziel: +10%

    return {
        "symbol": symbol,
        "preis": preis,
        "change_24h": round(change_24h, 2),
        "rsi": round(rsi, 2),
        "macd": round(macd, 4),
        "ma20": round(ma20, 2),
        "ma50": round(ma50, 2),
        "signale": signale,
        "punkte": punkte,
        "empfehlung": empfehlung,
        "stop_loss": stop_loss,
        "ziel": ziel,
    }


def analysiere_krypto(symbol: str) -> dict:
    """Hauptfunktion: Analysiert eine Kryptowaehrung komplett."""
    if not _netzwerk_verfuegbar():
        raise Exception("Kein Netzwerk verfuegbar")
    print(f"  Lade Daten fuer {symbol}...")
    df = lade_kursdaten(symbol)
    df = berechne_indikatoren(df)
    live = lade_aktuellen_preis(symbol)
    ergebnis = erstelle_einschaetzung(symbol, df, live)
    return ergebnis


def drucke_bericht(ergebnis: dict):
    """Gibt den Analysebericht lesbar aus."""
    print("\n" + "=" * 55)
    print(f"  KRYPTO-ANALYSE: {ergebnis['symbol']}")
    print("=" * 55)
    print(f"  Aktueller Preis : ${ergebnis['preis']:,.2f}")
    print(f"  24h Veraenderung: {ergebnis['change_24h']:+.2f}%")
    print(f"  RSI             : {ergebnis['rsi']}")
    print(f"  MACD            : {ergebnis['macd']}")
    print(f"  MA20            : ${ergebnis['ma20']:,.2f}")
    print(f"  MA50            : ${ergebnis['ma50']:,.2f}")
    print("\n  Signale:")
    for signal in ergebnis["signale"]:
        print(f"    - {signal}")
    print(f"\n  EMPFEHLUNG : >> {ergebnis['empfehlung']} <<")
    print(f"  Einstieg   : ${ergebnis['preis']:,.2f}")
    print(f"  Ziel (+10%): ${ergebnis['ziel']:,.2f}")
    print(f"  Stop-Loss  : ${ergebnis['stop_loss']:,.2f}  (-5%)")
    print("=" * 55)


if __name__ == "__main__":
    test_symbole = ["BTC", "ETH", "SOL"]

    print("Trading Intelligence System - Phase 1")
    print("Krypto-Analyst startet...\n")

    for i, symbol in enumerate(test_symbole):
        try:
            ergebnis = analysiere_krypto(symbol)
            drucke_bericht(ergebnis)
            if i < len(test_symbole) - 1:
                time.sleep(2)  # CoinGecko Rate-Limit: 30 Req/Min kostenlos
        except Exception as e:
            print(f"  Fehler bei {symbol}: {e}")
