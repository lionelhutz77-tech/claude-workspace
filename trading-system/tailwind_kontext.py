"""Lernsystem Stufe 3: Tailwind-Signale -> tatsaechliche Kursbewegung -> Ursache.

1. Historie: alle Tages-Reports des Tailwind-Scanners (GitHub) werden eingelesen
   und in data/tailwind_history.db gespeichert (nur neue Tage werden geladen).
2. Folgerendite: fuer jedes Signal die Rendite nach 5 und 10 Handelstagen und
   dieselbe Spanne im S&P 500 (Mehrrendite = Signal minus Markt).
3. Vorhersagekraft: Mehrrendite je Signalstufe (STARK/MODERAT/SCHWACH) und Thema.
   Erst wenn STARK belastbar besser ist als SCHWACH, darf Tailwind Gewicht bekommen.
4. Kontext: fuer grosse Bewegungen (|5T-Rendite| >= 10 %) Nachrichten aus dem
   eigenen Archiv bzw. Google-News-RSS (Datumsfilter) holen und per KI einem festen
   Ereignistyp zuordnen. Daraus entsteht eine Ereignis-Datenbank: welche Art von
   Nachricht bewegt welche Werte wie stark.

Automatisierte Modell-Ausgabe, keine Anlageberatung.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER / "agents"))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

DB_PFAD = HIER / "data" / "tailwind_history.db"
REPO = "lionelhutz77-tech/tailwind-scanner"
BEWEGUNG_SCHWELLE_PCT = 10.0
NEWS_PAUSE_S = 2.0
EREIGNISTYPEN = [
    "Quartalszahlen/Prognose", "Analysten-Einstufung", "Auftrag/Vertrag/Partnerschaft",
    "Produkt/Technologie", "Uebernahme/Fusion", "Regulierung/Politik", "Zinsen/Makro",
    "Sektor-/Peer-Bewegung", "Verwaesserung (Aktienausgabe/Wandelanleihe)",
    "Aktiensplit/Rueckkauf/Dividende", "Indexaufnahme/-entfernung", "Insiderkauf/-verkauf",
    "Recht/Klage", "Kein Nachrichtenausloeser erkennbar",
]


# ---------------------------------------------------------------------------
# Hilfen
# ---------------------------------------------------------------------------

def _http_get(url: str, *, json_antwort: bool = False, timeout: int = 30):
    headers = {"User-Agent": "trading-system-tailwind-kontext"}
    token = os.environ.get("GITHUB_TOKEN")
    if token and "api.github.com" in url:
        headers["Authorization"] = f"Bearer {token}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=timeout) as r:
        daten = r.read().decode("utf-8", errors="replace")
    return json.loads(daten) if json_antwort else daten


def _db() -> sqlite3.Connection:
    DB_PFAD.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PFAD)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS signale (
            datum TEXT NOT NULL, ticker TEXT NOT NULL, thema TEXT, score INTEGER,
            stufe TEXT, kurs REAL,
            rendite_5t REAL, rendite_10t REAL, markt_5t REAL, markt_10t REAL,
            PRIMARY KEY (datum, ticker)
        );
        CREATE TABLE IF NOT EXISTS geladene_reports (datum TEXT PRIMARY KEY);
        CREATE TABLE IF NOT EXISTS bewegungen (
            ticker TEXT NOT NULL, datum TEXT NOT NULL, rendite_5t REAL, markt_5t REAL,
            stufe TEXT, thema TEXT, ereignistyp TEXT, ausloeser TEXT, lehre TEXT,
            quellen INTEGER, quelle_art TEXT, analysiert_am TEXT,
            PRIMARY KEY (ticker, datum)
        );
        CREATE TABLE IF NOT EXISTS firmennamen (ticker TEXT PRIMARY KEY, name TEXT);
    """)
    return conn


# ---------------------------------------------------------------------------
# 1. Historie einlesen
# ---------------------------------------------------------------------------

_ZEILE = re.compile(
    r"<tr>\s*<td><strong>(?P<ticker>[A-Z0-9.\-]+)</strong></td>\s*<td>(?P<thema>[^<]*)</td>\s*"
    r"<td[^>]*>(?P<score>\d+)/100</td>\s*<td><span[^>]*>(?P<stufe>[A-Z]+)</span></td>\s*"
    r"<td>\$(?P<kurs>[\d.,]+)</td>")


def parse_report(html: str) -> list[dict]:
    zeilen = []
    for m in _ZEILE.finditer(html):
        zeilen.append({"ticker": m["ticker"], "thema": m["thema"].strip(), "score": int(m["score"]),
                       "stufe": m["stufe"], "kurs": float(m["kurs"].replace(",", ""))})
    return zeilen


def lade_historie(conn: sqlite3.Connection) -> int:
    """Laedt noch nicht gespeicherte Tages-Reports von GitHub. Gibt Anzahl neuer Tage zurueck."""
    dateien = _http_get(f"https://api.github.com/repos/{REPO}/contents/reports", json_antwort=True)
    bekannt = {r[0] for r in conn.execute("SELECT datum FROM geladene_reports")}
    neu = 0
    for datei in dateien:
        m = re.fullmatch(r"report_(\d{4}-\d{2}-\d{2})\.html", datei.get("name", ""))
        if not m or m[1] in bekannt:
            continue
        zeilen = parse_report(_http_get(datei["download_url"]))
        conn.executemany(
            "INSERT OR IGNORE INTO signale (datum, ticker, thema, score, stufe, kurs) VALUES (?,?,?,?,?,?)",
            [(m[1], z["ticker"], z["thema"], z["score"], z["stufe"], z["kurs"]) for z in zeilen])
        conn.execute("INSERT INTO geladene_reports VALUES (?)", (m[1],))
        neu += 1
    conn.commit()
    return neu


# ---------------------------------------------------------------------------
# 2. Folgerenditen
# ---------------------------------------------------------------------------

def _schlusskurse(ticker: str, ab: str):
    import yfinance as yf

    hist = yf.Ticker(ticker).history(start=ab, auto_adjust=True).dropna(subset=["Close"])
    hist.index = hist.index.tz_localize(None).normalize()
    return hist["Close"]


def _rendite(kurse, datum: str, tage: int) -> float | None:
    ab = kurse[kurse.index >= datum]
    if len(ab) <= tage:
        return None
    return (float(ab.iloc[tage]) / float(ab.iloc[0]) - 1) * 100


def berechne_folgerenditen(conn: sqlite3.Connection) -> int:
    """Fuellt fehlende 5/10-Tage-Renditen (inkl. S&P-500-Vergleich). Gibt Anzahl aktualisierter Zeilen zurueck."""
    offen = conn.execute("SELECT datum, ticker FROM signale WHERE rendite_10t IS NULL").fetchall()
    if not offen:
        return 0
    start = min(d for d, _ in offen)
    markt = _schlusskurse("SPY", start)
    nach_ticker: dict[str, list[str]] = {}
    for datum, ticker in offen:
        nach_ticker.setdefault(ticker, []).append(datum)
    aktualisiert = 0
    for ticker, daten in nach_ticker.items():
        try:
            kurse = _schlusskurse(ticker, min(daten))
        except Exception as exc:  # noqa: BLE001 - einzelner Ticker darf fehlen
            print(f"    {ticker}: Kurse nicht ladbar ({type(exc).__name__})")
            continue
        for datum in daten:
            r5, r10 = _rendite(kurse, datum, 5), _rendite(kurse, datum, 10)
            if r5 is None:
                continue
            conn.execute(
                "UPDATE signale SET rendite_5t=?, rendite_10t=?, markt_5t=?, markt_10t=? WHERE datum=? AND ticker=?",
                (r5, r10, _rendite(markt, datum, 5), _rendite(markt, datum, 10), datum, ticker))
            aktualisiert += 1
    conn.commit()
    return aktualisiert


# ---------------------------------------------------------------------------
# 3. Vorhersagekraft
# ---------------------------------------------------------------------------

_ERSTE_JE_WOCHE = """
    WITH erste AS (
        SELECT * FROM signale s WHERE datum = (
            SELECT MIN(datum) FROM signale s2
            WHERE s2.ticker = s.ticker AND strftime('%Y-%W', s2.datum) = strftime('%Y-%W', s.datum)))"""


def auswertung_je_stufe(conn: sqlite3.Connection) -> list[dict]:
    # Nur das erste Signal je Ticker und Kalenderwoche: dieselbe Aktie steht oft taeglich
    # in der Liste, sonst zaehlt eine einzige Bewegung mehrfach.
    zeilen = conn.execute(f"""
        {_ERSTE_JE_WOCHE}
        SELECT stufe, COUNT(*), AVG(rendite_5t - markt_5t), AVG(rendite_10t - markt_10t),
               AVG(CASE WHEN rendite_10t > markt_10t THEN 1.0 ELSE 0.0 END)
        FROM erste WHERE rendite_10t IS NOT NULL AND markt_10t IS NOT NULL
        GROUP BY stufe ORDER BY stufe""").fetchall()
    return [{"stufe": s, "anzahl": n, "mehr_5t": m5, "mehr_10t": m10, "quote_besser_als_markt": q}
            for s, n, m5, m10, q in zeilen]


def auswertung_je_thema(conn: sqlite3.Connection, mindestens: int = 8) -> list[dict]:
    zeilen = conn.execute(f"""
        {_ERSTE_JE_WOCHE}
        SELECT thema, COUNT(*), AVG(rendite_10t - markt_10t)
        FROM erste WHERE rendite_10t IS NOT NULL AND markt_10t IS NOT NULL AND stufe='STARK'
        GROUP BY thema HAVING COUNT(*) >= ? ORDER BY AVG(rendite_10t - markt_10t) DESC""",
        (mindestens,)).fetchall()
    return [{"thema": t, "anzahl": n, "mehr_10t": m} for t, n, m in zeilen]


# ---------------------------------------------------------------------------
# 4. Kontext grosser Bewegungen
# ---------------------------------------------------------------------------

def _firmenname(conn: sqlite3.Connection, ticker: str) -> str:
    zeile = conn.execute("SELECT name FROM firmennamen WHERE ticker=?", (ticker,)).fetchone()
    if zeile:
        return zeile[0]
    try:
        import yfinance as yf
        name = yf.Ticker(ticker).info.get("shortName") or ticker
    except Exception:  # noqa: BLE001
        name = ticker
    name = re.sub(r",?\s+(Inc\.?|Corporation|Corp\.?|Holdings?|Ltd\.?|plc|N\.V\.|S\.A\.|Co\.?|Class [A-Z])\b.*$", "",
                  name, flags=re.I).strip() or ticker
    conn.execute("INSERT OR REPLACE INTO firmennamen VALUES (?,?)", (ticker, name))
    return name


def _news_archiv(ticker: str, name: str, von: str, bis: str) -> list[str]:
    pfad = HIER / "data" / "news_archive.db"
    if not pfad.exists():
        return []
    # Kuerzel nur ab 3 Zeichen als Suchbegriff ("S" wuerde jedes "U.S." treffen).
    teile = [re.escape(name)] + ([rf"(?<![A-Za-z.]){re.escape(ticker)}(?![A-Za-z])"] if len(ticker) >= 3 else [])
    muster = re.compile("|".join(teile))
    conn = sqlite3.connect(pfad)
    try:
        zeilen = conn.execute("SELECT veroeffentlicht, quelle, titel FROM artikel WHERE veroeffentlicht BETWEEN ? AND ?",
                              (von, bis + "T23:59:59")).fetchall()
    finally:
        conn.close()
    return [f"{z[0][:10]} [{z[1]}] {z[2]}" for z in zeilen if muster.search(z[2])][:20]


def _google_news(name: str, von: str, bis: str) -> list[str] | None:
    """Historische Schlagzeilen ueber Google-News-RSS (Datumsfilter after/before).

    GDELT drosselte im Test dauerhaft (HTTP 429), Google News lieferte fuer denselben
    Zeitraum die passenden Artikel. None = Abfrage fehlgeschlagen (Fall bleibt offen).
    """
    import feedparser

    time.sleep(NEWS_PAUSE_S)
    q = urllib.parse.quote(f'"{name}" after:{von} before:{bis}')
    feed = feedparser.parse(f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en",
                            agent="Mozilla/5.0 (trading-system-tailwind-kontext)")
    status = getattr(feed, "status", None)
    if status is not None and status >= 400 or (not feed.entries and getattr(feed, "bozo", False)):
        print(f"    Google News fuer '{name}' nicht verfuegbar (Status {status})")
        return None
    return [f"{e.get('published', '')[5:16]} {e.get('title', '')}" for e in feed.entries[:25]]


def _klassifiziere(ticker: str, name: str, fall: dict, schlagzeilen: list[str]) -> dict:
    prompt = (
        f"{name} ({ticker}), Thema '{fall['thema']}', Tailwind-Stufe {fall['stufe']} am {fall['datum']}.\n"
        f"Kursbewegung in den 5 Handelstagen danach: {fall['rendite_5t']:+.1f} % (S&P 500: {fall['markt_5t']:+.1f} %).\n"
        "Schlagzeilen aus dem Zeitraum:\n" + ("\n".join(schlagzeilen) or "(keine gefunden)") +
        "\n\nAntworte exakt in diesen Zeilen:\n"
        f"EREIGNISTYP: genau einer aus [{'; '.join(EREIGNISTYPEN)}]\n"
        "AUSLOESER: ein Satz, nur aus den Schlagzeilen belegt (sonst 'nicht belegbar')\n"
        "LEHRE: ein pruefbarer Satz, wie ein Trading-System so etwas frueher erkennen oder vermeiden koennte\n"
        "Nichts erfinden."
    )
    from free_ai_client import generate_text
    text = generate_text("Du ordnest Kursbewegungen nuechtern ihren Nachrichtenausloesern zu.", prompt,
                         task="classify", max_tokens=300)

    def feld(n: str) -> str:
        for z in text.splitlines():
            if z.strip().upper().startswith(n + ":"):
                return z.split(":", 1)[1].strip().strip("[]")
        return ""

    typ = feld("EREIGNISTYP")
    typ = next((t for t in EREIGNISTYPEN if t.lower() in typ.lower()), "Kein Nachrichtenausloeser erkennbar")
    return {"ereignistyp": typ, "ausloeser": feld("AUSLOESER"), "lehre": feld("LEHRE")}


def analysiere_bewegungen(conn: sqlite3.Connection, max_faelle: int = 8) -> int:
    """Ordnet die groessten noch nicht analysierten Bewegungen (erstes Signal je Ticker und Woche) zu."""
    kandidaten = conn.execute("""
        SELECT s.datum, s.ticker, s.thema, s.stufe, s.rendite_5t, s.markt_5t FROM signale s
        LEFT JOIN bewegungen b ON b.ticker = s.ticker AND b.datum = s.datum
        WHERE b.ticker IS NULL AND s.rendite_5t IS NOT NULL AND ABS(s.rendite_5t) >= ?
        ORDER BY ABS(s.rendite_5t) DESC""", (BEWEGUNG_SCHWELLE_PCT,)).fetchall()
    erledigt_wochen = {(t, date.fromisoformat(d).isocalendar()[:2])
                       for t, d in conn.execute("SELECT ticker, datum FROM bewegungen")}
    analysiert = 0
    for datum, ticker, thema, stufe, r5, m5 in kandidaten:
        woche = (ticker, date.fromisoformat(datum).isocalendar()[:2])
        if woche in erledigt_wochen:
            continue
        erledigt_wochen.add(woche)
        name = _firmenname(conn, ticker)
        von = (date.fromisoformat(datum) - timedelta(days=3)).isoformat()
        bis = (date.fromisoformat(datum) + timedelta(days=8)).isoformat()
        schlagzeilen, art = _news_archiv(ticker, name, von, bis), "Archiv"
        if len(schlagzeilen) < 3:
            historisch = _google_news(name, von, bis)
            if historisch is None:
                continue  # ohne Nachrichtenlage kein Urteil speichern; naechster Lauf versucht es erneut
            schlagzeilen, art = schlagzeilen + historisch, "Archiv+GoogleNews"
        fall = {"datum": datum, "thema": thema, "stufe": stufe, "rendite_5t": r5, "markt_5t": m5 or 0.0}
        try:
            k = _klassifiziere(ticker, name, fall, schlagzeilen)
        except Exception as exc:  # noqa: BLE001 - KI-Ausfall sichtbar, Fall bleibt offen
            print(f"    KI-Zuordnung fuer {ticker} fehlgeschlagen: {exc}")
            continue
        conn.execute("INSERT OR REPLACE INTO bewegungen VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                     (ticker, datum, r5, m5, stufe, thema, k["ereignistyp"], k["ausloeser"], k["lehre"],
                      len(schlagzeilen), art, datetime.now().isoformat(timespec="seconds")))
        conn.commit()
        analysiert += 1
        print(f"    {ticker} {datum} {r5:+.1f} % -> {k['ereignistyp']}")
        if analysiert >= max_faelle:
            break
    return analysiert


def auswertung_je_ereignis(conn: sqlite3.Connection) -> list[dict]:
    zeilen = conn.execute("""
        SELECT ereignistyp, COUNT(*), AVG(rendite_5t), SUM(rendite_5t > 0), SUM(rendite_5t < 0)
        FROM bewegungen GROUP BY ereignistyp ORDER BY COUNT(*) DESC""").fetchall()
    return [{"typ": t, "anzahl": n, "schnitt_5t": a, "auf": u, "ab": d} for t, n, a, u, d in zeilen]


# ---------------------------------------------------------------------------
# Gesamtlauf + Berichtsabschnitt
# ---------------------------------------------------------------------------

def aktualisiere(max_faelle: int = 8) -> str:
    """Ein vollstaendiger Lernschritt; gibt einen Markdown-Abschnitt fuer den Wochen-Review zurueck."""
    conn = _db()
    try:
        neue_tage = lade_historie(conn)
        neue_renditen = berechne_folgerenditen(conn)
        neue_faelle = analysiere_bewegungen(conn, max_faelle)
        stufen, themen, ereignisse = auswertung_je_stufe(conn), auswertung_je_thema(conn), auswertung_je_ereignis(conn)
        gesamt = conn.execute("SELECT COUNT(*), COUNT(DISTINCT datum) FROM signale").fetchone()
    finally:
        conn.close()

    def p(x):
        return "n/v" if x is None else f"{x:+.2f} %"

    z = ["## Tailwind: Vorhersagekraft & Ursachen",
         f"Datenbasis: {gesamt[0]} Signale an {gesamt[1]} Scan-Tagen; Statistik nur erstes Signal je Aktie und Woche (neu: {neue_tage} Tage, "
         f"{neue_renditen} Renditen, {neue_faelle} analysierte Bewegungen).", "",
         "| Stufe | Signale | Mehrrendite 5 T | Mehrrendite 10 T | besser als S&P 500 |", "|---|---|---|---|---|"]
    for s in stufen:
        z.append(f"| {s['stufe']} | {s['anzahl']} | {p(s['mehr_5t'])} | {p(s['mehr_10t'])} | "
                 f"{s['quote_besser_als_markt'] * 100:.0f} % |")
    stark = next((s for s in stufen if s["stufe"] == "STARK"), None)
    schwach = next((s for s in stufen if s["stufe"] == "SCHWACH"), None)
    if stark and schwach and stark["mehr_10t"] is not None and schwach["mehr_10t"] is not None:
        diff = stark["mehr_10t"] - schwach["mehr_10t"]
        z.append(f"\nSTARK minus SCHWACH (10 T): {diff:+.2f} Prozentpunkte. "
                 + ("Hinweis auf Vorhersagekraft; noch kein Beweis (Signale ueberlappen zeitlich)." if diff > 0
                    else "Keine Vorhersagekraft erkennbar: Tailwind bekommt weiterhin kein Gewicht."))
    if themen:
        z += ["", "Themen (nur STARK, >= 8 Ticker-Wochen), Mehrrendite 10 T: " +
              ", ".join(f"{t['thema']} {p(t['mehr_10t'])} ({t['anzahl']})" for t in themen[:6])]
    if ereignisse:
        z += ["", "| Ausloeser grosser Bewegungen (>= 10 % in 5 T) | Faelle | Schnitt 5 T | auf/ab |", "|---|---|---|---|"]
        z += [f"| {e['typ']} | {e['anzahl']} | {p(e['schnitt_5t'])} | {e['auf']}/{e['ab']} |" for e in ereignisse]
    return "\n".join(z)


if __name__ == "__main__":
    anzahl = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    print(aktualisiere(anzahl))
