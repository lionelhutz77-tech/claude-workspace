"""
Pattern-Agent — Fortgeschrittene Technische Analyse
Erkennt Kerzenmuster, Fibonacci-Level, Stochastik, Support/Resistance
und Elliott-Wave-aehnliche Strukturen.

Erkannte Muster:
  Kerzenmuster : Hammer, Doji, Engulfing, Morning/Evening Star, Shooting Star
  Fibonacci    : Retracement-Level 23.6%, 38.2%, 50%, 61.8%, 78.6%
  Stochastik   : %K und %D Crossover, Overbought/Oversold
  Bollinger    : Squeeze, Breakout
  Support/Res  : Horizontale Zonen aus Hochs und Tiefs
  Trend        : Higher Highs/Lows (Aufwaerts), Lower Highs/Lows (Abwaerts)
"""

import sys
import warnings
warnings.filterwarnings("ignore")

from dataclasses import dataclass, field

import yfinance as yf
import pandas as pd
import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


# ---------------------------------------------------------------------------
# Datenstruktur
# ---------------------------------------------------------------------------

@dataclass
class PatternErgebnis:
    asset: str
    preis: float

    # Kerzenmuster
    kerzenmuster: list[str] = field(default_factory=list)

    # Fibonacci
    fib_naechstes_level: float = 0.0
    fib_level_name: str = ""
    fib_richtung: str = ""          # "support" oder "resistance"

    # Stochastik
    stoch_k: float = 0.0
    stoch_d: float = 0.0
    stoch_signal: str = "neutral"   # "kaufen", "verkaufen", "neutral"

    # Bollinger Bands
    bb_position: str = "mitte"      # "unten", "mitte", "oben", "squeeze"
    bb_breite_pct: float = 0.0

    # Support/Resistance
    naechster_support: float = 0.0
    naechster_widerstand: float = 0.0
    abstand_support_pct: float = 0.0
    abstand_widerstand_pct: float = 0.0

    # Trend-Struktur
    trend_struktur: str = "neutral"  # "aufwaerts", "abwaerts", "neutral"
    swing_punkte: list[float] = field(default_factory=list)

    # Gesamt-Score
    pattern_punkte: int = 0
    pattern_empfehlung: str = "ABWARTEN"
    zusammenfassung: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Kerzenmuster
# ---------------------------------------------------------------------------

def erkenne_kerzenmuster(df: pd.DataFrame) -> list[str]:
    """Erkennt gaengige Kerzenmuster in den letzten 3 Kerzen."""
    muster = []
    if len(df) < 3:
        return muster

    # Letzte 3 Kerzen
    c1 = df.iloc[-3]  # vorvorletzte
    c2 = df.iloc[-2]  # vorletzte
    c3 = df.iloc[-1]  # letzte (heute)

    def koerper(c):
        return abs(c["Close"] - c["Open"])

    def gesamtrange(c):
        return c["High"] - c["Low"]

    def ist_bullish(c):
        return c["Close"] > c["Open"]

    def ist_bearish(c):
        return c["Close"] < c["Open"]

    def oberer_docht(c):
        return c["High"] - max(c["Open"], c["Close"])

    def unterer_docht(c):
        return min(c["Open"], c["Close"]) - c["Low"]

    # --- Einzelne Kerze (c3) ---

    # Doji: Koerper sehr klein im Verhaeltnis zur Gesamtrange
    if gesamtrange(c3) > 0 and koerper(c3) / gesamtrange(c3) < 0.1:
        muster.append("Doji (Unentschlossenheit — Trendwende moeglich)")

    # Hammer: Kleiner Koerper oben, langer unterer Docht (bullish)
    if (unterer_docht(c3) > koerper(c3) * 2 and
            oberer_docht(c3) < koerper(c3) * 0.5 and
            ist_bullish(c3)):
        muster.append("Hammer (Bullish — potenzielle Trendumkehr nach unten)")

    # Shooting Star: Kleiner Koerper unten, langer oberer Docht (bearish)
    if (oberer_docht(c3) > koerper(c3) * 2 and
            unterer_docht(c3) < koerper(c3) * 0.5 and
            ist_bearish(c3)):
        muster.append("Shooting Star (Bearish — potenzielle Trendumkehr nach oben)")

    # Marubozu: Sehr langer Koerper ohne Doechte (starker Trend)
    if gesamtrange(c3) > 0 and koerper(c3) / gesamtrange(c3) > 0.9:
        richtung = "Bullish" if ist_bullish(c3) else "Bearish"
        muster.append(f"Marubozu ({richtung} — starker Momentum-Schub)")

    # --- Zwei Kerzen ---

    # Bullish Engulfing: bearishe Kerze, dann groessere bullishe Kerze
    if (ist_bearish(c2) and ist_bullish(c3) and
            c3["Open"] < c2["Close"] and c3["Close"] > c2["Open"]):
        muster.append("Bullish Engulfing (Starkes Kaufsignal — Bullen uebernehmen)")

    # Bearish Engulfing: bullishe Kerze, dann groessere bearishe Kerze
    if (ist_bullish(c2) and ist_bearish(c3) and
            c3["Open"] > c2["Close"] and c3["Close"] < c2["Open"]):
        muster.append("Bearish Engulfing (Starkes Verkaufssignal — Baeren uebernehmen)")

    # --- Drei Kerzen ---

    # Morning Star: Bearish, Doji/klein, Bullish (starkes Kaufsignal)
    if (ist_bearish(c1) and
            koerper(c2) < koerper(c1) * 0.3 and
            ist_bullish(c3) and
            c3["Close"] > (c1["Open"] + c1["Close"]) / 2):
        muster.append("Morning Star (Sehr starkes Kaufsignal — Bodenbildung)")

    # Evening Star: Bullish, Doji/klein, Bearish (starkes Verkaufssignal)
    if (ist_bullish(c1) and
            koerper(c2) < koerper(c1) * 0.3 and
            ist_bearish(c3) and
            c3["Close"] < (c1["Open"] + c1["Close"]) / 2):
        muster.append("Evening Star (Starkes Verkaufssignal — Topbildung)")

    # Three White Soldiers: 3 bullishe Kerzen mit hoeheren Schlusskursen
    if (ist_bullish(c1) and ist_bullish(c2) and ist_bullish(c3) and
            c2["Close"] > c1["Close"] and c3["Close"] > c2["Close"]):
        muster.append("Three White Soldiers (Starker Aufwaertstrend bestätigt)")

    # Three Black Crows: 3 bearishe Kerzen mit niedrigeren Schlusskursen
    if (ist_bearish(c1) and ist_bearish(c2) and ist_bearish(c3) and
            c2["Close"] < c1["Close"] and c3["Close"] < c2["Close"]):
        muster.append("Three Black Crows (Starker Abwaertstrend bestätigt)")

    return muster


# ---------------------------------------------------------------------------
# Fibonacci Retracements
# ---------------------------------------------------------------------------

FIB_LEVEL = {
    "23.6%": 0.236,
    "38.2%": 0.382,
    "50.0%": 0.500,
    "61.8%": 0.618,
    "78.6%": 0.786,
}

def berechne_fibonacci(df: pd.DataFrame, preis: float) -> tuple[float, str, str]:
    """
    Berechnet Fibonacci-Retracements vom letzten signifikanten Swing.
    Gibt (naechstes_level, level_name, richtung) zurueck.
    """
    if len(df) < 20:
        return 0.0, "", ""

    # Swing High und Low der letzten 50 Tage
    periode = df.iloc[-50:]
    swing_high = float(periode["High"].max())
    swing_low  = float(periode["Low"].min())
    spanne     = swing_high - swing_low

    if spanne <= 0:
        return 0.0, "", ""

    # Fibonacci-Level berechnen (von unten nach oben)
    fib_preise = {
        name: swing_low + spanne * (1 - wert)
        for name, wert in FIB_LEVEL.items()
    }

    # Naechstgelegenes Level finden
    naechstes_level = None
    naechster_name  = ""
    min_abstand     = float("inf")

    for name, level_preis in fib_preise.items():
        abstand = abs(preis - level_preis)
        if abstand < min_abstand:
            min_abstand    = abstand
            naechstes_level = level_preis
            naechster_name  = name

    # Ist der aktuelle Preis ueber oder unter dem Level?
    richtung = "support" if preis > naechstes_level else "resistance"

    return round(naechstes_level, 2), naechster_name, richtung


# ---------------------------------------------------------------------------
# Stochastik (%K und %D)
# ---------------------------------------------------------------------------

def berechne_stochastik(df: pd.DataFrame, k_periode: int = 14, d_periode: int = 3) -> tuple[float, float, str]:
    """
    Berechnet Stochastic Oscillator.
    Gibt (%K, %D, Signal) zurueck.
    """
    if len(df) < k_periode + d_periode:
        return 0.0, 0.0, "neutral"

    low_min  = df["Low"].rolling(k_periode).min()
    high_max = df["High"].rolling(k_periode).max()
    spanne   = high_max - low_min

    stoch_k = ((df["Close"] - low_min) / spanne.replace(0, 1)) * 100
    stoch_d = stoch_k.rolling(d_periode).mean()

    k = float(stoch_k.iloc[-1])
    d = float(stoch_d.iloc[-1])
    k_prev = float(stoch_k.iloc[-2])
    d_prev = float(stoch_d.iloc[-2])

    signal = "neutral"

    # Kaufsignal: %K kreuzt %D von unten, im ueberverkauften Bereich
    if k_prev < d_prev and k > d and k < 40:
        signal = "kaufen"
    # Verkaufssignal: %K kreuzt %D von oben, im ueberkauften Bereich
    elif k_prev > d_prev and k < d and k > 60:
        signal = "verkaufen"
    elif k < 20:
        signal = "stark_ueberverkauft"
    elif k > 80:
        signal = "stark_ueberkauft"

    return round(k, 1), round(d, 1), signal


# ---------------------------------------------------------------------------
# Bollinger Bands
# ---------------------------------------------------------------------------

def berechne_bollinger(df: pd.DataFrame, periode: int = 20, std: float = 2.0) -> tuple[str, float]:
    """
    Berechnet Bollinger Bands Position und Breite.
    Gibt (position, breite_pct) zurueck.
    """
    if len(df) < periode:
        return "mitte", 0.0

    ma   = df["Close"].rolling(periode).mean()
    std_ = df["Close"].rolling(periode).std()
    obb  = ma + std_ * std
    ubb  = ma - std_ * std

    preis    = float(df["Close"].iloc[-1])
    ma_val   = float(ma.iloc[-1])
    obb_val  = float(obb.iloc[-1])
    ubb_val  = float(ubb.iloc[-1])

    breite = (obb_val - ubb_val) / ma_val * 100 if ma_val > 0 else 0

    # Sehr enge Baender = Squeeze (Ausbruch wahrscheinlich)
    breite_hist = ((obb - ubb) / ma * 100).dropna()
    if len(breite_hist) >= 20:
        percentile_20 = float(np.percentile(breite_hist, 20))
        if breite < percentile_20:
            return "squeeze", round(breite, 2)

    if preis >= obb_val:
        return "oben", round(breite, 2)
    elif preis <= ubb_val:
        return "unten", round(breite, 2)
    elif preis > ma_val:
        return "mitte-oben", round(breite, 2)
    else:
        return "mitte-unten", round(breite, 2)


# ---------------------------------------------------------------------------
# Support und Resistance
# ---------------------------------------------------------------------------

def berechne_support_resistance(df: pd.DataFrame, preis: float) -> tuple[float, float, float, float]:
    """
    Ermittelt naechsten Support und Widerstand aus lokalen Hochs/Tiefs.
    Gibt (support, widerstand, abstand_support_pct, abstand_widerstand_pct) zurueck.
    """
    if len(df) < 20:
        return 0.0, 0.0, 0.0, 0.0

    # Lokale Hochs und Tiefs (Fenster von 5 Tagen)
    periode = df.iloc[-60:]
    highs   = []
    lows    = []

    for i in range(2, len(periode) - 2):
        h = float(periode["High"].iloc[i])
        l = float(periode["Low"].iloc[i])
        if (h > float(periode["High"].iloc[i-1]) and
                h > float(periode["High"].iloc[i-2]) and
                h > float(periode["High"].iloc[i+1]) and
                h > float(periode["High"].iloc[i+2])):
            highs.append(h)
        if (l < float(periode["Low"].iloc[i-1]) and
                l < float(periode["Low"].iloc[i-2]) and
                l < float(periode["Low"].iloc[i+1]) and
                l < float(periode["Low"].iloc[i+2])):
            lows.append(l)

    # Naechster Support (groesstes Low unter aktuellem Preis)
    supports    = [l for l in lows if l < preis]
    widerstaende = [h for h in highs if h > preis]

    support    = max(supports)    if supports    else preis * 0.95
    widerstand = min(widerstaende) if widerstaende else preis * 1.05

    abst_sup = (preis - support)    / preis * 100
    abst_wid = (widerstand - preis) / preis * 100

    return round(support, 2), round(widerstand, 2), round(abst_sup, 2), round(abst_wid, 2)


# ---------------------------------------------------------------------------
# Trend-Struktur (Higher Highs / Higher Lows)
# ---------------------------------------------------------------------------

def berechne_trendstruktur(df: pd.DataFrame) -> tuple[str, list[float]]:
    """
    Prueft ob Higher Highs/Lows (Aufwaerts) oder Lower Highs/Lows (Abwaerts).
    """
    if len(df) < 20:
        return "neutral", []

    # Letzte 4 Swing-Hochs
    highs = []
    lows  = []
    for i in range(2, len(df) - 2):
        h = float(df["High"].iloc[i])
        l = float(df["Low"].iloc[i])
        if (h > float(df["High"].iloc[i-1]) and h > float(df["High"].iloc[i+1])):
            highs.append(h)
        if (l < float(df["Low"].iloc[i-1]) and l < float(df["Low"].iloc[i+1])):
            lows.append(l)

    if len(highs) >= 3 and len(lows) >= 3:
        # Aufwaertstrend: jedes Hoch hoeher als vorheriges, jedes Tief hoeher
        if highs[-1] > highs[-2] > highs[-3] and lows[-1] > lows[-2]:
            return "aufwaerts", highs[-3:]
        # Abwaertstrend: jedes Hoch tiefer als vorheriges, jedes Tief tiefer
        elif highs[-1] < highs[-2] < highs[-3] and lows[-1] < lows[-2]:
            return "abwaerts", highs[-3:]

    return "neutral", []


# ---------------------------------------------------------------------------
# Haupt-Analyse
# ---------------------------------------------------------------------------

def analysiere_muster(ticker: str, ist_krypto: bool = False) -> PatternErgebnis | None:
    """Fuehrt die vollstaendige Pattern-Analyse fuer ein Asset durch."""
    try:
        if ist_krypto:
            yf_symbol = f"{ticker}-USD"
        else:
            yf_symbol = ticker

        t    = yf.Ticker(yf_symbol)
        df   = t.history(period="6mo")
        if df.empty or len(df) < 30:
            return None

        preis = float(df["Close"].iloc[-1])
        erg   = PatternErgebnis(asset=ticker, preis=preis)

        # 1. Kerzenmuster
        erg.kerzenmuster = erkenne_kerzenmuster(df)

        # 2. Fibonacci
        erg.fib_naechstes_level, erg.fib_level_name, erg.fib_richtung = \
            berechne_fibonacci(df, preis)

        # 3. Stochastik
        erg.stoch_k, erg.stoch_d, erg.stoch_signal = berechne_stochastik(df)

        # 4. Bollinger Bands
        erg.bb_position, erg.bb_breite_pct = berechne_bollinger(df)

        # 5. Support/Resistance
        erg.naechster_support, erg.naechster_widerstand, \
        erg.abstand_support_pct, erg.abstand_widerstand_pct = \
            berechne_support_resistance(df, preis)

        # 6. Trend-Struktur
        erg.trend_struktur, erg.swing_punkte = berechne_trendstruktur(df)

        # Gesamtbewertung
        punkte = 0
        zusammenfassung = []

        # Kerzenmuster
        for m in erg.kerzenmuster:
            if any(w in m for w in ["Bullish", "Morning Star", "Hammer", "Soldiers"]):
                punkte += 2
            elif any(w in m for w in ["Bearish", "Evening Star", "Shooting", "Crows"]):
                punkte -= 2
            elif "Doji" in m:
                pass  # neutral
            zusammenfassung.append(f"Kerze: {m}")

        # Stochastik
        if erg.stoch_signal == "kaufen":
            punkte += 2
            zusammenfassung.append(f"Stochastik: Kaufsignal (%K={erg.stoch_k:.0f} kreuzt %D)")
        elif erg.stoch_signal == "stark_ueberverkauft":
            punkte += 1
            zusammenfassung.append(f"Stochastik: Stark ueberverkauft ({erg.stoch_k:.0f}) — Erholung moeglich")
        elif erg.stoch_signal == "verkaufen":
            punkte -= 2
            zusammenfassung.append(f"Stochastik: Verkaufssignal (%K={erg.stoch_k:.0f})")
        elif erg.stoch_signal == "stark_ueberkauft":
            punkte -= 1
            zusammenfassung.append(f"Stochastik: Stark ueberkauft ({erg.stoch_k:.0f}) — Vorsicht")

        # Bollinger Bands
        if erg.bb_position == "unten":
            punkte += 2
            zusammenfassung.append("Bollinger: Preis am unteren Band — Kaufzone")
        elif erg.bb_position == "oben":
            punkte -= 1
            zusammenfassung.append("Bollinger: Preis am oberen Band — vorsichtig")
        elif erg.bb_position == "squeeze":
            punkte += 1
            zusammenfassung.append(f"Bollinger: Squeeze! Ausbruch steht bevor (Breite: {erg.bb_breite_pct:.1f}%)")

        # Fibonacci
        if erg.fib_level_name:
            abst = abs(preis - erg.fib_naechstes_level) / preis * 100
            if abst < 2.0:
                if erg.fib_richtung == "support":
                    punkte += 1
                    zusammenfassung.append(f"Fibonacci: Preis nahe {erg.fib_level_name} Support ({erg.fib_naechstes_level:.2f})")
                else:
                    punkte -= 1
                    zusammenfassung.append(f"Fibonacci: Nahe {erg.fib_level_name} Widerstand ({erg.fib_naechstes_level:.2f})")

        # Trend-Struktur
        if erg.trend_struktur == "aufwaerts":
            punkte += 2
            zusammenfassung.append("Trend: Higher Highs & Higher Lows — intakter Aufwaertstrend")
        elif erg.trend_struktur == "abwaerts":
            punkte -= 2
            zusammenfassung.append("Trend: Lower Highs & Lower Lows — intakter Abwaertstrend")

        erg.pattern_punkte = punkte
        erg.zusammenfassung = zusammenfassung

        if punkte >= 3:
            erg.pattern_empfehlung = "KAUFEN"
        elif punkte <= -3:
            erg.pattern_empfehlung = "VERKAUFEN"
        else:
            erg.pattern_empfehlung = "ABWARTEN"

        return erg

    except Exception as e:
        return None


# ---------------------------------------------------------------------------
# Ausgabe
# ---------------------------------------------------------------------------

def drucke_pattern(erg: PatternErgebnis):
    print(f"\n{'='*60}")
    print(f"  PATTERN-ANALYSE: {erg.asset}  —  ${erg.preis:,.2f}")
    print(f"{'='*60}")
    print(f"  Stochastik     : %K={erg.stoch_k:.0f}  %D={erg.stoch_d:.0f}  → {erg.stoch_signal}")
    print(f"  Bollinger      : {erg.bb_position}  (Breite: {erg.bb_breite_pct:.1f}%)")
    print(f"  Trend-Struktur : {erg.trend_struktur}")
    print(f"  Support        : ${erg.naechster_support:,.2f}  ({erg.abstand_support_pct:.1f}% entfernt)")
    print(f"  Widerstand     : ${erg.naechster_widerstand:,.2f}  ({erg.abstand_widerstand_pct:.1f}% entfernt)")
    if erg.fib_level_name:
        print(f"  Fibonacci      : {erg.fib_level_name} bei ${erg.fib_naechstes_level:,.2f} ({erg.fib_richtung})")
    if erg.kerzenmuster:
        print(f"  Kerzenmuster   :")
        for m in erg.kerzenmuster:
            print(f"    • {m}")
    print(f"\n  Analyse:")
    for z in erg.zusammenfassung:
        print(f"    → {z}")
    print(f"\n  Pattern-Score    : {erg.pattern_punkte:+d}")
    print(f"  EMPFEHLUNG       : >> {erg.pattern_empfehlung} <<")
    print(f"{'='*60}")


# ---------------------------------------------------------------------------
# Einstiegspunkt
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Trading Intelligence System — Pattern-Agent\n")
    for ticker in ["MSFT", "BTC"]:
        ist_krypto = ticker in ["BTC", "ETH", "SOL"]
        print(f"  Analysiere {ticker}...", end=" ", flush=True)
        erg = analysiere_muster(ticker, ist_krypto)
        if erg:
            print("OK")
            drucke_pattern(erg)
        else:
            print("Keine Daten")
