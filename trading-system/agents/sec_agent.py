"""
SEC EDGAR Agent — Insider-Transaktionen + Material Events

Liest taeglich:
  Form 4  — Insider-Kaeufe/-Verkaeufe von Managern und Directors
  8-K     — Material Events: Accounting-Flags, Restatements, Executive-Abgaenge

Kein API-Key. Kein kostenpflichtiger Dienst. Offiziell von SEC EDGAR (kostenlos).

Signale:
  CEO/CFO kauft Aktien (>$10k)   → +3 Punkte
  Director kauft (>$5k)          → +2 Punkte
  Insider verkauft               → -1 Punkt
  8-K Accounting-Warnung         → -3 Punkte + KAUFEN-Veto
  8-K Positiv (Akquisition etc.) → +1 Punkt
"""

import json
import time
import re
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, field
from xml.etree import ElementTree as ET
import urllib.request

# ─── Pfade ────────────────────────────────────────────────────────────────────
_BASE_DIR   = Path(__file__).parent.parent
_CACHE_DIR  = _BASE_DIR / "data" / "sec_cache"
_CACHE_DIR.mkdir(parents=True, exist_ok=True)
_CIK_DATEI  = _CACHE_DIR / "cik_mapping.json"

# SEC-Pflicht: User-Agent muss gesetzt sein
_USER_AGENT = "TradingIntelligenceSystem research@trading-system.local"

# In-Memory CIK Cache
_CIK_MAP: dict[str, str] = {}

# Rate-Limit: max 8 Req/s (SEC erlaubt 10)
_LETZTER_REQ = 0.0
_MIN_PAUSE   = 0.13

# Kryptos haben keine EDGAR-Eintraege
_KRYPTOS = {"BTC", "ETH", "SOL", "XRP", "ADA", "DOGE", "BNB", "MATIC",
            "AVAX", "DOT", "LINK", "UNI", "ATOM", "LTC", "BCH", "QBTS"}


# ─── HTTP-Helfer ──────────────────────────────────────────────────────────────

def _fetch_json(url: str) -> dict | None:
    global _LETZTER_REQ
    delta = _MIN_PAUSE - (time.time() - _LETZTER_REQ)
    if delta > 0:
        time.sleep(delta)
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": _USER_AGENT, "Accept": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            _LETZTER_REQ = time.time()
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        print(f"    [SEC] Fehler {url[-60:]}: {type(e).__name__}")
        return None


def _fetch_text(url: str) -> str:
    global _LETZTER_REQ
    delta = _MIN_PAUSE - (time.time() - _LETZTER_REQ)
    if delta > 0:
        time.sleep(delta)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
        with urllib.request.urlopen(req, timeout=15) as r:
            _LETZTER_REQ = time.time()
            return r.read().decode("utf-8", errors="replace")
    except Exception:
        return ""


# ─── CIK-Mapping ──────────────────────────────────────────────────────────────

def _lade_cik_map():
    global _CIK_MAP
    if _CIK_DATEI.exists():
        try:
            _CIK_MAP = json.loads(_CIK_DATEI.read_text())
            return
        except Exception:
            pass
    # Frisch laden
    daten = _fetch_json("https://www.sec.gov/files/company_tickers.json")
    if daten:
        for _, e in daten.items():
            _CIK_MAP[e.get("ticker", "").upper()] = str(e.get("cik_str", "")).zfill(10)
        _CIK_DATEI.write_text(json.dumps(_CIK_MAP))


def hole_cik(ticker: str) -> str | None:
    if not _CIK_MAP:
        _lade_cik_map()
    return _CIK_MAP.get(ticker.upper())


# ─── Datenstrukturen ──────────────────────────────────────────────────────────

@dataclass
class InsiderTransaktion:
    ticker:     str
    datum:      str
    name:       str
    rolle:      str          # CEO, CFO, Director, Officer
    aktion:     str          # KAUF / VERKAUF
    aktien:     float
    preis:      float
    volumen:    float        # aktien × preis
    punkte:     int


@dataclass
class AchtKMeldung:
    ticker:     str
    datum:      str
    betreff:    str
    kategorie:  str          # WARNUNG / POSITIV / NEUTRAL
    punkte:     int


@dataclass
class SecSignal:
    ticker:                 str
    insider:                list[InsiderTransaktion] = field(default_factory=list)
    meldungen:              list[AchtKMeldung]       = field(default_factory=list)
    gesamt_punkte:          int   = 0
    zusammenfassung:        str   = ""
    hat_schwere_warnung:    bool  = False


# ─── Form 4 Parser ────────────────────────────────────────────────────────────

def _parse_form4(xml: str, ticker: str) -> list[InsiderTransaktion]:
    """Parst Form 4 XML und gibt Insider-Transaktionen zurueck."""
    result = []
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return []

    # Wer hat gemeldet?
    name = "Unbekannt"
    rolle = "Insider"
    for owner in root.findall(".//reportingOwner"):
        n = (owner.findtext(".//rptOwnerName") or "").strip()
        if n:
            name = n
        rel = owner.find(".//reportingOwnerRelationship")
        if rel is not None:
            if rel.findtext("isDirector", "0") == "1":
                rolle = "Director"
            if rel.findtext("isOfficer", "0") == "1":
                titel = (rel.findtext("officerTitle") or "").strip()
                rolle = titel if titel else "Officer"

    datum = root.findtext(".//periodOfReport", datetime.now().strftime("%Y-%m-%d"))

    for t in root.findall(".//nonDerivativeTransaction"):
        code = (t.findtext(".//transactionCode") or "").strip().upper()
        if code not in ("P", "S"):
            continue  # Nur Open-Market Käufe (P) und Verkäufe (S)

        try:
            aktien = abs(float(t.findtext(".//transactionShares/value") or 0))
            preis  = abs(float(t.findtext(".//transactionPricePerShare/value") or 0))
        except (ValueError, TypeError):
            continue

        if aktien <= 0:
            continue

        volumen = aktien * preis
        aktion  = "KAUF" if code == "P" else "VERKAUF"

        # Kleine Transaktionen < $5k ignorieren (Reinvestition, Kleinstbetraege)
        if volumen < 5000:
            continue

        # Bonus-Punkte: CEO/CFO-Kauf besonders wertvoll
        if aktion == "KAUF":
            rolle_lower = rolle.lower()
            if any(r in rolle_lower for r in ("chief executive", "ceo")):
                punkte = 4
            elif any(r in rolle_lower for r in ("chief financial", "cfo", "president")):
                punkte = 3
            else:
                punkte = 2
        else:
            punkte = -1  # Verkauf weniger aussagekraeftig

        result.append(InsiderTransaktion(
            ticker=ticker, datum=datum, name=name, rolle=rolle,
            aktion=aktion, aktien=aktien, preis=preis,
            volumen=volumen, punkte=punkte,
        ))

    return result


# ─── 8-K Kategorisierung ─────────────────────────────────────────────────────

_SCHWERE_WARNUNGEN = [
    "restatement", "restate", "material weakness", "going concern",
    "sec investigation", "sec inquiry", "subpoena", "accounting error",
    "internal control", "fraud", "irregularities", "audit committee investigation",
    "delisting", "nasdaq notice", "nyse notice", "informal inquiry",
]
_MITTLERE_WARNUNGEN = [
    "departure", "resignation", "terminated", "dismissal",
    "ceo", "chief executive", "chief financial", "cfo",
]
_POSITIV_KW = [
    "acquisition", "merger", "buyback", "share repurchase", "dividend increase",
    "new contract", "strategic partnership", "expansion", "fda approval",
    "fda clearance", "patent grant", "record revenue", "record earnings",
    "joint venture",
]


def _kategorisiere_8k(betreff: str) -> tuple[str, int]:
    b = betreff.lower()
    if any(kw in b for kw in _SCHWERE_WARNUNGEN):
        return "WARNUNG", -3
    if any(kw in b for kw in _MITTLERE_WARNUNGEN):
        return "WARNUNG", -1
    if any(kw in b for kw in _POSITIV_KW):
        return "POSITIV", +1
    return "NEUTRAL", 0


# ─── Hauptanalyse ─────────────────────────────────────────────────────────────

def analysiere_ticker(ticker: str, tage: int = 7) -> SecSignal | None:
    """Analysiert Form 4 und 8-K der letzten N Tage fuer einen Ticker."""
    if ticker.upper() in _KRYPTOS:
        return None

    cik = hole_cik(ticker)
    if not cik:
        return None

    # Tages-Cache (ein Fetch pro Tag pro Ticker)
    heute = datetime.now().strftime("%Y-%m-%d")
    cache = _CACHE_DIR / f"{ticker}_{heute}.json"
    if cache.exists():
        try:
            return _von_dict(json.loads(cache.read_text()))
        except Exception:
            pass

    subs = _fetch_json(f"https://data.sec.gov/submissions/CIK{cik}.json")
    if not subs:
        return None

    recent = subs.get("filings", {}).get("recent", {})
    if not recent:
        return None

    formen    = recent.get("form", [])
    daten_l   = recent.get("filingDate", [])
    acc_l     = recent.get("accessionNumber", [])
    dok_l     = recent.get("primaryDocument", [])
    items_l   = recent.get("items", [""] * len(formen))

    grenze = (datetime.now() - timedelta(days=tage)).date()
    signal = SecSignal(ticker=ticker)
    cik_int = int(cik)

    for form, dat_str, acc, dok, items in zip(formen, daten_l, acc_l, dok_l, items_l):
        try:
            dat = datetime.strptime(dat_str, "%Y-%m-%d").date()
        except ValueError:
            continue
        if dat < grenze:
            break

        acc_clean = acc.replace("-", "")

        if form == "4":
            url = f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc_clean}/{dok}"
            xml = _fetch_text(url)
            if xml:
                signal.insider.extend(_parse_form4(xml, ticker))

        elif form in ("8-K", "8-K/A"):
            betreff = (items or dok or "").strip()
            kat, pts = _kategorisiere_8k(betreff)
            if kat != "NEUTRAL":  # Nur relevante 8-K speichern
                signal.meldungen.append(AchtKMeldung(
                    ticker=ticker, datum=dat_str,
                    betreff=betreff, kategorie=kat, punkte=pts,
                ))

    # Score + Zusammenfassung
    signal.gesamt_punkte = (
        sum(t.punkte for t in signal.insider) +
        sum(m.punkte for m in signal.meldungen)
    )

    teile = []
    kaeufe = [t for t in signal.insider if t.aktion == "KAUF"]
    if kaeufe:
        vol = sum(t.volumen for t in kaeufe)
        groesster = max(kaeufe, key=lambda x: x.volumen)
        teile.append(
            f"Insider-Kauf: {groesster.rolle} {groesster.name} "
            f"(${vol:,.0f} gesamt, {len(kaeufe)} Transakt.)"
        )

    schwere = [m for m in signal.meldungen if m.punkte <= -3]
    if schwere:
        signal.hat_schwere_warnung = True
        teile.append(f"8-K ALARM: {schwere[0].betreff[:70]}")
    elif signal.meldungen:
        pos = [m for m in signal.meldungen if m.punkte > 0]
        if pos:
            teile.append(f"8-K positiv: {pos[0].betreff[:60]}")

    signal.zusammenfassung = " | ".join(teile)

    # Cachen
    try:
        cache.write_text(json.dumps(_zu_dict(signal)))
    except Exception:
        pass

    return signal


def _zu_dict(s: SecSignal) -> dict:
    return {
        "ticker": s.ticker,
        "gesamt_punkte": s.gesamt_punkte,
        "zusammenfassung": s.zusammenfassung,
        "hat_schwere_warnung": s.hat_schwere_warnung,
        "insider": [
            {"datum": t.datum, "name": t.name, "rolle": t.rolle,
             "aktion": t.aktion, "aktien": t.aktien, "preis": t.preis,
             "volumen": t.volumen, "punkte": t.punkte}
            for t in s.insider
        ],
        "meldungen": [
            {"datum": m.datum, "betreff": m.betreff,
             "kategorie": m.kategorie, "punkte": m.punkte}
            for m in s.meldungen
        ],
    }


def _von_dict(d: dict) -> SecSignal:
    s = SecSignal(
        ticker=d["ticker"],
        gesamt_punkte=d.get("gesamt_punkte", 0),
        zusammenfassung=d.get("zusammenfassung", ""),
        hat_schwere_warnung=d.get("hat_schwere_warnung", False),
    )
    for t in d.get("insider", []):
        s.insider.append(InsiderTransaktion(
            ticker=d["ticker"], datum=t["datum"], name=t["name"],
            rolle=t["rolle"], aktion=t["aktion"], aktien=t["aktien"],
            preis=t["preis"], volumen=t["volumen"], punkte=t["punkte"],
        ))
    for m in d.get("meldungen", []):
        s.meldungen.append(AchtKMeldung(
            ticker=d["ticker"], datum=m["datum"], betreff=m["betreff"],
            kategorie=m["kategorie"], punkte=m["punkte"],
        ))
    return s


# ─── Aggregierter Scan ────────────────────────────────────────────────────────

def scanne_alle(tickers: list[str], tage: int = 7) -> dict[str, SecSignal]:
    """Scannt alle Ticker und gibt nur relevante Signale zurueck."""
    ergebnisse: dict[str, SecSignal] = {}
    aktien = [t for t in tickers if t.upper() not in _KRYPTOS]

    for ticker in aktien:
        try:
            sig = analysiere_ticker(ticker, tage)
            if sig and (sig.insider or sig.meldungen):
                ergebnisse[ticker] = sig
                if sig.zusammenfassung:
                    icon = "🟢" if sig.gesamt_punkte > 0 else "🔴"
                    print(f"    {icon} {ticker}: {sig.zusammenfassung}")
        except Exception as e:
            pass

    return ergebnisse


def wende_sec_an(signal: dict, sec_signale: dict[str, SecSignal]) -> dict:
    """
    Wendet SEC-Insider/8-K-Punkte auf ein aggregiertes Signal an.
    Hartes VETO bei schwerer 8-K Warnung (Accounting, Fraud etc.)
    """
    ticker = signal.get("asset", "")
    if ticker not in sec_signale:
        return signal

    sec = sec_signale[ticker]
    if sec.gesamt_punkte == 0 and not sec.hat_schwere_warnung:
        return signal

    signal = dict(signal)
    signal["gesamt_punkte"] = round(
        signal.get("gesamt_punkte", 0) + sec.gesamt_punkte, 2
    )

    if sec.zusammenfassung:
        pfeil = "🟢" if sec.gesamt_punkte > 0 else "🔴"
        signal.setdefault("begruendung", []).append(
            f"{pfeil} SEC: {sec.zusammenfassung}"
        )

    # Schwere Warnung → Kaufen blockieren (SMCI-Regel)
    if sec.hat_schwere_warnung:
        if signal.get("empfehlung") == "KAUFEN":
            signal["empfehlung"] = "ABWARTEN"
            signal.setdefault("begruendung", []).append(
                "⚠️ SEC-VETO: Schwere 8-K Warnung — KAUFEN blockiert"
            )

    signal["sec_punkte"] = sec.gesamt_punkte
    return signal


# ─── Standalone-Test ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("SEC EDGAR Agent — Test\n")
    test_ticker = ["MSFT", "NVDA", "SMCI", "PLTR"]
    for t in test_ticker:
        print(f"\n{t} wird analysiert...")
        sig = analysiere_ticker(t, tage=30)
        if sig:
            print(f"  Punkte: {sig.gesamt_punkte:+d}")
            print(f"  Insider: {len(sig.insider)} Transaktionen")
            print(f"  8-K: {len(sig.meldungen)} Meldungen")
            if sig.zusammenfassung:
                print(f"  → {sig.zusammenfassung}")
        else:
            print("  Kein Signal / CIK nicht gefunden")
