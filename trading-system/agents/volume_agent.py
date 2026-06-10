"""
Volume & Marktstruktur Agent
Inspiriert von professioneller Order-Flow-Analyse:
Volumen zeigt was Institutionelle tun — nicht was Indikatoren sagen.

Analysiert:
  1. Relatives Volumen   — ungewoehnlich hoch/niedrig vs. Durchschnitt
  2. Volumen-Trend       — steigendes Volumen bestaetigt Kursbewegung
  3. Order Blocks        — Zonen mit hohem institutionellen Interesse
  4. Fair Value Gaps     — Preisluecken die der Markt oft schliesst
  5. Volumen-Divergenz   — Kurs steigt aber Volumen sinkt = Warnung
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
class VolumeErgebnis:
    asset: str
    preis: float

    # Relatives Volumen
    volumen_heute: float = 0.0
    volumen_schnitt_20d: float = 0.0
    relatives_volumen: float = 0.0   # 1.0 = normal, 2.0 = doppelt so hoch
    volumen_signal: str = "normal"   # "hoch", "sehr_hoch", "niedrig", "normal"

    # Volumen-Trend-Bestaetigung
    volumen_bestaetigt_trend: bool = False
    volumen_divergenz: bool = False   # Preis steigt, Volumen faellt = Warnung

    # On-Balance Volume (OBV)
    obv_trend: str = "neutral"       # "steigend", "fallend", "neutral"

    # Order Blocks
    order_blocks: list[dict] = field(default_factory=list)

    # Fair Value Gaps
    fair_value_gaps: list[dict] = field(default_factory=list)

    # Gesamtbewertung
    volume_punkte: int = 0
    volume_empfehlung: str = "NEUTRAL"
    zusammenfassung: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Analyse-Funktionen
# ---------------------------------------------------------------------------

def analysiere_relatives_volumen(df: pd.DataFrame) -> tuple[float, float, float, str]:
    """
    Berechnet das relative Volumen (heutiges vs. 20-Tage-Durchschnitt).
    """
    if "Volume" not in df.columns or len(df) < 21:
        return 0, 0, 1.0, "normal"

    vol_heute   = float(df["Volume"].iloc[-1])
    vol_schnitt = float(df["Volume"].iloc[-21:-1].mean())

    if vol_schnitt == 0:
        return vol_heute, vol_schnitt, 1.0, "normal"

    rel_vol = vol_heute / vol_schnitt

    if rel_vol > 3.0:
        signal = "sehr_hoch"     # Institutionelle im Markt
    elif rel_vol > 1.8:
        signal = "hoch"          # Erhoehtes Interesse
    elif rel_vol < 0.5:
        signal = "niedrig"       # Wenig Handel = schwaches Signal
    else:
        signal = "normal"

    return vol_heute, vol_schnitt, round(rel_vol, 2), signal


def erkenne_volumen_trend(df: pd.DataFrame) -> tuple[bool, bool]:
    """
    Prueft ob Volumen den Kurstrend bestaetigt oder widerspricht.
    Gibt (bestaetigt, divergenz) zurueck.
    """
    if len(df) < 10:
        return False, False

    # Letzte 5 Tage: Korrelation Kurs und Volumen
    preise  = df["Close"].iloc[-5:].values
    vol     = df["Volume"].iloc[-5:].values if "Volume" in df.columns else None

    if vol is None or len(vol) < 5:
        return False, False

    kurs_steigt = preise[-1] > preise[0]
    vol_steigt  = vol[-1] > vol[0]

    bestaetigt = (kurs_steigt and vol_steigt) or (not kurs_steigt and not vol_steigt)
    divergenz  = kurs_steigt and not vol_steigt   # Gefaehrlich: Preis steigt ohne Volumen

    return bestaetigt, divergenz


def berechne_obv(df: pd.DataFrame) -> str:
    """
    On-Balance Volume: kumuliertes Volumen gewichtet nach Kursrichtung.
    Zeigt ob Institutionelle akkumulieren (kaufen) oder verteilen (verkaufen).
    """
    if "Volume" not in df.columns or len(df) < 20:
        return "neutral"

    obv = []
    for i in range(1, len(df)):
        if df["Close"].iloc[i] > df["Close"].iloc[i-1]:
            obv.append(float(df["Volume"].iloc[i]))
        elif df["Close"].iloc[i] < df["Close"].iloc[i-1]:
            obv.append(-float(df["Volume"].iloc[i]))
        else:
            obv.append(0)

    obv_kumuliert = pd.Series(obv).cumsum()
    obv_ma5  = obv_kumuliert.iloc[-5:].mean()
    obv_ma20 = obv_kumuliert.iloc[-20:].mean()

    if obv_ma5 > obv_ma20 * 1.05:
        return "steigend"   # Akkumulation — Institutionelle kaufen
    elif obv_ma5 < obv_ma20 * 0.95:
        return "fallend"    # Distribution — Institutionelle verkaufen
    else:
        return "neutral"


def erkenne_order_blocks(df: pd.DataFrame, preis: float) -> list[dict]:
    """
    Order Blocks: Kerzen mit sehr hohem Volumen dicht am aktuellen Preis.
    Diese Zonen haben institutionelles Interesse und wirken als Support/Resistance.
    """
    if "Volume" not in df.columns or len(df) < 20:
        return []

    vol_schwelle = df["Volume"].iloc[-50:].quantile(0.85) if len(df) >= 50 else df["Volume"].mean() * 1.5
    blocks = []

    for i in range(max(0, len(df)-50), len(df)-1):
        vol  = float(df["Volume"].iloc[i])
        if vol < vol_schwelle:
            continue

        kurs   = float(df["Close"].iloc[i])
        abstand = abs(preis - kurs) / preis * 100

        # Nur Blocks in der Naehe (max 10% entfernt)
        if abstand > 10:
            continue

        blocks.append({
            "preis":   round(kurs, 2),
            "typ":     "support" if kurs < preis else "resistance",
            "abstand": round(abstand, 1),
            "volumen": int(vol),
            "datum":   str(df.index[i].date()) if hasattr(df.index[i], "date") else "",
        })

    # Naechste behalten (max. 3)
    blocks.sort(key=lambda x: x["abstand"])
    return blocks[:3]


def erkenne_fair_value_gaps(df: pd.DataFrame, preis: float) -> list[dict]:
    """
    Fair Value Gaps (FVG): Preisluecken zwischen Kerzen.
    Der Markt tendiert dazu diese Luecken zu schliessen.
    """
    gaps = []
    if len(df) < 3:
        return gaps

    for i in range(1, len(df)-1):
        hoch_davor   = float(df["High"].iloc[i-1])
        tief_danach  = float(df["Low"].iloc[i+1])
        tief_davor   = float(df["Low"].iloc[i-1])
        hoch_danach  = float(df["High"].iloc[i+1])

        # Bullische FVG: Luecke nach oben (Tief der aktuellen > Hoch der vorherigen)
        if float(df["Low"].iloc[i]) > hoch_davor:
            luecke_preis = (float(df["Low"].iloc[i]) + hoch_davor) / 2
            abstand      = abs(preis - luecke_preis) / preis * 100
            if abstand < 8:
                gaps.append({
                    "typ":     "bullish_fvg",
                    "preis":   round(luecke_preis, 2),
                    "abstand": round(abstand, 1),
                    "richtung": "support",
                })

        # Bearische FVG: Luecke nach unten
        if float(df["High"].iloc[i]) < tief_davor:
            luecke_preis = (float(df["High"].iloc[i]) + tief_davor) / 2
            abstand      = abs(preis - luecke_preis) / preis * 100
            if abstand < 8:
                gaps.append({
                    "typ":     "bearish_fvg",
                    "preis":   round(luecke_preis, 2),
                    "abstand": round(abstand, 1),
                    "richtung": "resistance",
                })

    gaps.sort(key=lambda x: x["abstand"])
    return gaps[:3]


# ---------------------------------------------------------------------------
# Haupt-Analyse
# ---------------------------------------------------------------------------

def analysiere_volumen(ticker: str, ist_krypto: bool = False) -> VolumeErgebnis | None:
    """Vollstaendige Volume & Marktstruktur Analyse."""
    try:
        yf_sym = f"{ticker}-USD" if ist_krypto else ticker
        t      = yf.Ticker(yf_sym)
        df     = t.history(period="3mo")

        if df.empty or len(df) < 20:
            return None

        preis = float(df["Close"].iloc[-1])
        erg   = VolumeErgebnis(asset=ticker, preis=preis)

        # 1. Relatives Volumen
        erg.volumen_heute, erg.volumen_schnitt_20d, erg.relatives_volumen, erg.volumen_signal = \
            analysiere_relatives_volumen(df)

        # 2. Volumen-Trend
        erg.volumen_bestaetigt_trend, erg.volumen_divergenz = erkenne_volumen_trend(df)

        # 3. OBV
        erg.obv_trend = berechne_obv(df)

        # 4. Order Blocks
        erg.order_blocks = erkenne_order_blocks(df, preis)

        # 5. Fair Value Gaps
        erg.fair_value_gaps = erkenne_fair_value_gaps(df, preis)

        # Gesamtbewertung
        punkte = 0
        zusammenfassung = []

        # Volumen-Signal
        if erg.volumen_signal == "sehr_hoch":
            # Richtung entscheidet ob bullish oder bearish
            kurs_heute = float(df["Close"].iloc[-1])
            kurs_gestern = float(df["Close"].iloc[-2])
            if kurs_heute > kurs_gestern:
                punkte += 3
                zusammenfassung.append(f"Sehr hohes Volumen ({erg.relatives_volumen:.1f}x) bei Kursanstieg — institutionelle Kaeufe")
            else:
                punkte -= 3
                zusammenfassung.append(f"Sehr hohes Volumen ({erg.relatives_volumen:.1f}x) bei Kursfall — institutionelle Verkauefe")
        elif erg.volumen_signal == "hoch":
            punkte += 1
            zusammenfassung.append(f"Erhoehtes Volumen ({erg.relatives_volumen:.1f}x) — Interesse steigt")
        elif erg.volumen_signal == "niedrig":
            punkte -= 1
            zusammenfassung.append(f"Geringes Volumen ({erg.relatives_volumen:.1f}x) — schwaches Signal")

        # Volumen-Divergenz (Warnsignal)
        if erg.volumen_divergenz:
            punkte -= 2
            zusammenfassung.append("WARNUNG: Kurs steigt ohne Volumen-Bestaetigung — Schwaeche")
        elif erg.volumen_bestaetigt_trend:
            punkte += 1
            zusammenfassung.append("Volumen bestaetigt Kurstrend")

        # OBV
        if erg.obv_trend == "steigend":
            punkte += 2
            zusammenfassung.append("OBV steigend — Institutionelle akkumulieren (kaufen)")
        elif erg.obv_trend == "fallend":
            punkte -= 2
            zusammenfassung.append("OBV fallend — Institutionelle distribuieren (verkaufen)")

        # Order Blocks nahe Preis
        for ob in erg.order_blocks[:1]:
            if ob["typ"] == "support":
                punkte += 1
                zusammenfassung.append(f"Order Block Support bei ${ob['preis']:,.2f} ({ob['abstand']:.1f}% entfernt)")
            else:
                punkte -= 1
                zusammenfassung.append(f"Order Block Widerstand bei ${ob['preis']:,.2f} ({ob['abstand']:.1f}% entfernt)")

        # Fair Value Gaps
        for fvg in erg.fair_value_gaps[:1]:
            zusammenfassung.append(f"Fair Value Gap ({fvg['typ']}) bei ${fvg['preis']:,.2f} — Markt koennte zurueckkehren")

        erg.volume_punkte = punkte
        erg.zusammenfassung = zusammenfassung

        if punkte >= 3:
            erg.volume_empfehlung = "KAUFEN"
        elif punkte <= -3:
            erg.volume_empfehlung = "VERKAUFEN"
        else:
            erg.volume_empfehlung = "NEUTRAL"

        return erg

    except Exception:
        return None


# ---------------------------------------------------------------------------
# Ausgabe
# ---------------------------------------------------------------------------

def drucke_volume_analyse(erg: VolumeErgebnis):
    print(f"\n{'='*60}")
    print(f"  VOLUME-ANALYSE: {erg.asset}  —  ${erg.preis:,.2f}")
    print(f"{'='*60}")
    print(f"  Volumen heute  : {erg.volumen_heute:,.0f}")
    print(f"  Ø 20d Volumen  : {erg.volumen_schnitt_20d:,.0f}")
    print(f"  Relatives Vol  : {erg.relatives_volumen:.1f}x  → {erg.volumen_signal.upper()}")
    print(f"  OBV-Trend      : {erg.obv_trend.upper()}")
    print(f"  Vol-Divergenz  : {'JA — WARNUNG' if erg.volumen_divergenz else 'Nein'}")
    if erg.order_blocks:
        print(f"  Order Blocks   :")
        for ob in erg.order_blocks:
            print(f"    {ob['typ'].upper():<12} ${ob['preis']:,.2f}  ({ob['abstand']:.1f}% entfernt)")
    if erg.fair_value_gaps:
        print(f"  Fair Value Gaps:")
        for fvg in erg.fair_value_gaps:
            print(f"    {fvg['typ']:<15} ${fvg['preis']:,.2f}  ({fvg['abstand']:.1f}% entfernt)")
    print(f"\n  Analyse:")
    for z in erg.zusammenfassung:
        print(f"    → {z}")
    print(f"\n  Volume-Score   : {erg.volume_punkte:+d}")
    print(f"  EMPFEHLUNG     : >> {erg.volume_empfehlung} <<")
    print(f"{'='*60}")


# ---------------------------------------------------------------------------
# Einstiegspunkt
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Trading Intelligence System — Volume & Marktstruktur Agent\n")
    for ticker, krypto in [("MSFT", False), ("BTC", True)]:
        print(f"  Analysiere {ticker}...", end=" ", flush=True)
        erg = analysiere_volumen(ticker, krypto)
        if erg:
            print("OK")
            drucke_volume_analyse(erg)
        else:
            print("Keine Daten")
