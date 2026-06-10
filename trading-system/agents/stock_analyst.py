"""
Aktien-Analyst Agent — Phase 1
Lädt Kursdaten und berechnet technische Indikatoren (RSI, MACD, Moving Averages).
"""

import sys
import yfinance as yf
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def lade_kursdaten(ticker: str, zeitraum: str = "3mo") -> pd.DataFrame:
    """Lädt historische Kursdaten für einen Ticker (z.B. 'AAPL', 'MSFT')."""
    aktie = yf.Ticker(ticker)
    df = aktie.history(period=zeitraum)
    return df


def berechne_indikatoren(df: pd.DataFrame) -> pd.DataFrame:
    """Berechnet RSI, MACD und Moving Averages."""
    # Moving Averages
    df["MA20"] = df["Close"].rolling(window=20).mean()
    df["MA50"] = df["Close"].rolling(window=50).mean()

    # RSI (Relative Strength Index)
    delta = df["Close"].diff()
    gewinn = delta.clip(lower=0)
    verlust = -delta.clip(upper=0)
    avg_gewinn = gewinn.rolling(window=14).mean()
    avg_verlust = verlust.rolling(window=14).mean()
    rs = avg_gewinn / avg_verlust
    df["RSI"] = 100 - (100 / (1 + rs))

    # MACD
    ema12 = df["Close"].ewm(span=12, adjust=False).mean()
    ema26 = df["Close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = ema12 - ema26
    df["MACD_Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()

    return df


def erstelle_einschaetzung(ticker: str, df: pd.DataFrame) -> dict:
    """Erstellt eine erste Einschätzung basierend auf den Indikatoren."""
    letzter = df.iloc[-1]
    preis = letzter["Close"]
    rsi = letzter["RSI"]
    macd = letzter["MACD"]
    macd_signal = letzter["MACD_Signal"]
    ma20 = letzter["MA20"]
    ma50 = letzter["MA50"]

    signale = []
    punkte = 0  # positiv = bullish, negativ = bearish

    # RSI-Bewertung
    if rsi < 30:
        signale.append("RSI ueberverkauft (<30) => bullishes Signal")
        punkte += 2
    elif rsi > 70:
        signale.append("RSI ueberkauft (>70) => bearishes Signal")
        punkte -= 2
    else:
        signale.append(f"RSI neutral ({rsi:.1f})")

    # MACD-Bewertung
    if macd > macd_signal:
        signale.append("MACD ueber Signal-Linie => bullishes Signal")
        punkte += 1
    else:
        signale.append("MACD unter Signal-Linie => bearishes Signal")
        punkte -= 1

    # Moving Average Trend
    if preis > ma20 > ma50:
        signale.append("Preis ueber MA20 & MA50 => Aufwaertstrend")
        punkte += 2
    elif preis < ma20 < ma50:
        signale.append("Preis unter MA20 & MA50 => Abwaertstrend")
        punkte -= 2
    else:
        signale.append("Moving Averages gemischt => Seitwärtstrend")

    # Gesamteinschätzung
    if punkte >= 3:
        empfehlung = "KAUFEN"
    elif punkte <= -3:
        empfehlung = "VERKAUFEN"
    else:
        empfehlung = "HALTEN / ABWARTEN"

    return {
        "ticker": ticker,
        "preis": round(preis, 2),
        "rsi": round(rsi, 2),
        "macd": round(macd, 4),
        "ma20": round(ma20, 2),
        "ma50": round(ma50, 2),
        "signale": signale,
        "punkte": punkte,
        "empfehlung": empfehlung,
    }


def analysiere_aktie(ticker: str) -> dict:
    """Hauptfunktion: Analysiert eine Aktie komplett."""
    print(f"  Lade Daten für {ticker}...")
    df = lade_kursdaten(ticker)
    df = berechne_indikatoren(df)
    ergebnis = erstelle_einschaetzung(ticker, df)
    return ergebnis


def drucke_bericht(ergebnis: dict):
    """Gibt den Analysebericht lesbar aus."""
    print("\n" + "=" * 50)
    print(f"  AKTIEN-ANALYSE: {ergebnis['ticker']}")
    print("=" * 50)
    print(f"  Aktueller Preis : ${ergebnis['preis']}")
    print(f"  RSI             : {ergebnis['rsi']}")
    print(f"  MACD            : {ergebnis['macd']}")
    print(f"  MA20            : ${ergebnis['ma20']}")
    print(f"  MA50            : ${ergebnis['ma50']}")
    print("\n  Signale:")
    for signal in ergebnis["signale"]:
        print(f"    - {signal}")
    print(f"\n  EMPFEHLUNG: >> {ergebnis['empfehlung']} <<")
    print("=" * 50)


if __name__ == "__main__":
    # Test mit drei bekannten Aktien
    test_ticker = ["AAPL", "MSFT", "NVDA"]

    print("Trading Intelligence System — Phase 1")
    print("Aktien-Analyst startet...\n")

    for ticker in test_ticker:
        ergebnis = analysiere_aktie(ticker)
        drucke_bericht(ergebnis)
