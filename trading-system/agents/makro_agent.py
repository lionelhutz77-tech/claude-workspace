"""
Makro-Agent
Erkennt marktbewegende Makro-Ereignisse aus den News und bewertet
deren Auswirkung auf verschiedene Asset-Klassen.

Erkannte Ereignisse:
  - Fed/EZB Zinsentscheidungen und Statements
  - Geopolitische Konflikte (Oel, Sicherheit)
  - Inflationsdaten (CPI, PPI)
  - Wirtschaftsdaten (GDP, Arbeitsmarkt)
  - Regulierung (Krypto-Verbote, SEC-Entscheidungen)
  - Institutionelle Bewegungen (ETF-Fluesse, Whale-Verkäufe)
"""

import sys
from dataclasses import dataclass, field

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


# ---------------------------------------------------------------------------
# Makro-Event Definitionen
# ---------------------------------------------------------------------------

MAKRO_EVENTS = {
    # --- Zinspolitik ---
    "zinserhoehung": {
        "keywords": ["rate hike", "zinserhoehung", "fed raises", "zinsanstieg",
                     "higher rates", "hawkish", "tightening", "25 basis points",
                     "50 basis points", "fed hikes", "boe raises", "ecb raises"],
        "negativ_assets": ["BTC", "ETH", "SOL", "TSLA", "NVDA", "META", "AMZN",
                           "GOOGL", "NFLX", "ARKK", "growth stocks", "MC", "SMCI", "AMD"],
        "positiv_assets": ["JPM", "BAC", "GS", "MS", "WFC", "C", "USB",
                           "XOM", "CVX", "USD", "ALV"],
        "staerke": -3,
        "beschreibung": "Zinserhöhung — teures Geld schadet Wachstumswerten & Krypto",
    },
    "zinssenkung": {
        "keywords": ["rate cut", "zinssenkung", "fed cuts", "dovish", "easing",
                     "lower rates", "fed pivot", "fed senkt", "zins sinkt"],
        "negativ_assets": ["JPM", "BAC", "GS", "ALV"],
        "positiv_assets": ["BTC", "ETH", "TSLA", "NVDA", "META", "growth", "MC", "AMD", "SMCI"],
        "staerke": +3,
        "beschreibung": "Zinssenkung — billiges Geld treibt Wachstumswerte & Krypto",
    },
    "zinsangst": {
        "keywords": ["inflation fears", "rate fears", "fed hawkish", "higher for longer",
                     "inflationsangst", "zinsdruck", "no rate cuts", "delay cut",
                     "federal reserve warns", "fed signals"],
        "negativ_assets": ["BTC", "ETH", "TSLA", "NVDA", "growth"],
        "positiv_assets": ["XOM", "CVX", "GS", "JPM"],
        "staerke": -2,
        "beschreibung": "Zinsangst — Markt fuerchtet laenger hohe Zinsen",
    },

    # --- Inflation ---
    "hohe_inflation": {
        "keywords": ["cpi rises", "inflation surges", "hot inflation", "above expectations",
                     "inflation hoeher", "verbraucherpreise steigen", "ppi rises"],
        "negativ_assets": ["BTC", "ETH", "TSLA", "growth", "bonds"],
        "positiv_assets": ["GOLD", "XOM", "CVX", "commodity"],
        "staerke": -2,
        "beschreibung": "Hohe Inflation — Kaufkraft sinkt, Zinserhoehung droht",
    },
    "niedrige_inflation": {
        "keywords": ["cpi falls", "inflation cools", "deflation", "inflation below",
                     "inflation sinkt", "preise fallen", "disinflation"],
        "negativ_assets": ["XOM", "CVX", "commodity"],
        "positiv_assets": ["BTC", "ETH", "TSLA", "NVDA", "growth", "bonds"],
        "staerke": +2,
        "beschreibung": "Sinkende Inflation — Zinssenkungen wahrscheinlicher",
    },

    # --- Geopolitik ---
    "krieg_konflikt": {
        "keywords": ["war", "conflict", "military", "attack", "invasion", "strike",
                     "krieg", "konflikt", "angriff", "eskalation", "sanctions",
                     "iran", "russia", "china taiwan", "middle east"],
        "negativ_assets": ["BTC", "ETH", "TSLA", "growth", "SPY", "market", "MC", "EVK"],
        "positiv_assets": ["GOLD", "XOM", "CVX", "LMT", "NOC", "GD", "RTX", "RHM", "AVAV"],
        "staerke": -2,
        "beschreibung": "Geopolitische Eskalation — Risikoaversion, Oel steigt",
    },
    "deeskalation": {
        "keywords": ["ceasefire", "peace talks", "deal reached", "tensions ease",
                     "waffenstillstand", "friedensgespraeche", "deeskalation",
                     "iran deal", "nuclear deal", "peace deal", "agreement reached",
                     "diplomatic breakthrough", "sanctions lifted", "einigung erzielt"],
        "negativ_assets": ["GOLD", "LMT", "NOC", "GD", "RTX", "RHM", "AVAV"],
        "positiv_assets": ["BTC", "ETH", "growth", "SPY", "DAL", "UAL", "AAL", "MC", "AMD"],
        "staerke": +2,
        "beschreibung": "Geopolitische Entspannung — Risikofreude kehrt zurueck, Gold/Ruestung fallen",
    },
    "oelpreis_crash": {
        "keywords": ["oil price crash", "oil plunges", "crude falls", "oil supply surge",
                     "opec increase", "iran oil", "sanctions relief oil", "oil glut",
                     "oelpreis faellt", "oelpreis sinkt", "rohoel crash", "brent falls",
                     "wti falls", "oil surplus", "energy prices fall"],
        "negativ_assets": ["XOM", "CVX", "COP", "BP", "SLB", "HAL", "MRO"],
        "positiv_assets": ["DAL", "UAL", "AAL", "FDX", "UPS", "AMZN", "consumer", "EVK"],
        "staerke": -2,
        "beschreibung": "Oelpreiscrash — Energieaktien fallen, Transport/Konsum profitieren; Chemie (EVK) profitiert",
    },
    "oelpreis_anstieg": {
        "keywords": ["oil price surge", "crude rallies", "oil supply cut", "opec cut",
                     "oil spike", "energy crisis", "oelpreis steigt", "oelpreisanstieg",
                     "rohoel steigt", "brent rallies", "wti surges", "oil shortage"],
        "negativ_assets": ["DAL", "UAL", "AAL", "FDX", "consumer", "AMZN", "EVK"],
        "positiv_assets": ["XOM", "CVX", "COP", "BP", "SLB", "GOLD"],
        "staerke": -1,
        "beschreibung": "Oelpreisanstieg — Energiekosten steigen, Transport & Chemie (EVK) leiden",
    },

    # --- Krypto-spezifisch ---
    "btc_etf_abfluesse": {
        "keywords": ["etf outflows", "bitcoin etf sell", "etf abfluesse", "etf selling",
                     "institutional selling", "etf redemption", "spot etf outflows"],
        "negativ_assets": ["BTC", "ETH", "SOL", "COIN", "MSTR"],
        "positiv_assets": [],
        "staerke": -3,
        "beschreibung": "BTC-ETF Abfluesse — institutionelle Investoren verkaufen",
    },
    "btc_etf_zufluesse": {
        "keywords": ["etf inflows", "bitcoin etf buy", "etf zufluesse", "institutional buying",
                     "spot etf inflows", "record inflows", "blackrock bitcoin"],
        "negativ_assets": [],
        "positiv_assets": ["BTC", "ETH", "SOL", "COIN", "MSTR"],
        "staerke": +3,
        "beschreibung": "BTC-ETF Zufluesse — institutionelle Nachfrage steigt",
    },
    "krypto_regulierung_negativ": {
        "keywords": ["crypto ban", "sec crackdown", "krypto verbot", "regulate crypto",
                     "bitcoin illegal", "crypto sanctions", "sec charges", "cftc"],
        "negativ_assets": ["BTC", "ETH", "SOL", "XRP", "COIN"],
        "positiv_assets": [],
        "staerke": -3,
        "beschreibung": "Negative Krypto-Regulierung — rechtliche Unsicherheit steigt",
    },
    "krypto_regulierung_positiv": {
        "keywords": ["crypto approved", "bitcoin legal", "etf approved", "regulatory clarity",
                     "crypto friendly", "bitcoin reserve", "strategic reserve"],
        "negativ_assets": [],
        "positiv_assets": ["BTC", "ETH", "SOL", "COIN", "MSTR"],
        "staerke": +3,
        "beschreibung": "Positive Krypto-Regulierung — rechtliche Klarheit steigt",
    },

    # --- Whale / Institutionen ---
    "whale_verkauf": {
        "keywords": ["microstrategy sells", "whale sells", "large bitcoin transfer",
                     "miner selling", "mt gox", "government sells bitcoin",
                     "microstrategy sold", "large sell"],
        "negativ_assets": ["BTC", "ETH", "COIN", "MSTR"],
        "positiv_assets": [],
        "staerke": -2,
        "beschreibung": "Whale-/Institutionen-Verkauf — grosser Verkaufsdruck",
    },

    # --- Wirtschaft ---
    "rezession": {
        "keywords": ["recession", "gdp falls", "gdp shrinks", "economic contraction",
                     "rezession", "wirtschaftseinbruch", "negative growth", "downturn"],
        "negativ_assets": ["TSLA", "AMZN", "HD", "LOW", "BTC", "growth", "MC", "EVK", "RHM"],
        "positiv_assets": ["WMT", "COST", "JNJ", "PG", "KO", "GOLD", "ALV"],
        "staerke": -3,
        "beschreibung": "Rezessionsangst — defensiv und Gold als sicherer Hafen",
    },
    "starke_wirtschaft": {
        "keywords": ["strong gdp", "jobs beat", "unemployment low", "economy strong",
                     "wirtschaft waechst", "beschaeftigung stark", "gdp beats"],
        "negativ_assets": [],
        "positiv_assets": ["SPY", "growth", "AMZN", "HD", "TSLA", "MC", "EVK", "AMD"],
        "staerke": +2,
        "beschreibung": "Starke Wirtschaft — Konsumwerte, Zykliker und Luxusgüter (MC) profitieren",
    },
}


# ---------------------------------------------------------------------------
# Erkennungs-Funktion
# ---------------------------------------------------------------------------

@dataclass
class MakroSignal:
    event_typ: str
    beschreibung: str
    staerke: int                    # -3 bis +3
    betroffene_assets_negativ: list[str] = field(default_factory=list)
    betroffene_assets_positiv: list[str] = field(default_factory=list)
    gefundene_keywords: list[str]   = field(default_factory=list)
    quellen: list[str]              = field(default_factory=list)


def erkenne_makro_events(nachrichten: list) -> list[MakroSignal]:
    """
    Durchsucht alle heutigen Nachrichten nach Makro-Events.
    Gibt eine Liste erkannter Ereignisse zurueck.
    """
    gefundene_events = []

    for event_typ, config in MAKRO_EVENTS.items():
        keywords_gefunden = []
        quellen_gefunden  = []

        for nachricht in nachrichten:
            text = ""
            # Unterstuetzt sowohl dict als auch Dataclass
            if hasattr(nachricht, "titel"):
                text = (nachricht.titel + " " + nachricht.zusammenfassung).lower()
            elif isinstance(nachricht, dict):
                text = (nachricht.get("titel", "") + " " +
                        nachricht.get("zusammenfassung", "")).lower()

            treffer = [kw for kw in config["keywords"] if kw in text]
            if treffer:
                keywords_gefunden.extend(treffer)
                quelle = getattr(nachricht, "quelle", "") or (nachricht.get("quelle", "") if isinstance(nachricht, dict) else "")
                if quelle not in quellen_gefunden:
                    quellen_gefunden.append(quelle)

        if keywords_gefunden:
            gefundene_events.append(MakroSignal(
                event_typ=event_typ,
                beschreibung=config["beschreibung"],
                staerke=config["staerke"],
                betroffene_assets_negativ=config["negativ_assets"],
                betroffene_assets_positiv=config["positiv_assets"],
                gefundene_keywords=list(set(keywords_gefunden))[:5],
                quellen=quellen_gefunden[:3],
            ))

    # Nach Staerke sortieren (stärkste Events zuerst)
    gefundene_events.sort(key=lambda x: abs(x.staerke), reverse=True)
    return gefundene_events


def makro_einfluss_auf_asset(asset: str, makro_signale: list[MakroSignal]) -> tuple[int, list[str]]:
    """
    Berechnet den Makro-Gesamteinfluss auf ein bestimmtes Asset.
    Gibt (punkte, begruendungen) zurueck.
    """
    punkte       = 0
    begruendungen = []

    for sig in makro_signale:
        asset_betroffen_negativ = any(
            a.upper() in asset.upper() or asset.upper() in a.upper()
            for a in sig.betroffene_assets_negativ
        )
        asset_betroffen_positiv = any(
            a.upper() in asset.upper() or asset.upper() in a.upper()
            for a in sig.betroffene_assets_positiv
        )

        if asset_betroffen_negativ:
            punkte -= sig.staerke if sig.staerke > 0 else abs(sig.staerke)
            begruendungen.append(
                f"Makro NEGATIV: {sig.beschreibung} (Staerke: {sig.staerke})"
            )
        elif asset_betroffen_positiv:
            punkte += abs(sig.staerke)
            begruendungen.append(
                f"Makro POSITIV: {sig.beschreibung} (Staerke: +{abs(sig.staerke)})"
            )

    return punkte, begruendungen


def drucke_makro_lage(signale: list[MakroSignal]):
    if not signale:
        print("  Keine signifikanten Makro-Events heute erkannt.")
        return

    print(f"\n  MAKRO-LAGE ({len(signale)} Events erkannt):")
    for sig in signale:
        richtung = "⚠️ NEGATIV" if sig.staerke < 0 else "✅ POSITIV"
        print(f"  {richtung} [{sig.staerke:+d}] {sig.beschreibung}")
        print(f"    Keywords: {', '.join(sig.gefundene_keywords[:3])}")
        if sig.betroffene_assets_negativ[:4]:
            print(f"    Betrifft negativ: {', '.join(sig.betroffene_assets_negativ[:4])}")
        if sig.betroffene_assets_positiv[:4]:
            print(f"    Betrifft positiv: {', '.join(sig.betroffene_assets_positiv[:4])}")
