"""Taeglicher Markt-News-Digest (Stufe 1 des Lernsystems).

- Sammelt Schlagzeilen aus freien RSS-Quellen (Boerse + Krypto + Notenbank),
  dazu Fear & Greed und Tagesveraenderung wichtiger Leitwerte.
- Archiviert alle Artikel dauerhaft in data/news_archive.db. Dieses Archiv ist die
  Grundlage fuer Sonntags-Review und Tailwind-Kontext (welche Nachricht vor welcher
  Kursbewegung stand).
- Erstellt ein kurzes Summary ueber das Free-AI-Gateway (Routine-Route) und sendet es
  per Telegram. Faellt die KI aus, wird ein deterministisches Summary gesendet und der
  Fehler sichtbar gemeldet.

Automatisierte Modell-Ausgabe, keine Anlageberatung.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import feedparser

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER / "agents"))

from news_agent import RSS_QUELLEN, erkenne_assets, Nachricht  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

DB_PFAD = HIER / "data" / "news_archive.db"
AUSGABE = HIER / "output"

ZUSATZ_QUELLEN = {
    "Handelsblatt Finanzen": "https://www.handelsblatt.com/contentexport/feed/finanzen",
    "Fed Monetary Policy":   "https://www.federalreserve.gov/feeds/press_monetary.xml",
}
LEITWERTE = {"S&P 500": "^GSPC", "Nasdaq 100": "^NDX", "DAX": "^GDAXI",
             "Bitcoin": "BTC-USD", "Ethereum": "ETH-USD", "Gold": "GC=F",
             "Oel (WTI)": "CL=F", "US-10J-Rendite": "^TNX", "EUR/USD": "EURUSD=X"}
MAX_TITEL_IM_PROMPT = 90


def _verbindung() -> sqlite3.Connection:
    DB_PFAD.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PFAD)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS artikel (
            id              TEXT PRIMARY KEY,
            quelle          TEXT NOT NULL,
            titel           TEXT NOT NULL,
            teaser          TEXT,
            url             TEXT,
            veroeffentlicht TEXT,
            gesammelt_am    TEXT NOT NULL,
            assets          TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_artikel_zeit ON artikel(veroeffentlicht);
        CREATE TABLE IF NOT EXISTS tages_digest (
            datum       TEXT PRIMARY KEY,
            summary     TEXT NOT NULL,
            kennzahlen  TEXT NOT NULL,
            ki_status   TEXT NOT NULL,
            artikel     INTEGER NOT NULL
        );
    """)
    return conn


def _zeitpunkt(eintrag) -> str:
    for feld in ("published", "updated"):
        wert = eintrag.get(feld)
        if not wert:
            continue
        try:
            dt = parsedate_to_datetime(wert)
        except (TypeError, ValueError):
            try:
                dt = datetime.fromisoformat(wert.replace("Z", "+00:00"))
            except ValueError:
                continue
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat(timespec="seconds")
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sammle_artikel(conn: sqlite3.Connection) -> tuple[int, dict[str, str]]:
    """Laedt alle Feeds; gibt neue Artikel und Quellenstatus zurueck."""
    jetzt = datetime.now(timezone.utc).isoformat(timespec="seconds")
    neu, status = 0, {}
    for quelle, url in {**RSS_QUELLEN, **ZUSATZ_QUELLEN}.items():
        feed = feedparser.parse(url, agent="Mozilla/5.0 (trading-news-digest)")
        if not feed.entries:
            status[quelle] = f"keine Eintraege ({type(getattr(feed, 'bozo_exception', None)).__name__})"
            continue
        status[quelle] = f"{len(feed.entries)} Eintraege"
        for e in feed.entries:
            titel = (e.get("title") or "").strip()
            if not titel:
                continue
            link = e.get("link", "")
            teaser = (e.get("summary") or "")[:400]
            art_id = hashlib.sha256((link or titel).encode("utf-8")).hexdigest()[:24]
            assets = erkenne_assets(Nachricht(titel=titel, zusammenfassung=teaser, quelle=quelle,
                                              url=link, datum=datetime.now(timezone.utc)))
            cur = conn.execute(
                "INSERT OR IGNORE INTO artikel VALUES (?,?,?,?,?,?,?,?)",
                (art_id, quelle, titel, teaser, link, _zeitpunkt(e), jetzt, json.dumps(assets)),
            )
            neu += cur.rowcount
    conn.commit()
    return neu, status


def lade_kennzahlen() -> dict:
    """Tagesveraenderung der Leitwerte + Fear & Greed (Fehler werden vermerkt, nicht verschwiegen)."""
    import yfinance as yf

    werte: dict = {}
    for name, sym in LEITWERTE.items():
        try:
            hist = yf.Ticker(sym).history(period="10d").dropna(subset=["Close"])
            letzter, vorher = float(hist["Close"].iloc[-1]), float(hist["Close"].iloc[-2])
            werte[name] = {"kurs": round(letzter, 4), "veraenderung_pct": round((letzter / vorher - 1) * 100, 2)}
        except Exception as exc:  # noqa: BLE001 - Datenquelle darf ausfallen, wird angezeigt
            werte[name] = {"fehler": type(exc).__name__}
    try:
        from fear_greed_agent import hole_fear_greed_aktien, hole_fear_greed_krypto
        werte["Fear&Greed Aktien"] = hole_fear_greed_aktien()
        werte["Fear&Greed Krypto"] = hole_fear_greed_krypto()
    except Exception as exc:  # noqa: BLE001
        werte["Fear&Greed"] = {"fehler": type(exc).__name__}
    return werte


def artikel_seit(conn: sqlite3.Connection, stunden: int = 26) -> list[tuple[str, str, str]]:
    grenze = (datetime.now(timezone.utc) - timedelta(hours=stunden)).isoformat(timespec="seconds")
    return conn.execute(
        "SELECT quelle, titel, assets FROM artikel WHERE veroeffentlicht >= ? ORDER BY veroeffentlicht DESC",
        (grenze,),
    ).fetchall()


def _kennzahlen_text(werte: dict) -> str:
    zeilen = []
    for name, w in werte.items():
        if "veraenderung_pct" in w:
            zeilen.append(f"{name}: {w['veraenderung_pct']:+.2f}%")
        elif "fehler" in w:
            zeilen.append(f"{name}: nicht verfuegbar")
        elif "score" in w:
            zeilen.append(f"{name}: {w['score']} ({w.get('label', '')})")
    return " | ".join(zeilen)


def erstelle_summary(artikel: list[tuple[str, str, str]], werte: dict) -> tuple[str, str]:
    """KI-Summary; bei Ausfall sichtbarer deterministischer Ersatz."""
    titel = [f"- [{q}] {t}" for q, t, _ in artikel[:MAX_TITEL_IM_PROMPT]]
    prompt = (
        f"Kennzahlen seit gestern: {_kennzahlen_text(werte)}\n\n"
        f"Schlagzeilen der letzten 24 Stunden ({len(artikel)} gesamt, Auszug):\n" + "\n".join(titel) +
        "\n\nSchreibe auf Deutsch ein Markt-Summary mit genau diesen Abschnitten:\n"
        "MARKTLAGE: 2 Saetze.\nAKTIEN: bis 4 Stichpunkte (Treiber, betroffene Werte/Sektoren).\n"
        "KRYPTO: bis 4 Stichpunkte.\nMAKRO/POLITIK: bis 3 Stichpunkte.\n"
        "BEOBACHTEN: bis 3 Ereignisse/Termine, die Kurse bewegen koennen.\n"
        "Nur aus den gelieferten Schlagzeilen und Kennzahlen ableiten. Keine Daten, Termine oder "
        "Zahlen erfinden, die nicht in den Schlagzeilen stehen; bei Unklarheit weglassen. "
        "Keine Kauf- oder Verkaufsempfehlung."
    )
    try:
        from free_ai_client import generate_text
        text = generate_text("Du bist ein nuechterner Marktanalyst.", prompt, task="market_synthesis", max_tokens=700)
        return text, "ok"
    except Exception as exc:  # noqa: BLE001
        top = "\n".join(f"- {t}" for _, t, _ in artikel[:12])
        return (f"KI-Summary nicht verfuegbar ({str(exc)[:120]}).\n\nKennzahlen: {_kennzahlen_text(werte)}\n\n"
                f"Wichtigste Schlagzeilen:\n{top}"), f"fehler: {type(exc).__name__}"


def main() -> int:
    heute = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    conn = _verbindung()
    neu, status = sammle_artikel(conn)
    artikel = artikel_seit(conn)
    werte = lade_kennzahlen()
    summary, ki_status = erstelle_summary(artikel, werte)

    conn.execute("INSERT OR REPLACE INTO tages_digest VALUES (?,?,?,?,?)",
                 (heute, summary, json.dumps(werte, ensure_ascii=False), ki_status, len(artikel)))
    conn.commit()
    gesamt = conn.execute("SELECT COUNT(*) FROM artikel").fetchone()[0]
    conn.close()

    AUSGABE.mkdir(exist_ok=True)
    ausfaelle = [q for q, s in status.items() if s.startswith("keine")]
    bericht = (f"# Markt-News {heute}\n\n{summary}\n\n---\nArtikel (24h): {len(artikel)} | neu archiviert: {neu} | "
               f"Archiv gesamt: {gesamt}\nQuellen ohne Daten: {', '.join(ausfaelle) or 'keine'}\n\n"
               "Automatisierte Modell-Ausgabe, keine Anlageberatung.\n")
    (AUSGABE / "news_digest_aktuell.md").write_text(bericht, encoding="utf-8")
    print(bericht)

    try:
        from telegram_agent import sende_nachricht, _html
        sende_nachricht(f"<b>📰 Markt-News {heute}</b>\n\n{_html(summary)[:3500]}\n\n"
                        f"<i>{len(artikel)} Artikel · keine Anlageberatung</i>")
    except Exception as exc:  # noqa: BLE001
        print(f"Telegram nicht gesendet: {exc}")

    # Qualitaets-Gate fuer den Workflow: leeres Archiv oder KI-Ausfall -> sichtbar fehlschlagen.
    if len(artikel) < 20 or ki_status != "ok":
        print(f"QUALITAETSPROBLEM: {len(artikel)} Artikel, KI-Status {ki_status}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
