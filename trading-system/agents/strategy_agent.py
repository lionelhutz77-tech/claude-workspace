"""
Strategie-Agent
Klassifiziert jede Empfehlung in Short/Medium/Long-Term,
berechnet Break-Even nach Trade Republic Kosten und
fuehrt eine taeglich Retro-Analyse durch.

Trade Republic Kosten (Stand 2026):
  - 1,00 EUR Ordergebuehr pro Trade (Kauf + Verkauf = 2 EUR gesamt)
  - 0,15% FX-Spread bei US-Aktien (eingebaut in den Kurs)
  - 1,50% Spread bei Krypto
  - 0,00% bei deutschen/EU-Aktien (kein FX)
"""

import sys
import os
import time
import warnings
warnings.filterwarnings("ignore")

from dataclasses import dataclass
from datetime import datetime, timedelta

import yfinance as yf
import pandas as pd
import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


# ---------------------------------------------------------------------------
# Trade Republic Kostenmodell
# ---------------------------------------------------------------------------

TR_ORDER_GEBUEHR    = 1.00    # EUR pro Order (Kauf ODER Verkauf)
TR_FX_SPREAD_US     = 0.0015  # 0.15% FX bei US-Aktien
TR_KRYPTO_SPREAD    = 0.015   # 1.5% bei Krypto
TR_EU_SPREAD        = 0.0     # 0% bei EU-Aktien (kein FX)


def berechne_kosten(
    investition_eur: float,
    asset_typ: str,          # "aktie_us", "aktie_eu", "krypto"
) -> dict:
    """
    Berechnet die vollstaendigen Trade-Kosten bei Trade Republic.
    Gibt Break-Even-Prozentsatz zurueck.
    """
    if asset_typ == "krypto":
        spread = TR_KRYPTO_SPREAD
    elif asset_typ == "aktie_us":
        spread = TR_FX_SPREAD_US
    else:
        spread = TR_EU_SPREAD

    kosten_kauf     = TR_ORDER_GEBUEHR + (investition_eur * spread)
    kosten_verkauf  = TR_ORDER_GEBUEHR + (investition_eur * spread)
    kosten_gesamt   = kosten_kauf + kosten_verkauf

    # Mindest-Gewinn um Break-Even zu erreichen
    breakeven_pct   = (kosten_gesamt / investition_eur) * 100

    return {
        "kosten_kauf_eur":    round(kosten_kauf,   2),
        "kosten_verkauf_eur": round(kosten_verkauf, 2),
        "kosten_gesamt_eur":  round(kosten_gesamt,  2),
        "breakeven_pct":      round(breakeven_pct,  2),
        "netto_ziel_pct":     round(breakeven_pct + 2.0, 2),  # Mindest-Netto-Gewinn
    }


# ---------------------------------------------------------------------------
# Strategie-Klassifikation
# ---------------------------------------------------------------------------

@dataclass
class StrategieKlassifikation:
    asset: str
    strategie: str          # "SHORT", "MEDIUM", "LONG"
    begruendung: str
    haltezeit_tage: int     # empfohlene Haltezeit
    ziel_pct: float         # realistisches Kursziel in %
    stop_pct: float         # Stop-Loss in %
    ziel_preis: float
    stop_preis: float
    breakeven_pct: float    # Mindest-Gewinn nach Kosten
    netto_ziel_eur: float   # erwarteter Nettogewinn in EUR


def klassifiziere_strategie(
    asset: str,
    preis: float,
    rsi: float,
    momentum_5d: float,
    asset_typ: str,
    investition_eur: float = 100.0,
) -> StrategieKlassifikation:
    """
    Klassifiziert einen Trade als Short/Medium/Long basierend auf:
    - RSI (Ueberkauft/Ueberverkauft)
    - 5-Tage-Momentum (kurzfristiger Schwung)
    - Volatilitaet (ATR)
    - Asset-Typ
    """
    # Krypto immer Short oder Medium (24/7, hoehere Volatilitaet)
    if asset_typ == "krypto":
        if momentum_5d > 3 and rsi < 65:
            strategie = "SHORT"
            haltezeit = 3
            ziel_pct  = 5.0
            stop_pct  = 3.0
            begruendung = f"Starkes 5d-Momentum ({momentum_5d:+.1f}%) + RSI gesund ({rsi:.0f})"
        elif rsi < 40:
            strategie = "MEDIUM"
            haltezeit = 14
            ziel_pct  = 15.0
            stop_pct  = 7.0
            begruendung = f"RSI ueberverkauft ({rsi:.0f}) — Erholung erwartet"
        else:
            strategie = "SHORT"
            haltezeit = 5
            ziel_pct  = 6.0
            stop_pct  = 3.0
            begruendung = "Krypto mit neutralem Momentum"

    # Aktien: nach Momentum und RSI einteilen
    elif momentum_5d > 4 and rsi < 68:
        strategie = "SHORT"
        haltezeit = 5
        ziel_pct  = 4.0
        stop_pct  = 2.0
        begruendung = f"Starkes Kurz-Momentum ({momentum_5d:+.1f}%) — kurzfristiger Swing"
    elif rsi < 45 and momentum_5d > 0:
        strategie = "MEDIUM"
        haltezeit = 14
        ziel_pct  = 10.0
        stop_pct  = 5.0
        begruendung = f"RSI tief ({rsi:.0f}) mit positivem Momentum — Erholungskauf"
    elif rsi < 55 and momentum_5d > 1:
        strategie = "MEDIUM"
        haltezeit = 10
        ziel_pct  = 8.0
        stop_pct  = 4.0
        begruendung = f"RSI neutral ({rsi:.0f}), Trend aufwaerts — Swing-Position"
    else:
        strategie = "LONG"
        haltezeit = 30
        ziel_pct  = 15.0
        stop_pct  = 7.0
        begruendung = f"Kein kurzfristiger Katalysator erkennbar — langfristiger Aufbau"

    ziel_preis = round(preis * (1 + ziel_pct / 100), 2)
    stop_preis = round(preis * (1 - stop_pct / 100), 2)

    # Kosten und Nettogewinn
    typ_key = "krypto" if asset_typ == "krypto" else "aktie_us"
    kosten  = berechne_kosten(investition_eur, typ_key)
    brutto_gewinn_eur = investition_eur * (ziel_pct / 100)
    netto_eur = brutto_gewinn_eur - kosten["kosten_gesamt_eur"]

    return StrategieKlassifikation(
        asset=asset,
        strategie=strategie,
        begruendung=begruendung,
        haltezeit_tage=haltezeit,
        ziel_pct=ziel_pct,
        stop_pct=stop_pct,
        ziel_preis=ziel_preis,
        stop_preis=stop_preis,
        breakeven_pct=kosten["breakeven_pct"],
        netto_ziel_eur=round(netto_eur, 2),
    )


# ---------------------------------------------------------------------------
# Retro-Analyse
# ---------------------------------------------------------------------------

@dataclass
class RetroErgebnis:
    asset: str
    analyse_datum: str
    empfehlung: str
    einstieg_preis: float
    preis_5d_spaeter: float
    preis_10d_spaeter: float
    preis_20d_spaeter: float
    rendite_5d_pct: float
    rendite_10d_pct: float
    rendite_20d_pct: float
    beste_strategie: str     # welche Haltezeit waere am besten gewesen
    netto_5d_eur: float      # Nettogewinn/-verlust nach Kosten (100 EUR Basis)
    netto_10d_eur: float
    netto_20d_eur: float


def retro_analyse(
    asset: str,
    einstieg_preis: float,
    analyse_datum: str,
    asset_typ: str = "aktie_us",
    investition_eur: float = 100.0,
) -> RetroErgebnis | None:
    """
    Prueft rueckwirkend: Was haette eine Position eingebracht?
    Vergleicht Short (5 Tage), Medium (10 Tage), Long (20 Tage).
    """
    try:
        datum = datetime.strptime(analyse_datum, "%Y-%m-%d")
        heute = datetime.now()
        tage_seit_signal = (heute - datum).days

        if tage_seit_signal < 5:
            return None  # Noch nicht genug Daten

        # Kursdaten laden
        if asset_typ == "krypto":
            yf_symbol = f"{asset}-USD"
        else:
            yf_symbol = asset

        ticker = yf.Ticker(yf_symbol)
        hist   = ticker.history(start=datum.strftime("%Y-%m-%d"),
                                end=heute.strftime("%Y-%m-%d"))

        if hist.empty or len(hist) < 5:
            return None

        preise = hist["Close"].values

        def preis_nach_n_tagen(n: int) -> float:
            idx = min(n, len(preise) - 1)
            return float(preise[idx])

        p5  = preis_nach_n_tagen(5)
        p10 = preis_nach_n_tagen(10)
        p20 = preis_nach_n_tagen(20)

        r5  = (p5  / einstieg_preis - 1) * 100
        r10 = (p10 / einstieg_preis - 1) * 100
        r20 = (p20 / einstieg_preis - 1) * 100

        typ_key = "krypto" if asset_typ == "krypto" else "aktie_us"
        kosten  = berechne_kosten(investition_eur, typ_key)["kosten_gesamt_eur"]

        def netto(rendite_pct: float) -> float:
            return round(investition_eur * (rendite_pct / 100) - kosten, 2)

        n5, n10, n20 = netto(r5), netto(r10), netto(r20)

        # Beste Strategie bestimmen
        beste = max([("5d", n5), ("10d", n10), ("20d", n20)], key=lambda x: x[1])

        return RetroErgebnis(
            asset=asset,
            analyse_datum=analyse_datum,
            empfehlung="KAUFEN",
            einstieg_preis=einstieg_preis,
            preis_5d_spaeter=round(p5,  2),
            preis_10d_spaeter=round(p10, 2),
            preis_20d_spaeter=round(p20, 2),
            rendite_5d_pct=round(r5,  2),
            rendite_10d_pct=round(r10, 2),
            rendite_20d_pct=round(r20, 2),
            beste_strategie=beste[0],
            netto_5d_eur=n5,
            netto_10d_eur=n10,
            netto_20d_eur=n20,
        )

    except Exception as e:
        return None


def retro_analyse_alle(signale_historisch: list[dict]) -> list[RetroErgebnis]:
    """
    Fuehrt Retro-Analyse fuer alle historischen Signale durch.
    Liest aus der Memory-Datenbank.
    """
    import sqlite3
    db_pfad = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "market_memory.db")

    if not os.path.exists(db_pfad):
        return []

    conn = sqlite3.connect(db_pfad)
    conn.row_factory = sqlite3.Row

    # Signale der letzten 30 Tage holen
    grenze = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    rows   = conn.execute("""
        SELECT asset, datum, einstieg, empfehlung
        FROM tages_signale
        WHERE datum >= ? AND empfehlung = 'KAUFEN'
        ORDER BY datum DESC
    """, (grenze,)).fetchall()
    conn.close()

    ergebnisse = []
    for row in rows:
        if not row["einstieg"] or row["einstieg"] == 0:
            continue
        r = retro_analyse(
            asset=row["asset"],
            einstieg_preis=float(row["einstieg"]),
            analyse_datum=row["datum"],
        )
        if r:
            ergebnisse.append(r)
        time.sleep(0.2)

    return ergebnisse


# ---------------------------------------------------------------------------
# Ausgabe
# ---------------------------------------------------------------------------

def drucke_strategie(k: StrategieKlassifikation, investition_eur: float):
    print(f"\n  {k.asset} → Strategie: {k.strategie}  ({k.haltezeit_tage} Tage)")
    print(f"    {k.begruendung}")
    print(f"    Ziel: ${k.ziel_preis:,.2f} (+{k.ziel_pct:.1f}%)  |  Stop: ${k.stop_preis:,.2f} (-{k.stop_pct:.1f}%)")
    print(f"    Break-Even nach TR-Kosten: +{k.breakeven_pct:.2f}%")
    print(f"    Netto-Gewinn bei Ziel ({investition_eur:.0f} EUR): {k.netto_ziel_eur:+.2f} EUR")


def drucke_retro(r: RetroErgebnis):
    beste_farbe = {"5d": "Short", "10d": "Medium", "20d": "Long"}
    print(f"\n  {r.asset} (Signal: {r.analyse_datum})")
    print(f"    Einstieg: ${r.einstieg_preis:,.2f}")
    print(f"    5d:  ${r.preis_5d_spaeter:,.2f}  ({r.rendite_5d_pct:>+.1f}%)  Netto: {r.netto_5d_eur:>+.2f} EUR")
    print(f"    10d: ${r.preis_10d_spaeter:,.2f}  ({r.rendite_10d_pct:>+.1f}%)  Netto: {r.netto_10d_eur:>+.2f} EUR")
    print(f"    20d: ${r.preis_20d_spaeter:,.2f}  ({r.rendite_20d_pct:>+.1f}%)  Netto: {r.netto_20d_eur:>+.2f} EUR")
    print(f"    Beste Strategie waere gewesen: {beste_farbe.get(r.beste_strategie,'–')}-Term ({r.beste_strategie})")


# ---------------------------------------------------------------------------
# Einstiegspunkt
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Trading Intelligence System — Strategie-Agent\n")

    # Kostenbeispiele
    print("=== TRADE REPUBLIC KOSTENRECHNER ===")
    for investition in [50, 100, 250, 500, 1000]:
        k = berechne_kosten(investition, "aktie_us")
        print(f"  {investition:>5} EUR US-Aktie:  "
              f"Kosten {k['kosten_gesamt_eur']:.2f} EUR  |  "
              f"Break-Even: +{k['breakeven_pct']:.2f}%")

    print()
    for investition in [50, 100, 250]:
        k = berechne_kosten(investition, "krypto")
        print(f"  {investition:>5} EUR Krypto:    "
              f"Kosten {k['kosten_gesamt_eur']:.2f} EUR  |  "
              f"Break-Even: +{k['breakeven_pct']:.2f}%")

    # Strategie-Klassifikation Beispiele
    print("\n=== STRATEGIE-KLASSIFIKATION ===")
    test_assets = [
        ("ADBE",  259.21, 52.3, 4.8,  "aktie_us"),
        ("AMD",   505.14, 63.1, 12.4, "aktie_us"),
        ("BTC",   73816.0, 22.0, -0.4, "krypto"),
        ("ETH",   2022.75, 20.7, 0.1, "krypto"),
    ]
    for asset, preis, rsi, mom, typ in test_assets:
        k = klassifiziere_strategie(asset, preis, rsi, mom, typ, investition_eur=100)
        drucke_strategie(k, 100)

    # Retro-Analyse (falls Daten vorhanden)
    print("\n=== RETRO-ANALYSE (letzte 30 Tage) ===")
    retros = retro_analyse_alle([])
    if retros:
        for r in retros[:5]:
            drucke_retro(r)
    else:
        print("  Noch keine historischen Daten — waechst taeglich.")
