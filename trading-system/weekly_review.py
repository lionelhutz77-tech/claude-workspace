"""Sonntags-Review (Stufe 2 des Lernsystems).

Jeden Sonntag in der Cloud:
1. Alle Signale der letzten 7 Tage gegen die echte Kursentwicklung halten
   (Kauf-Trefferquote, Verluste, verpasste Chancen).
2. Wochenrendite jedes virtuellen Depots gegen Benchmarks (S&P 500, Bitcoin)
   und gegen die Ziel-Linie "2 % + Gebuehren" legen.
3. Fuer die auffaelligsten Faelle (verpasste Chancen, Verluste) die archivierten
   Nachrichten der Woche heranziehen und per KI-Tiefenroute Ursachen und
   pruefbare Hypothesen ableiten.
4. Hypothesen als "offen" speichern. Sie aendern keine laufende Strategie
   (vorregistrierte Arme bleiben unangetastet), sondern werden in den Folgewochen
   gegen neue Daten geprueft: bestaetigt, verworfen oder weiter offen.

Automatisierte Modell-Ausgabe, keine Anlageberatung.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER / "agents"))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

DATA = HIER / "data"
AUSGABE = HIER / "output"
ZIEL_WOCHE_PCT = 2.0          # Wunschziel des Nutzers (vor Gebuehren), nur als Vergleichslinie
GEBUEHR_JE_TRADE_PCT = 0.1    # konservative Annahme fuer Spread/Gebuehr je Kauf oder Verkauf
CHANCE_SCHWELLE_PCT = 8.0     # Abwarten-Signal, danach >= +8 % in der Woche = verpasste Chance
VERLUST_SCHWELLE_PCT = -5.0   # Kauf-Signal, danach <= -5 % = relevanter Verlust
MAX_KI_FAELLE = 4


# ---------------------------------------------------------------------------
# Daten
# ---------------------------------------------------------------------------

def _kurs_entwicklung(asset: str, asset_typ: str, seit: str) -> float | None:
    """Rendite in % vom Schlusskurs am Signaltag bis heute (None, wenn nicht belegbar)."""
    import yfinance as yf

    symbol = f"{asset}-USD" if asset_typ == "krypto" else asset
    try:
        hist = yf.Ticker(symbol).history(start=seit).dropna(subset=["Close"])
    except Exception:  # noqa: BLE001
        return None
    if len(hist) < 2:
        return None
    return (float(hist["Close"].iloc[-1]) / float(hist["Close"].iloc[0]) - 1) * 100


def signale_der_woche(seit: str) -> list[dict]:
    from learning_agent import _asset_typ

    with sqlite3.connect(DATA / "market_memory.db") as conn:
        conn.row_factory = sqlite3.Row
        spalten = {r[1] for r in conn.execute("PRAGMA table_info(tages_signale)")}
        typ = "asset_typ" if "asset_typ" in spalten else "NULL AS asset_typ"
        zeilen = conn.execute(
            f"SELECT datum, asset, empfehlung, einstieg, gesamt_punkte, {typ} "
            "FROM tages_signale WHERE datum >= ? ORDER BY datum", (seit,)).fetchall()
    # Pro Asset nur das erste Signal der Woche bewerten (sonst zaehlt ein Trend mehrfach).
    erste: dict[str, dict] = {}
    for z in zeilen:
        erste.setdefault(z["asset"], dict(z))
    ergebnis = []
    for s in erste.values():
        s["asset_typ"] = _asset_typ(s["asset"], s["asset_typ"])
        s["rendite_pct"] = _kurs_entwicklung(s["asset"], s["asset_typ"], s["datum"])
        if s["rendite_pct"] is not None and abs(s["rendite_pct"]) <= 100:
            ergebnis.append(s)
    return ergebnis


def _wochen_rendite(verlauf: list[tuple[str, float]], seit: str) -> float | None:
    davor = [w for d, w in verlauf if d <= seit]
    start = davor[-1] if davor else (verlauf[0][1] if verlauf else None)
    if not verlauf or not start:
        return None
    return (verlauf[-1][1] / start - 1) * 100


def depot_renditen(seit: str) -> list[dict]:
    depots: list[dict] = []
    with sqlite3.connect(DATA / "portfolio.db") as conn:
        v = conn.execute("SELECT datum, depotwert FROM depot_verlauf ORDER BY datum").fetchall()
        depots.append({"depot": "Musterdepot (1.000 EUR)", "wert": v[-1][1] if v else None,
                       "woche_pct": _wochen_rendite(v, seit)})
    with sqlite3.connect(DATA / "multi_depot.db") as conn:
        for (strategie,) in conn.execute("SELECT DISTINCT strategie FROM verlauf ORDER BY strategie"):
            v = conn.execute("SELECT datum, depotwert FROM verlauf WHERE strategie=? ORDER BY datum",
                             (strategie,)).fetchall()
            depots.append({"depot": f"Multi {strategie} (1.000 EUR)", "wert": v[-1][1],
                           "woche_pct": _wochen_rendite(v, seit)})
        tabellen = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "snapshots" in tabellen:
            for (strategie,) in conn.execute("SELECT DISTINCT strategy FROM snapshots ORDER BY strategy"):
                v = [(d[:10], w) for d, w in conn.execute(
                    "SELECT observed_at, equity_eur FROM snapshots WHERE strategy=? ORDER BY observed_at",
                    (strategie,))]
                depots.append({"depot": f"Experiment {strategie} (10.000 EUR)", "wert": v[-1][1],
                               "woche_pct": _wochen_rendite(v, seit)})
    return depots


def benchmarks(seit: str) -> dict[str, float | None]:
    return {"S&P 500": _kurs_entwicklung("SPY", "aktie", seit),
            "Bitcoin": _kurs_entwicklung("BTC", "krypto", seit)}


def news_zu(asset: str, seit: str, limit: int = 25) -> list[str]:
    pfad = DATA / "news_archive.db"
    if not pfad.exists():
        return []
    import re

    # Kuerzel nur als eigenes, grossgeschriebenes Wort zaehlen: "ARE" darf nicht jedes "are" treffen.
    muster = re.compile(rf"(?<![A-Za-z]){re.escape(asset)}(?![A-Za-z])")
    conn = sqlite3.connect(pfad)
    try:
        zeilen = conn.execute(
            "SELECT veroeffentlicht, quelle, titel, assets FROM artikel WHERE veroeffentlicht >= ? "
            "ORDER BY veroeffentlicht", (seit,)).fetchall()
    finally:
        conn.close()
    treffer = [z for z in zeilen if asset in json.loads(z[3] or "[]") or muster.search(z[2])]
    return [f"{z[0][:10]} [{z[1]}] {z[2]}" for z in treffer[:limit]]


# ---------------------------------------------------------------------------
# Lernen: Hypothesen ableiten und alte Hypothesen pruefen
# ---------------------------------------------------------------------------

def _lern_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DATA / "learnings.db")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS wochen_reviews (
            datum TEXT PRIMARY KEY, bericht TEXT NOT NULL, kennzahlen TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS review_hypothesen (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            erstellt TEXT NOT NULL,
            asset TEXT, fall TEXT, hypothese TEXT NOT NULL, pruefregel TEXT,
            status TEXT NOT NULL DEFAULT 'offen',
            belege_pro INTEGER NOT NULL DEFAULT 0,
            belege_contra INTEGER NOT NULL DEFAULT 0,
            zuletzt_geprueft TEXT
        );
    """)
    return conn


def analysiere_fall(fall: dict, seit: str) -> dict:
    news = news_zu(fall["asset"], seit)
    prompt = (
        f"Fall: {fall['art']} bei {fall['asset']} ({fall['asset_typ']}).\n"
        f"Signal am {fall['datum']}: {fall['empfehlung']} (Punkte {fall.get('gesamt_punkte')}), "
        f"Kursentwicklung seitdem {fall['rendite_pct']:+.1f} %.\n"
        f"Archivierte Schlagzeilen der Woche zu {fall['asset']}:\n" + ("\n".join(news) or "(keine im Archiv)") +
        "\n\nAntworte exakt in diesen Zeilen:\n"
        "URSACHE: wahrscheinlichster Treiber der Kursbewegung laut Schlagzeilen (oder 'nicht belegbar').\n"
        "SYSTEMFEHLER: warum das Signal danebenlag (Technik, News-Bewertung, fehlender Baustein).\n"
        "HYPOTHESE: eine pruefbare Regel in einem Satz (Wenn ... dann ...).\n"
        "PRUEFREGEL: woran man in den naechsten Wochen objektiv sieht, ob die Hypothese stimmt.\n"
        "Nichts erfinden, was nicht aus Signal, Kursentwicklung oder Schlagzeilen folgt."
    )
    try:
        from free_ai_client import generate_text
        text = generate_text("Du bist ein nuechterner Trading-Reviewer.", prompt,
                             task="review", max_tokens=450)
    except Exception as exc:  # noqa: BLE001
        return {"text": f"KI-Analyse nicht verfuegbar: {exc}", "hypothese": "", "pruefregel": "", "news": len(news)}

    def feld(name: str) -> str:
        for zeile in text.splitlines():
            if zeile.strip().upper().startswith(name + ":"):
                return zeile.split(":", 1)[1].strip()
        return ""

    hypothese = feld("HYPOTHESE")
    # Nur echte Hypothesen speichern, keine zurueckgegebenen Vorlagen-Platzhalter.
    if "..." in hypothese or "…" in hypothese or "prüfbare Regel" in hypothese or "pruefbare Regel" in hypothese:
        hypothese = ""
    return {"text": text, "hypothese": hypothese, "pruefregel": feld("PRUEFREGEL"), "news": len(news)}


# ---------------------------------------------------------------------------
# Bericht
# ---------------------------------------------------------------------------

def _pct(wert: float | None) -> str:
    return "n/v" if wert is None else f"{wert:+.2f} %"


def main() -> int:
    heute = datetime.now(timezone.utc).date()
    seit = (heute - timedelta(days=7)).isoformat()

    signale = signale_der_woche(seit)
    kaeufe = [s for s in signale if s["empfehlung"] == "KAUFEN"]
    treffer = [s for s in kaeufe if s["rendite_pct"] > 0]
    verluste = [s for s in kaeufe if s["rendite_pct"] <= VERLUST_SCHWELLE_PCT]
    verpasst = sorted([s for s in signale if s["empfehlung"] != "KAUFEN"
                       and s["rendite_pct"] >= CHANCE_SCHWELLE_PCT],
                      key=lambda s: -s["rendite_pct"])
    depots = depot_renditen(seit)
    bench = benchmarks(seit)

    faelle = ([{**s, "art": "Verpasste Chance"} for s in verpasst] +
              [{**s, "art": "Verlust nach Kaufsignal"} for s in verluste])[:MAX_KI_FAELLE]
    analysen = [(f, analysiere_fall(f, seit)) for f in faelle]

    conn = _lern_db()
    for f, a in analysen:
        if a["hypothese"]:
            conn.execute("INSERT INTO review_hypothesen (erstellt, asset, fall, hypothese, pruefregel) "
                         "VALUES (?,?,?,?,?)", (heute.isoformat(), f["asset"], f["art"],
                                                a["hypothese"], a["pruefregel"]))
    offene = conn.execute("SELECT COUNT(*) FROM review_hypothesen WHERE status='offen'").fetchone()[0]

    ziel_netto = ZIEL_WOCHE_PCT + 2 * GEBUEHR_JE_TRADE_PCT
    z = [f"# Wochen-Review {heute.isoformat()} (Woche ab {seit})", ""]
    z += ["## Signale der Woche",
          f"- Bewertete Signale: {len(signale)} (je Asset das erste Signal der Woche)",
          f"- Kaufsignale: {len(kaeufe)}, davon im Plus: {len(treffer)}"
          + (f" ({len(treffer) / len(kaeufe) * 100:.0f} %)" if kaeufe else ""),
          f"- Verluste <= {VERLUST_SCHWELLE_PCT:.0f} %: {len(verluste)}",
          f"- Verpasste Chancen (Abwarten, danach >= +{CHANCE_SCHWELLE_PCT:.0f} %): {len(verpasst)}"]
    for s in verpasst[:8]:
        z.append(f"  - {s['asset']} ({s['asset_typ']}): {s['empfehlung']} am {s['datum']}, seitdem {_pct(s['rendite_pct'])}")
    z += ["", "## Depots diese Woche",
          f"Benchmarks: S&P 500 {_pct(bench['S&P 500'])} | Bitcoin {_pct(bench['Bitcoin'])} | "
          f"Ziel-Linie Nutzer {ziel_netto:.1f} % (2 % + Gebuehren)", "",
          "| Depot | Wert | Woche | vs. S&P 500 | Ziel erreicht |", "|---|---|---|---|---|"]
    for d in depots:
        diff = (d["woche_pct"] - bench["S&P 500"]) if d["woche_pct"] is not None and bench["S&P 500"] is not None else None
        ziel = "n/v" if d["woche_pct"] is None else ("ja" if d["woche_pct"] >= ziel_netto else "nein")
        wert = "n/v" if d["wert"] is None else f"{d['wert']:,.2f}"
        z.append(f"| {d['depot']} | {wert} | {_pct(d['woche_pct'])} | {_pct(diff)} | {ziel} |")
    z += ["", "## Ursachen & neue Hypothesen"]
    if not analysen:
        z.append("Keine auffaelligen Faelle diese Woche.")
    for f, a in analysen:
        z += [f"### {f['art']}: {f['asset']} ({_pct(f['rendite_pct'])}, {a['news']} Schlagzeilen im Archiv)",
              a["text"], ""]
    z += [f"Offene Hypothesen gesamt: {offene}. Sie aendern keine laufende Strategie, sondern werden "
          "als eigene Testarme bzw. in den Folge-Reviews gegen neue Daten geprueft.",
          "", "Automatisierte Modell-Ausgabe, keine Anlageberatung. Keine Gewaehr."]
    bericht = "\n".join(z)

    kennzahlen = {"signale": len(signale), "kaeufe": len(kaeufe), "treffer": len(treffer),
                  "verluste": len(verluste), "verpasst": len(verpasst), "benchmarks": bench,
                  "depots": depots}
    conn.execute("INSERT OR REPLACE INTO wochen_reviews VALUES (?,?,?)",
                 (heute.isoformat(), bericht, json.dumps(kennzahlen, ensure_ascii=False)))
    conn.commit()
    conn.close()

    AUSGABE.mkdir(exist_ok=True)
    (AUSGABE / "wochen_review_aktuell.md").write_text(bericht, encoding="utf-8")
    print(bericht)

    try:
        from telegram_agent import sende_nachricht, _html
        kurz = (f"<b>📊 Wochen-Review {heute.isoformat()}</b>\n"
                f"Kaufsignale: {len(kaeufe)}, im Plus: {len(treffer)} · Verluste: {len(verluste)} · "
                f"verpasste Chancen: {len(verpasst)}\n"
                f"S&P 500 {_pct(bench['S&P 500'])} · Bitcoin {_pct(bench['Bitcoin'])}\n\n")
        kurz += "\n".join(f"{_html(d['depot'])}: {_pct(d['woche_pct'])}" for d in depots)
        if verpasst:
            kurz += "\n\nVerpasst: " + ", ".join(f"{s['asset']} {_pct(s['rendite_pct'])}" for s in verpasst[:5])
        kurz += "\n\n<i>Voller Bericht im Repo: trading-system/output/wochen_review_aktuell.md · keine Anlageberatung</i>"
        sende_nachricht(kurz)
    except Exception as exc:  # noqa: BLE001
        print(f"Telegram nicht gesendet: {exc}")

    ki_fehler = sum(1 for _, a in analysen if a["text"].startswith("KI-Analyse nicht verfuegbar"))
    if ki_fehler:
        print(f"QUALITAETSPROBLEM: {ki_fehler} KI-Analysen fehlgeschlagen.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
