"""Lernsystem Stufe 4: regelbasierte Paper-Strategiearme (vorregistriert 27.09.2026).

Unabhaengig von der KI-Kette: die Arme rechnen direkt auf Tageskursen, damit eine
Chance wie BTC am 16.09. nicht daran scheitert, dass die KI-Gesamtwertung "Abwarten"
sagt. Dieselbe Schrittfunktion laeuft im Backtest und live, damit beide identisch
rechnen.

Arme (je 10.000 USD, nur Paper, keine Brokerorders):
  TREND         Long-Ausbruch: Schluss > 20-Tage-Hoch, Schluss > SMA50 > SMA200.
                Risiko 1 % des Depots je Trade, Stop Einstieg - 2 ATR, danach
                Nachziehen auf Hoch - 3 ATR; Ausstieg auch bei Schluss < SMA50.
                Max. 8 Positionen, max. 20 % je Position.
  TREND_SCHUTZ  wie TREND, aber kein Einstieg nach Verwaesserungs-Nachricht
                (Aktienausgabe/ATM/Wandelanleihe, 10 Tage) - Befund Stufe 3: 0/5 aufwaerts.
  SHORT         Short-Ausbruch: Schluss < 20-Tage-Tief, Schluss < SMA50 < SMA200.
                Risiko 0,5 % je Trade, Stop Einstieg + 2 ATR, Nachziehen Tief + 3 ATR,
                Ausstieg auch bei Schluss > SMA50. Max. 4 Positionen, max. 15 %.
  KERN          Langfrist: SPY 40 %, QQQ 25 %, BTC 15 %, GLD 20 %; monatlich
                neu gewichtet, jede Komponente nur ueber SMA200 (sonst Cash).
  SHORT_REGIME  wie SHORT, aber nur wenn SPY bzw. BTC unter SMA200 (nach Backtest ergaenzt).
  MISCH         rechnerisch 50 % KERN + 30 % TREND + 20 % SHORT (kein eigener Handel).

Ausfuehrung: Entscheidung auf Schlusskurs Tag t, Ausfuehrung zum Schlusskurs des
naechsten verfuegbaren Tages (keine Vorausschau), 0,2 % Kosten/Slippage je Seite.
Automatisierte Modell-Ausgabe, keine Anlageberatung.
"""

from __future__ import annotations

import json
import math
import re
import sqlite3
import sys
import time
import urllib.parse
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER / "agents"))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

DB_PFAD = HIER / "data" / "strategie_arme.db"
START_USD = 10_000.0
KOSTEN = 0.002
ARME = ("TREND", "TREND_SCHUTZ", "SHORT", "SHORT_REGIME", "KERN")
MISCH_GEWICHTE = {"KERN": 0.5, "TREND": 0.3, "SHORT": 0.2}
KERN_GEWICHTE = {"SPY": 0.40, "QQQ": 0.25, "BTC-USD": 0.15, "GLD": 0.20}

KRYPTO = ["BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD", "BNB-USD", "ADA-USD", "DOGE-USD",
          "LINK-USD", "AVAX-USD"]
AKTIEN = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AVGO", "JPM", "V",
          "LLY", "UNH", "XOM", "COST", "NFLX", "AMD", "ORCL", "CRM", "ADBE", "PLTR",
          "CRWD", "PANW", "FTNT", "ZS", "NET", "MU", "ANET", "COIN", "LMT", "RTX",
          "CAT", "GE", "BA", "WMT", "HD", "KO", "PEP", "GS", "BAC", "DIS"]
ETFS = ["SPY", "QQQ", "GLD"]
UNIVERSUM = sorted(set(KRYPTO + AKTIEN + ETFS))
HANDELBAR = KRYPTO + AKTIEN  # KERN handelt ETFs/BTC separat

REGELN = {
    "TREND": {"richtung": 1, "risiko": 0.010, "max_pos": 8, "max_anteil": 0.20, "schutz": False},
    "TREND_SCHUTZ": {"richtung": 1, "risiko": 0.010, "max_pos": 8, "max_anteil": 0.20, "schutz": True},
    "SHORT": {"richtung": -1, "risiko": 0.005, "max_pos": 4, "max_anteil": 0.15, "schutz": False},
    # Nach dem Backtest ergaenzt (SHORT verlor in jeder Variante): Shorts nur, wenn der
    # jeweilige Gesamtmarkt (SPY fuer Aktien, BTC fuer Krypto) unter seiner SMA200 liegt.
    # Zaehlt erst mit Live-Beleg, da nachtraeglich formuliert.
    "SHORT_REGIME": {"richtung": -1, "risiko": 0.005, "max_pos": 4, "max_anteil": 0.15, "schutz": False,
                     "regime": True},
}


# ---------------------------------------------------------------------------
# Kennzahlen
# ---------------------------------------------------------------------------

def kennzahlen(df: pd.DataFrame) -> pd.DataFrame:
    """Erwartet Spalten High/Low/Close; ergaenzt SMA, Donchian (ohne heutigen Tag) und ATR."""
    k = pd.DataFrame(index=df.index)
    k["close"] = df["Close"]
    k["sma50"] = df["Close"].rolling(50).mean()
    k["sma200"] = df["Close"].rolling(200).mean()
    k["hoch20"] = df["High"].rolling(20).max().shift(1)
    k["tief20"] = df["Low"].rolling(20).min().shift(1)
    tr = pd.concat([df["High"] - df["Low"], (df["High"] - df["Close"].shift()).abs(),
                    (df["Low"] - df["Close"].shift()).abs()], axis=1).max(axis=1)
    k["atr"] = tr.rolling(14).mean()
    return k


def lade_kurse(symbole: list[str], jahre: float = 4.0) -> dict[str, pd.DataFrame]:
    import yfinance as yf

    daten = yf.download(symbole, period=f"{int(jahre * 365)}d", auto_adjust=True, progress=False,
                        group_by="ticker", threads=True)
    ergebnis = {}
    for s in symbole:
        try:
            df = daten[s][["High", "Low", "Close"]].dropna()
        except KeyError:
            continue
        if len(df) >= 220:
            df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
            ergebnis[s] = kennzahlen(df)
    return ergebnis


# ---------------------------------------------------------------------------
# Zustand und Schrittfunktion (Backtest == Live)
# ---------------------------------------------------------------------------

@dataclass
class Position:
    symbol: str
    menge: float          # > 0 long, < 0 short
    einstieg: float
    stop: float
    extrem: float         # hoechster (long) bzw. tiefster (short) Schluss seit Einstieg
    eroeffnet: str


@dataclass
class Arm:
    name: str
    cash: float = START_USD
    positionen: dict[str, Position] = field(default_factory=dict)
    auftraege: list[dict] = field(default_factory=list)   # Ausfuehrung am naechsten Tag
    trades: list[dict] = field(default_factory=list)
    kern_monat: str = ""

    def wert(self, kurse: dict[str, float]) -> float:
        summe = self.cash
        for p in self.positionen.values():
            summe += p.menge * kurse.get(p.symbol, p.einstieg)
        return summe


def _schliessen(arm: Arm, pos: Position, kurs: float, tag: str, grund: str) -> None:
    if pos.menge > 0:
        erloes = pos.menge * kurs * (1 - KOSTEN)
        pnl = erloes - pos.menge * pos.einstieg
        arm.cash += erloes
    else:
        rueckkauf = -pos.menge * kurs * (1 + KOSTEN)
        pnl = -pos.menge * pos.einstieg - rueckkauf
        arm.cash -= rueckkauf
    arm.trades.append({"symbol": pos.symbol, "richtung": "long" if pos.menge > 0 else "short",
                       "eroeffnet": pos.eroeffnet, "geschlossen": tag, "einstieg": pos.einstieg,
                       "ausstieg": kurs, "pnl": pnl, "grund": grund})
    del arm.positionen[pos.symbol]


def schritt(arm: Arm, tag: pd.Timestamp, daten: dict[str, pd.DataFrame], sperrliste: set[str] | None = None) -> None:
    """Ein Handelstag: offene Auftraege ausfuehren, Stops pruefen, neue Signale vormerken."""
    heute = {s: d.loc[tag] for s, d in daten.items() if tag in d.index}
    kurse = {s: float(z["close"]) for s, z in heute.items()}
    t = tag.date().isoformat()

    # 1. Auftraege von gestern zum heutigen Schluss ausfuehren
    offen = arm.auftraege
    arm.auftraege = []
    for a in offen:
        if a["symbol"] not in kurse:
            arm.auftraege.append(a)  # kein Kurs (z. B. Wochenende bei Aktien) -> naechster Tag
            continue
        kurs = kurse[a["symbol"]]
        if a["art"] == "schliessen" and a["symbol"] in arm.positionen:
            _schliessen(arm, arm.positionen[a["symbol"]], kurs, t, a["grund"])
        elif a["art"] == "oeffnen" and a["symbol"] not in arm.positionen:
            menge = a["menge"]
            if menge > 0:
                kosten = menge * kurs * (1 + KOSTEN)
                if kosten > arm.cash:
                    menge = arm.cash / (kurs * (1 + KOSTEN))
                    kosten = arm.cash
                if menge * kurs < 50:
                    continue
                arm.cash -= kosten
            else:
                arm.cash += -menge * kurs * (1 - KOSTEN)
            atr = float(heute[a["symbol"]]["atr"])
            stop = kurs - 2 * atr if menge > 0 else kurs + 2 * atr
            arm.positionen[a["symbol"]] = Position(a["symbol"], menge, kurs, stop, kurs, t)

    if arm.name == "KERN":
        _kern_schritt(arm, tag, heute, kurse)
        return

    regel = REGELN[arm.name]
    richtung = regel["richtung"]
    # 2. Stops nachziehen und Ausstiege vormerken
    geplant = {a["symbol"] for a in arm.auftraege}
    for pos in list(arm.positionen.values()):
        z = heute.get(pos.symbol)
        if z is None or pos.symbol in geplant:
            continue
        c, atr, sma50 = float(z["close"]), float(z["atr"]), float(z["sma50"])
        if richtung > 0:
            pos.extrem = max(pos.extrem, c)
            pos.stop = max(pos.stop, pos.extrem - 3 * atr)
            raus = c <= pos.stop or c < sma50
        else:
            pos.extrem = min(pos.extrem, c)
            pos.stop = min(pos.stop, pos.extrem + 3 * atr)
            raus = c >= pos.stop or c > sma50
        if raus:
            arm.auftraege.append({"art": "schliessen", "symbol": pos.symbol,
                                  "grund": "Stop" if (c <= pos.stop if richtung > 0 else c >= pos.stop) else "Trendbruch"})

    # 3. Neue Einstiege (staerkster Ausbruch zuerst)
    wert = arm.wert(kurse)
    frei = regel["max_pos"] - len(arm.positionen) - sum(a["art"] == "oeffnen" for a in arm.auftraege)
    kandidaten = []
    baer = {}
    if regel.get("regime"):
        for markt in ("SPY", "BTC-USD"):
            m = heute.get(markt)
            baer[markt] = m is not None and float(m["close"]) < float(m["sma200"])
    for s in HANDELBAR:
        z = heute.get(s)
        if z is None or s in arm.positionen or s in geplant or z.isna().any():
            continue
        if regel.get("regime") and not baer.get("BTC-USD" if s.endswith("-USD") else "SPY"):
            continue
        c = float(z["close"])
        if richtung > 0 and c > z["hoch20"] and c > z["sma50"] > z["sma200"]:
            kandidaten.append((c / z["hoch20"] - 1, s))
        elif richtung < 0 and c < z["tief20"] and c < z["sma50"] < z["sma200"]:
            kandidaten.append((z["tief20"] / c - 1, s))
    for _, s in sorted(kandidaten, reverse=True)[:max(0, frei)]:
        if regel["schutz"] and sperrliste and s in sperrliste:
            continue
        z = heute[s]
        c, atr = float(z["close"]), float(z["atr"])
        if atr <= 0:
            continue
        menge = min(wert * regel["risiko"] / (2 * atr), wert * regel["max_anteil"] / c)
        arm.auftraege.append({"art": "oeffnen", "symbol": s, "menge": richtung * menge})


def _kern_schritt(arm: Arm, tag: pd.Timestamp, heute: dict, kurse: dict[str, float]) -> None:
    monat = tag.strftime("%Y-%m")
    if monat == arm.kern_monat or arm.auftraege:
        return
    if any(s not in heute for s in KERN_GEWICHTE):
        return  # am naechsten gemeinsamen Handelstag neu gewichten
    arm.kern_monat = monat
    wert = arm.wert(kurse)
    for s, gewicht in KERN_GEWICHTE.items():
        z = heute[s]
        ziel = wert * gewicht if float(z["close"]) > float(z["sma200"]) else 0.0
        aktuell = arm.positionen[s].menge * kurse[s] if s in arm.positionen else 0.0
        if abs(ziel - aktuell) < 0.05 * wert * gewicht and not (ziel == 0 and aktuell > 0):
            continue
        if s in arm.positionen:
            arm.auftraege.append({"art": "schliessen", "symbol": s, "grund": "Monatsausgleich"})
        if ziel > 0:
            arm.auftraege.append({"art": "oeffnen", "symbol": s, "menge": ziel / kurse[s]})


# ---------------------------------------------------------------------------
# Backtest
# ---------------------------------------------------------------------------

def backtest(daten: dict[str, pd.DataFrame], ab: str) -> dict:
    arme = {n: Arm(n) for n in ARME if n != "TREND_SCHUTZ"}  # Schutzfilter braucht Live-Nachrichten
    tage = sorted({t for d in daten.values() for t in d.index if t >= pd.Timestamp(ab)})
    verlauf = []
    for tag in tage:
        kurse = {s: float(d.loc[tag, "close"]) for s, d in daten.items() if tag in d.index}
        for arm in arme.values():
            schritt(arm, tag, daten)
        # Kurse fuer Bewertung: letzter bekannter Schluss je Symbol
        letzte = {s: float(d.loc[:tag, "close"].iloc[-1]) for s, d in daten.items() if len(d.loc[:tag])}
        letzte.update(kurse)
        zeile = {"tag": tag, **{n: a.wert(letzte) for n, a in arme.items()}}
        zeile["MISCH"] = sum(zeile[n] * g for n, g in MISCH_GEWICHTE.items())
        verlauf.append(zeile)
    df = pd.DataFrame(verlauf).set_index("tag")
    ergebnis = {}
    for spalte in list(arme) + ["MISCH"]:
        ergebnis[spalte] = _kennwerte(df[spalte], [t for t in arme[spalte].trades] if spalte in arme else [])
    for bench, sym in (("SPY halten", "SPY"), ("BTC halten", "BTC-USD")):
        reihe = daten[sym]["close"].reindex(df.index).ffill().bfill()  # Start am Wochenende: erster Kurs
        ergebnis[bench] = _kennwerte(reihe / reihe.iloc[0] * START_USD, [])
    return ergebnis


def _kennwerte(reihe: pd.Series, trades: list[dict]) -> dict:
    jahre = max((reihe.index[-1] - reihe.index[0]).days / 365.25, 1e-9)
    gesamt = reihe.iloc[-1] / reihe.iloc[0] - 1
    woche = reihe.resample("W").last().pct_change().dropna()
    spitze = reihe.cummax()
    return {"gesamt_pct": gesamt * 100, "pro_jahr_pct": ((1 + gesamt) ** (1 / jahre) - 1) * 100,
            "max_drawdown_pct": ((reihe / spitze - 1).min()) * 100,
            "wochen_ueber_2pct": float((woche >= 0.022).mean() * 100) if len(woche) else 0.0,
            "wochen_im_plus": float((woche > 0).mean() * 100) if len(woche) else 0.0,
            "trades": len(trades),
            "trefferquote_pct": (sum(t["pnl"] > 0 for t in trades) / len(trades) * 100) if trades else None}


# ---------------------------------------------------------------------------
# Live: Zustand in SQLite, Verwaesserungs-Sperre aus Nachrichten
# ---------------------------------------------------------------------------

VERWAESSERUNG = re.compile(r"\b(public offering|stock offering|share offering|at-the-market|ATM program|"
                           r"convertible (senior )?notes|direct offering|registered offering|"
                           r"secondary offering|Kapitalerh[oö]hung|dilut)", re.I)


def verwaesserungs_sperre(symbole: list[str], tage: int = 10) -> set[str]:
    """Aktien mit Verwaesserungs-Schlagzeile in den letzten `tage` Tagen (Archiv + Google News)."""
    import feedparser

    gesperrt = set()
    for s in symbole:
        if s.endswith("-USD") or len(s) < 2:
            continue  # Ein-Buchstaben-Ticker (V) sind als Suchwort nicht eindeutig
        q = urllib.parse.quote(f'"{s}" (offering OR "at-the-market" OR convertible) when:{tage}d')
        feed = feedparser.parse(f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en",
                                agent="Mozilla/5.0 (trading-system-strategie-arme)")
        ticker_wort = re.compile(rf"(?<![A-Za-z]){re.escape(s)}(?![A-Za-z])")
        if any(VERWAESSERUNG.search(e.get("title", "")) and ticker_wort.search(e.get("title", ""))
               for e in feed.entries):
            gesperrt.add(s)
        time.sleep(1.0)
    return gesperrt


def _db() -> sqlite3.Connection:
    DB_PFAD.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PFAD)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS zustand (arm TEXT PRIMARY KEY, json TEXT NOT NULL, stand TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS verlauf (datum TEXT, arm TEXT, wert REAL, PRIMARY KEY (datum, arm));
        CREATE TABLE IF NOT EXISTS trades (arm TEXT, symbol TEXT, richtung TEXT, eroeffnet TEXT,
            geschlossen TEXT, einstieg REAL, ausstieg REAL, pnl REAL, grund TEXT);
        CREATE TABLE IF NOT EXISTS meta (schluessel TEXT PRIMARY KEY, wert TEXT);
    """)
    return conn


def _arm_laden(conn: sqlite3.Connection, name: str) -> tuple[Arm, str | None]:
    zeile = conn.execute("SELECT json, stand FROM zustand WHERE arm=?", (name,)).fetchone()
    if not zeile:
        return Arm(name), None
    d = json.loads(zeile[0])
    arm = Arm(name, d["cash"], {s: Position(**p) for s, p in d["positionen"].items()}, d["auftraege"], [],
              d.get("kern_monat", ""))
    return arm, zeile[1]


def _arm_speichern(conn: sqlite3.Connection, arm: Arm, stand: str) -> None:
    d = {"cash": arm.cash, "positionen": {s: vars(p) for s, p in arm.positionen.items()},
         "auftraege": arm.auftraege, "kern_monat": arm.kern_monat}
    conn.execute("INSERT OR REPLACE INTO zustand VALUES (?,?,?)", (arm.name, json.dumps(d), stand))
    conn.executemany("INSERT INTO trades VALUES (?,?,?,?,?,?,?,?,?)",
                     [(arm.name, t["symbol"], t["richtung"], t["eroeffnet"], t["geschlossen"], t["einstieg"],
                       t["ausstieg"], t["pnl"], t["grund"]) for t in arm.trades])


def live_lauf() -> dict:
    """Verarbeitet alle seit dem letzten Lauf neuen Handelstage (idempotent)."""
    daten = lade_kurse(UNIVERSUM, jahre=1.5)
    # Nur abgeschlossene Tage: die Krypto-Kerze des laufenden UTC-Tages ist beim
    # Morgenlauf erst wenige Stunden alt.
    heute_utc = pd.Timestamp(datetime.now(timezone.utc).date())
    daten = {s: d[d.index < heute_utc] for s, d in daten.items()}
    conn = _db()
    try:
        start = conn.execute("SELECT wert FROM meta WHERE schluessel='start'").fetchone()
        if not start:
            # Erster Lauf: Stichtag = letzter vollstaendiger Tag; kein rueckwirkender Handel.
            letzter = max(d.index.max() for d in daten.values())
            conn.execute("INSERT INTO meta VALUES ('start', ?)", (letzter.date().isoformat(),))
            start_tag = letzter
        else:
            start_tag = pd.Timestamp(start[0])
        sperre = verwaesserungs_sperre(AKTIEN)
        ergebnis = {"gesperrt": sorted(sperre), "neue_tage": 0}
        letzte = {s: float(d["close"].iloc[-1]) for s, d in daten.items()}
        for name in ARME:
            arm, stand = _arm_laden(conn, name)
            tage = sorted({t for d in daten.values() for t in d.index
                           if t >= start_tag and (stand is None or t > pd.Timestamp(stand))})
            for tag in tage:
                schritt(arm, tag, daten, sperre)
                bewertung = {s: float(d.loc[:tag, "close"].iloc[-1]) for s, d in daten.items() if len(d.loc[:tag])}
                conn.execute("INSERT OR REPLACE INTO verlauf VALUES (?,?,?)",
                             (tag.date().isoformat(), name, arm.wert(bewertung)))
            if tage:
                _arm_speichern(conn, arm, tage[-1].date().isoformat())
                ergebnis["neue_tage"] = max(ergebnis["neue_tage"], len(tage))
            ergebnis[name] = {"wert": round(arm.wert(letzte), 2), "positionen": sorted(arm.positionen),
                              "auftraege": [f"{a['art']} {a['symbol']}" for a in arm.auftraege],
                              "geschlossen": [f"{t['symbol']} {t['pnl']:+.0f} USD ({t['grund']})" for t in arm.trades]}
        ergebnis["MISCH"] = {"wert": round(sum(ergebnis[n]["wert"] * g for n, g in MISCH_GEWICHTE.items()), 2)}
        conn.commit()
    finally:
        conn.close()
    return ergebnis


def wochen_abschnitt() -> str:
    """Markdown fuer den Sonntags-Review: Stand, Wochenrendite, Trades der Woche."""
    conn = _db()
    try:
        seit = (date.today() - timedelta(days=7)).isoformat()
        z = ["## Regel-Strategiearme (Stufe 4, je 10.000 USD Paper)",
             "| Arm | Wert | seit Start | Woche | Trades Woche (Gewinn/Verlust) |", "|---|---|---|---|---|"]
        werte = {}
        for name in ARME:
            reihe = conn.execute("SELECT datum, wert FROM verlauf WHERE arm=? ORDER BY datum", (name,)).fetchall()
            if not reihe:
                continue
            vor = [w for d, w in reihe if d <= seit]
            basis = vor[-1] if vor else START_USD
            jetzt = reihe[-1][1]
            werte[name] = (jetzt, basis)
            tw = conn.execute("SELECT pnl FROM trades WHERE arm=? AND geschlossen > ?", (name, seit)).fetchall()
            z.append(f"| {name} | {jetzt:,.0f} | {(jetzt / START_USD - 1) * 100:+.2f} % | "
                     f"{(jetzt / basis - 1) * 100:+.2f} % | {len(tw)} ({sum(p > 0 for (p,) in tw)}/{sum(p <= 0 for (p,) in tw)}) |")
        if all(n in werte for n in MISCH_GEWICHTE):
            jetzt = sum(werte[n][0] * g for n, g in MISCH_GEWICHTE.items())
            basis = sum(werte[n][1] * g for n, g in MISCH_GEWICHTE.items())
            z.append(f"| MISCH | {jetzt:,.0f} | {(jetzt / START_USD - 1) * 100:+.2f} % | {(jetzt / basis - 1) * 100:+.2f} % | – |")
        bt = conn.execute("SELECT wert FROM meta WHERE schluessel='backtest'").fetchone()
        if bt:
            z += ["", "Backtest-Referenz (vor Start festgelegte Regeln): " + bt[0]]
    finally:
        conn.close()
    return "\n".join(z)


def backtest_speichern(ab: str = "2021-06-01") -> dict:
    ergebnis = backtest(lade_kurse(UNIVERSUM, jahre=6.5), ab)
    kurz = "; ".join(f"{k} {v['pro_jahr_pct']:+.1f} %/J, MaxDD {v['max_drawdown_pct']:.0f} %"
                     for k, v in ergebnis.items())
    conn = _db()
    try:
        conn.execute("INSERT OR REPLACE INTO meta VALUES ('backtest', ?)", (f"ab {ab}: {kurz}",))
        conn.commit()
    finally:
        conn.close()
    return ergebnis


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "backtest":
        for name, k in backtest_speichern(sys.argv[2] if len(sys.argv) > 2 else "2021-06-01").items():
            tq = "n/v" if k["trefferquote_pct"] is None else f"{k['trefferquote_pct']:.0f} %"
            print(f"{name:12} gesamt {k['gesamt_pct']:+8.1f} % | p.a. {k['pro_jahr_pct']:+6.1f} % | "
                  f"MaxDD {k['max_drawdown_pct']:6.1f} % | Wochen im Plus {k['wochen_im_plus']:4.0f} % | "
                  f"Wochen >= 2,2 % {k['wochen_ueber_2pct']:4.0f} % | Trades {k['trades']:4d} | Treffer {tq}")
    else:
        ergebnis = live_lauf()
        print(json.dumps(ergebnis, ensure_ascii=False, indent=2))
        zeilen = []
        for name in ARME:
            e = ergebnis[name]
            neu = [a for a in e["auftraege"]] + [f"geschlossen {g}" for g in e["geschlossen"]]
            if neu:
                zeilen.append(f"<b>{name}</b> ({e['wert']:,.0f} USD): " + ", ".join(neu))
        if zeilen:
            try:
                from telegram_agent import sende_nachricht
                text = "\n".join(["<b>⚙️ Regel-Strategien (Paper)</b>", *zeilen,
                                  f"MISCH: {ergebnis['MISCH']['wert']:,.0f} USD",
                                  "<i>Orders werden zum naechsten Schlusskurs ausgefuehrt · keine Anlageberatung</i>"])
                sende_nachricht(text)
            except Exception as exc:  # noqa: BLE001
                print(f"Telegram nicht gesendet: {exc}")
