"""
Korrelations-Agent
Erkennt Zusammenhaenge zwischen Assets und leitet daraus zusaetzliche
Signale ab. Zwei Methoden:

1. STATISTISCHE KORRELATION
   Berechnet den Pearson-Korrelationskoeffizienten aus echten Kursdaten
   der letzten 90 Tage. Wert zwischen -1 und +1:
     +0.7 bis +1.0 = stark positiv korreliert (bewegen sich gleich)
      0.0          = keine Korrelation
     -0.7 bis -1.0 = stark negativ korreliert (bewegen sich entgegengesetzt)

2. BEKANNTE THEMATISCHE KORRELATIONEN
   Vordefinierte Beziehungen die fundamental begruendet sind:
     BTC steigt  -> COIN, MSTR profitieren
     Oel steigt  -> XOM, CVX profitieren
     Fed Zinsangst -> Tech-Aktien unter Druck
     usw.

Ausgabe: Fuer jedes analysierte Asset werden verwandte Assets und
         deren erwartete Reaktion gezeigt.
"""

import sys
import time
import warnings
warnings.filterwarnings("ignore")

from dataclasses import dataclass, field

import yfinance as yf
import pandas as pd
import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


# ---------------------------------------------------------------------------
# Bekannte thematische Korrelationen
# ---------------------------------------------------------------------------

# Format: Trigger-Asset -> [(Korreliertes Asset, Richtung, Begruendung)]
THEMATISCHE_KORRELATIONEN = {
    "BTC": [
        ("ETH",   +0.90, "Krypto-Markt bewegt sich gemeinsam"),
        ("SOL",   +0.85, "Altcoins folgen Bitcoin-Trend"),
        ("COIN",  +0.80, "Coinbase-Umsatz direkt abhaengig von BTC-Volumen"),
        ("MSTR",  +0.85, "MicroStrategy haelt grosse BTC-Positionen"),
        ("HOOD",  +0.70, "Robinhood-Handelsvolumen steigt bei Krypto-Rally"),
    ],
    "ETH": [
        ("BTC",   +0.90, "Krypto-Leitwaehrung"),
        ("SOL",   +0.80, "Konkurrierendes Layer-1-Netzwerk, aehnliche Investoren"),
    ],
    "NVDA": [
        ("AMD",   +0.75, "Beide profitieren von KI/GPU-Nachfrage"),
        ("AVGO",  +0.65, "KI-Chip-Sektor"),
        ("MSFT",  +0.60, "Azure KI-Infrastruktur nutzt NVIDIA-GPUs"),
        ("META",  +0.55, "Meta investiert massiv in NVIDIA-Hardware"),
    ],
    "TSLA": [
        ("RIVN",  +0.70, "Elektrofahrzeug-Sektor"),
        ("LCID",  +0.65, "EV-Konkurrent"),
        ("NIO",   +0.60, "Chinesischer EV-Hersteller, aehnliche Investoren"),
        ("LI",    +0.60, "Chinesischer EV-Hersteller"),
    ],
    "AAPL": [
        ("MSFT",  +0.75, "Beide grosse Tech-Konsumenten-Unternehmen"),
        ("GOOGL", +0.70, "Big Tech gleichlaeufig"),
        ("QCOM",  +0.60, "Qualcomm liefert Chips fuer iPhones"),
    ],
    "MSFT": [
        ("GOOGL", +0.75, "Cloud-Konkurrenten mit aehnlichen Investoren"),
        ("AMZN",  +0.70, "AWS vs. Azure Wettbewerb"),
        ("CRM",   +0.65, "Enterprise-Software-Sektor"),
    ],
    "XOM": [
        ("CVX",   +0.90, "Beide Oel-Majors, stark korreliert"),
        ("COP",   +0.85, "Oel & Gas Sektor"),
        ("OXY",   +0.80, "Rohoel-Foerderung"),
    ],
    "JPM": [
        ("BAC",   +0.85, "US-Grossbanken bewegen sich gemeinsam"),
        ("GS",    +0.80, "Investment-Banking"),
        ("MS",    +0.80, "Finanzsektor"),
        ("C",     +0.80, "Grossbank"),
    ],
    "AMZN": [
        ("GOOGL", +0.70, "Cloud & Werbung"),
        ("MSFT",  +0.70, "Cloud-Infrastruktur"),
        ("SHOP",  +0.65, "E-Commerce-Sektor"),
    ],
    "META": [
        ("GOOGL", +0.75, "Online-Werbung Duopol"),
        ("SNAP",  +0.65, "Social-Media-Werbung"),
        ("PINS",  +0.60, "Social-Media-Plattform"),
    ],
    "GOOGL": [
        ("META",  +0.75, "Online-Werbung"),
        ("MSFT",  +0.70, "Big Tech, Cloud"),
        ("AMZN",  +0.65, "Cloud & Technologie"),
    ],
}

# Makro-Ereignisse und ihre Sektorauswirkungen
MAKRO_EVENTS = {
    "zinserhoehung": {
        "beschreibung": "Zinserhöhung oder Zinsangst",
        "negativ": ["TSLA", "NVDA", "META", "AMZN", "GOOGL", "BTC", "ETH"],
        "positiv": ["JPM", "BAC", "GS", "MS", "XOM"],
    },
    "rezessionsangst": {
        "beschreibung": "Rezessionsangst / schwache Wirtschaftsdaten",
        "negativ": ["TSLA", "AMZN", "HD", "LOW"],
        "positiv": ["WMT", "COST", "JNJ", "PG", "KO"],
    },
    "krypto_rally": {
        "beschreibung": "Krypto-Markt im Aufwind",
        "negativ": [],
        "positiv": ["COIN", "MSTR", "HOOD", "SQ"],
    },
    "ki_boom": {
        "beschreibung": "KI-Investitionen steigen",
        "negativ": [],
        "positiv": ["NVDA", "AMD", "MSFT", "GOOGL", "META", "AVGO"],
    },
}


# ---------------------------------------------------------------------------
# Statistische Korrelation berechnen
# ---------------------------------------------------------------------------

@dataclass
class KorrelationsPaar:
    asset_a: str
    asset_b: str
    korrelation: float       # -1.0 bis +1.0
    zeitraum_tage: int
    staerke: str             # "stark", "moderat", "schwach", "negativ"
    interpretation: str


@dataclass
class KorrelationsAnalyse:
    asset: str
    statistische_paare: list[KorrelationsPaar] = field(default_factory=list)
    thematische_links: list[dict] = field(default_factory=list)
    verstarkende_signale: list[str] = field(default_factory=list)
    warnungen: list[str] = field(default_factory=list)
    verwandte_kaufkandidaten: list[str] = field(default_factory=list)


def berechne_korrelation(
    ticker_a: str,
    ticker_b: str,
    zeitraum: str = "3mo",
) -> float | None:
    """Berechnet die Pearson-Korrelation zwischen zwei Assets."""
    try:
        daten = yf.download(
            [ticker_a, ticker_b],
            period=zeitraum,
            interval="1d",
            auto_adjust=True,
            progress=False,
        )
        if daten.empty:
            return None

        if hasattr(daten.columns, "levels"):
            close_a = daten["Close"][ticker_a].dropna()
            close_b = daten["Close"][ticker_b].dropna()
        else:
            return None

        # Renditen berechnen (stabiler als Rohpreise)
        renditen_a = close_a.pct_change().dropna()
        renditen_b = close_b.pct_change().dropna()

        gemeinsam = pd.concat([renditen_a, renditen_b], axis=1).dropna()
        if len(gemeinsam) < 20:
            return None

        return round(float(gemeinsam.iloc[:, 0].corr(gemeinsam.iloc[:, 1])), 3)

    except Exception:
        return None


def _korrelations_staerke(wert: float) -> tuple[str, str]:
    """Gibt Staerken-Label und Interpretation zurueck."""
    abs_wert = abs(wert)
    richtung = "positiv" if wert > 0 else "negativ"

    if abs_wert >= 0.80:
        return "stark", f"Sehr starke {richtung}e Korrelation — bewegen sich fast im Gleichschritt"
    elif abs_wert >= 0.60:
        return "moderat", f"Moderate {richtung}e Korrelation — aehnliche Reaktion auf Marktbewegungen"
    elif abs_wert >= 0.40:
        return "schwach", f"Schwache {richtung}e Korrelation — gelegentlich gleichlaeufig"
    else:
        return "keine", "Kaum Korrelation — Assets bewegen sich unabhaengig"


# ---------------------------------------------------------------------------
# Hauptanalyse
# ---------------------------------------------------------------------------

def analysiere_korrelationen(
    asset: str,
    aktuelle_signale: dict,       # alle heutigen Signale {ticker: empfehlung}
    berechne_statistisch: bool = True,
) -> KorrelationsAnalyse:
    """
    Fuehrt die vollstaendige Korrelationsanalyse fuer ein Asset durch.
    Kombiniert statistische und thematische Ansaetze.
    """
    analyse = KorrelationsAnalyse(asset=asset)

    # --- Thematische Korrelationen ---
    if asset in THEMATISCHE_KORRELATIONEN:
        for (korr_asset, korr_wert, begruendung) in THEMATISCHE_KORRELATIONEN[asset]:
            link = {
                "asset":        korr_asset,
                "korrelation":  korr_wert,
                "begruendung":  begruendung,
                "signal":       aktuelle_signale.get(korr_asset, "–"),
            }
            analyse.thematische_links.append(link)

            # Wenn korreliertes Asset auch KAUFEN-Signal hat -> verstaerkt Signal
            if (korr_wert > 0.70 and
                    aktuelle_signale.get(korr_asset) == "KAUFEN"):
                analyse.verstarkende_signale.append(
                    f"{korr_asset} zeigt ebenfalls KAUFEN ({korr_wert:.0%} Korrelation) — "
                    f"verstaerkt das Signal fuer {asset}"
                )

            # Verwandte Kaufkandidaten die noch nicht analysiert wurden
            if (korr_wert > 0.65 and
                    korr_asset not in aktuelle_signale and
                    korr_asset not in analyse.verwandte_kaufkandidaten):
                analyse.verwandte_kaufkandidaten.append(korr_asset)

    # --- Statistische Korrelation fuer Top-Partner ---
    if berechne_statistisch and asset in THEMATISCHE_KORRELATIONEN:
        top_partner = [p[0] for p in THEMATISCHE_KORRELATIONEN[asset][:3]]
        for partner in top_partner:
            korr = berechne_korrelation(asset, partner)
            if korr is not None:
                staerke, interpretation = _korrelations_staerke(korr)
                analyse.statistische_paare.append(KorrelationsPaar(
                    asset_a=asset,
                    asset_b=partner,
                    korrelation=korr,
                    zeitraum_tage=90,
                    staerke=staerke,
                    interpretation=interpretation,
                ))
            time.sleep(0.3)

    # --- Warnungen wenn Korrelation Widerspruch zeigt ---
    for paar in analyse.statistische_paare:
        # Negativkorrelation zu einem als KAUFEN bewerteten Asset
        if (paar.korrelation < -0.60 and
                aktuelle_signale.get(paar.asset_b) == "KAUFEN"):
            analyse.warnungen.append(
                f"{paar.asset_b} zeigt KAUFEN, ist aber negativ korreliert "
                f"({paar.korrelation:.2f}) zu {asset} — widersprueliche Signale"
            )

    return analyse


def analysiere_alle_korrelationen(
    signale: list[dict],
) -> dict[str, KorrelationsAnalyse]:
    """Analysiert Korrelationen fuer alle Assets im Tagesbericht."""
    signal_map = {s["asset"]: s.get("finale", {}).get("empfehlung", "–") for s in signale}
    ergebnisse = {}

    for signal in signale:
        asset = signal["asset"]
        if asset in THEMATISCHE_KORRELATIONEN:
            analyse = analysiere_korrelationen(asset, signal_map)
            ergebnisse[asset] = analyse

    return ergebnisse


# ---------------------------------------------------------------------------
# Ausgabe
# ---------------------------------------------------------------------------

def drucke_korrelations_analyse(analyse: KorrelationsAnalyse):
    breite = 62
    print(f"\n  KORRELATIONEN: {analyse.asset}")
    print("  " + "-" * (breite - 2))

    if analyse.thematische_links:
        print("  Thematisch verwandte Assets:")
        for link in analyse.thematische_links:
            signal_str = f"[{link['signal']}]" if link["signal"] != "–" else ""
            print(f"    {link['asset']:<6} {link['korrelation']:+.0%}  "
                  f"{signal_str:<12} {link['begruendung'][:45]}")

    if analyse.statistische_paare:
        print("\n  Statistische Korrelation (letzte 90 Tage):")
        for paar in analyse.statistische_paare:
            balken = "█" * int(abs(paar.korrelation) * 10)
            print(f"    {paar.asset_b:<6} {paar.korrelation:+.3f}  {balken:<10}  "
                  f"{paar.staerke}")

    if analyse.verstarkende_signale:
        print("\n  Verstaerkende Signale:")
        for v in analyse.verstarkende_signale:
            print(f"    + {v}")

    if analyse.warnungen:
        print("\n  Warnungen:")
        for w in analyse.warnungen:
            print(f"    ! {w}")

    if analyse.verwandte_kaufkandidaten:
        print(f"\n  Ggf. auch pruefen: {', '.join(analyse.verwandte_kaufkandidaten)}")


# ---------------------------------------------------------------------------
# Einstiegspunkt
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Trading Intelligence System — Korrelations-Agent\n")

    # Beispiel-Signale simulieren
    test_signale = [
        {"asset": "BTC",  "finale": {"empfehlung": "KAUFEN"}},
        {"asset": "NVDA", "finale": {"empfehlung": "KAUFEN"}},
        {"asset": "TSLA", "finale": {"empfehlung": "ABWARTEN"}},
    ]

    signal_map = {s["asset"]: s["finale"]["empfehlung"] for s in test_signale}

    for s in test_signale:
        asset = s["asset"]
        print(f"  Analysiere {asset}...", end=" ", flush=True)
        analyse = analysiere_korrelationen(asset, signal_map, berechne_statistisch=True)
        print("OK")
        drucke_korrelations_analyse(analyse)
        print()
