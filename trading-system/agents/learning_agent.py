"""
Lern-Agent — Retrospektive Fehleranalyse
Vergleicht vergangene Empfehlungen mit tatsaechlichen Kursen,
erkennt grosse Abweichungen und analysiert die Ursachen mit KI.

Ablauf:
  1. Alle vergangenen Signale aus der Datenbank laden
  2. Tatsaechliche Kursentwicklung ermitteln
  3. Abweichung berechnen (Signal vs. Realitaet)
  4. Bei Abweichung > Schwellenwert: KI-Analyse der Ursache
  5. Erkenntnis speichern → System lernt fuer die Zukunft
  6. Dashboard-Sektion generieren

Schwellenwert: -8% (Empfehlung KAUFEN, Kurs faellt mehr als 8%)
"""

import sys
import os
import sqlite3
import time
from datetime import datetime, timedelta
from dataclasses import dataclass, field

import yfinance as yf
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_groq   = Groq(api_key=os.environ.get("GROQ_API_KEY"))
MODEL   = "llama-3.3-70b-versatile"
DB_PFAD = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "market_memory.db")
LERN_DB = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "learnings.db")

ABWEICHUNG_SCHWELLE  = -8.0   # % — bei diesem Verlust wird analysiert
CHANCE_SCHWELLE      = +10.0  # % — verpasste Chance wenn ABWARTEN und Kurs steigt
MAX_ANALYSEN_PRO_TAG = 3      # KI-Analysen pro Lauf (Groq-Limit schonen)


# ---------------------------------------------------------------------------
# Datenbank fuer Erkenntnisse
# ---------------------------------------------------------------------------

def initialisiere_lern_db():
    os.makedirs(os.path.dirname(LERN_DB), exist_ok=True)
    with sqlite3.connect(LERN_DB) as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS fehleranalysen (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            datum_signal    TEXT,
            datum_analyse   TEXT,
            asset           TEXT,
            empfehlung      TEXT,
            einstieg        REAL,
            kurs_5d         REAL,
            kurs_10d        REAL,
            rendite_5d      REAL,
            rendite_10d     REAL,
            fehler_typ      TEXT,
            ki_analyse      TEXT,
            lehre           TEXT,
            erstellt_am     TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS system_lehren (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            kategorie       TEXT,
            lehre           TEXT,
            beispiel        TEXT,
            haeufigkeit     INTEGER DEFAULT 1,
            wirksam         INTEGER DEFAULT 1,
            fehler_nach_lehr INTEGER DEFAULT 0,
            ersetzt_durch   TEXT DEFAULT '',
            erstellt_am     TEXT DEFAULT CURRENT_TIMESTAMP,
            zuletzt         TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS lern_tagesberichte (
            datum       TEXT PRIMARY KEY,
            bericht     TEXT,
            trefferquote REAL,
            neue_lehren  INTEGER DEFAULT 0,
            angepasste   INTEGER DEFAULT 0
        );
        """)
        # Neue Spalten nachrüsten falls DB schon existiert (ohne Fehler)
        for col, typ in [("wirksam", "INTEGER DEFAULT 1"),
                         ("fehler_nach_lehr", "INTEGER DEFAULT 0"),
                         ("ersetzt_durch", "TEXT DEFAULT ''")]:
            try:
                conn.execute(f"ALTER TABLE system_lehren ADD COLUMN {col} {typ}")
            except Exception:
                pass


def speichere_fehleranalyse(analyse: dict):
    initialisiere_lern_db()
    with sqlite3.connect(LERN_DB) as conn:
        conn.execute("""
        INSERT INTO fehleranalysen
            (datum_signal, datum_analyse, asset, empfehlung, einstieg,
             kurs_5d, kurs_10d, rendite_5d, rendite_10d, fehler_typ, ki_analyse, lehre)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            analyse["datum_signal"], datetime.now().strftime("%Y-%m-%d"),
            analyse["asset"], analyse["empfehlung"],
            analyse["einstieg"], analyse.get("kurs_5d", 0), analyse.get("kurs_10d", 0),
            analyse.get("rendite_5d", 0), analyse.get("rendite_10d", 0),
            analyse.get("fehler_typ", ""), analyse.get("ki_analyse", ""),
            analyse.get("lehre", ""),
        ))


def speichere_lehre(kategorie: str, lehre: str, beispiel: str):
    """Speichert eine gewonnene Erkenntnis. Erhoeht Haeufigkeit wenn schon bekannt."""
    initialisiere_lern_db()
    with sqlite3.connect(LERN_DB) as conn:
        vorhanden = conn.execute(
            "SELECT id FROM system_lehren WHERE kategorie=? AND lehre=?",
            (kategorie, lehre[:200])
        ).fetchone()
        if vorhanden:
            conn.execute(
                "UPDATE system_lehren SET haeufigkeit=haeufigkeit+1, zuletzt=? WHERE id=?",
                (datetime.now().strftime("%Y-%m-%d"), vorhanden[0])
            )
        else:
            conn.execute(
                "INSERT INTO system_lehren (kategorie, lehre, beispiel) VALUES (?, ?, ?)",
                (kategorie, lehre[:200], beispiel[:300])
            )


def hole_top_lehren(limit: int = 10) -> list[dict]:
    """Gibt die haeufigsten und wichtigsten Erkenntnisse zurueck."""
    initialisiere_lern_db()
    with sqlite3.connect(LERN_DB) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT kategorie, lehre, beispiel, haeufigkeit, zuletzt
            FROM system_lehren
            ORDER BY haeufigkeit DESC, zuletzt DESC
            LIMIT ?
        """, (limit,)).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Kursvergleich
# ---------------------------------------------------------------------------

@dataclass
class AbweichungsAnalyse:
    asset: str
    datum_signal: str
    empfehlung: str
    einstieg: float
    kurs_5d: float = 0.0
    kurs_10d: float = 0.0
    rendite_5d: float = 0.0
    rendite_10d: float = 0.0
    ist_fehler: bool = False
    fehler_typ: str = ""
    ki_analyse: str = ""
    lehre: str = ""


def hole_tatsaechliche_kurse(asset: str, datum_signal: str, asset_typ: str = "aktie") -> dict:
    """Holt die tatsaechlichen Kurse 5 und 10 Tage nach dem Signal."""
    try:
        signal_datum = datetime.strptime(datum_signal, "%Y-%m-%d")
        heute        = datetime.now()
        tage_seit    = (heute - signal_datum).days

        if tage_seit < 3:
            return {}

        yf_sym = f"{asset}-USD" if asset_typ == "krypto" else asset
        ticker = yf.Ticker(yf_sym)
        hist   = ticker.history(
            start=signal_datum.strftime("%Y-%m-%d"),
            end=heute.strftime("%Y-%m-%d")
        )

        if hist.empty:
            return {}

        preise = hist["Close"].values

        def preis_nach_n(n):
            idx = min(n, len(preise) - 1)
            return float(preise[idx])

        return {
            "kurs_5d":  preis_nach_n(5)  if tage_seit >= 5  else None,
            "kurs_10d": preis_nach_n(10) if tage_seit >= 10 else None,
        }

    except Exception:
        return {}


def analysiere_abweichungen() -> list[AbweichungsAnalyse]:
    """
    Laedt alle vergangenen Signale (KAUFEN + ABWARTEN + VERKAUFEN) und vergleicht
    mit tatsaechlicher Entwicklung. Erkennt:
      - KAUFEN-Fehler: Kurs faellt >8% nach KAUFEN-Empfehlung
      - Verpasste Chancen: ABWARTEN/VERKAUFEN, aber Kurs steigt >10%
      - Korrekte Calls: KAUFEN mit positivem Ergebnis (Verstaerkung)
    """
    if not os.path.exists(DB_PFAD):
        return []

    grenze = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    with sqlite3.connect(DB_PFAD) as conn:
        conn.row_factory = sqlite3.Row
        signale = conn.execute("""
            SELECT ts.datum, ts.asset, ts.empfehlung, ts.einstieg
            FROM tages_signale ts
            WHERE ts.datum >= ?
            ORDER BY ts.datum DESC
        """, (grenze,)).fetchall()

    ergebnisse = []
    for sig in signale:
        if not sig["einstieg"] or sig["einstieg"] == 0:
            continue

        kurse = hole_tatsaechliche_kurse(
            sig["asset"], sig["datum"],
            asset_typ="krypto" if sig["asset"] in ["BTC","ETH","SOL","XRP","BNB"] else "aktie"
        )

        if not kurse:
            continue

        analyse = AbweichungsAnalyse(
            asset=sig["asset"],
            datum_signal=sig["datum"],
            empfehlung=sig["empfehlung"],
            einstieg=float(sig["einstieg"]),
        )

        if kurse.get("kurs_5d"):
            analyse.kurs_5d   = kurse["kurs_5d"]
            analyse.rendite_5d = (kurse["kurs_5d"] / sig["einstieg"] - 1) * 100

        if kurse.get("kurs_10d"):
            analyse.kurs_10d   = kurse["kurs_10d"]
            analyse.rendite_10d = (kurse["kurs_10d"] / sig["einstieg"] - 1) * 100

        # Rendite auswerten
        rendite_best = max(
            analyse.rendite_5d  if analyse.kurs_5d  else 0,
            analyse.rendite_10d if analyse.kurs_10d else 0,
        )
        rendite_worst = min(
            analyse.rendite_5d  if analyse.kurs_5d  else 0,
            analyse.rendite_10d if analyse.kurs_10d else 0,
        )

        empf = sig["empfehlung"]

        if empf == "KAUFEN":
            if rendite_worst < ABWEICHUNG_SCHWELLE:
                analyse.ist_fehler = True
                if rendite_worst < -20:
                    analyse.fehler_typ = "MASSIVER_VERLUST"
                elif rendite_worst < -12:
                    analyse.fehler_typ = "GROSSER_VERLUST"
                else:
                    analyse.fehler_typ = "SIGNIFIKANTER_VERLUST"
            elif rendite_best > 0:
                # Korrekter Call — positiv verstaerken
                analyse.fehler_typ = "KORREKT_KAUFEN"

        elif empf in ("ABWARTEN", "HALTEN / ABWARTEN", "VERKAUFEN"):
            if rendite_best > CHANCE_SCHWELLE:
                # Verpasste Chance: Wir haben ABWARTEN gesagt, Kurs stieg stark
                analyse.ist_fehler = True
                analyse.fehler_typ = "VERPASSTE_CHANCE"

        ergebnisse.append(analyse)
        time.sleep(0.2)

    return ergebnisse


# ---------------------------------------------------------------------------
# KI-Fehleranalyse
# ---------------------------------------------------------------------------

def ki_analysiere_fehler(analyse: AbweichungsAnalyse) -> tuple[str, str]:
    """
    Laesst die KI analysieren warum ein Signal fehlgeschlagen ist oder eine Chance verpasst wurde.
    Gibt (analyse_text, lehre) zurueck.
    """
    if analyse.fehler_typ == "VERPASSTE_CHANCE":
        prompt = f"""Du bist ein erfahrener Marktanalyst. Analysiere diese verpasste Chance:

Asset: {analyse.asset}
Signal-Datum: {analyse.datum_signal}
Unsere Empfehlung: ABWARTEN/VERKAUFEN bei ${analyse.einstieg:,.2f}
Tatsaechliche Entwicklung:
  Nach 5 Tagen:  ${analyse.kurs_5d:,.2f}  ({analyse.rendite_5d:+.1f}%)
  Nach 10 Tagen: ${analyse.kurs_10d:,.2f} ({analyse.rendite_10d:+.1f}%)

Beantworte kurz und praezise:

URSACHE: [Warum haben wir den Anstieg verpasst? Was hat uns zur falschen Empfehlung gefuehrt?]

WARNSIGNALE: [Welche Signale haetten auf den Anstieg hingedeutet?]

LEHRE: [Eine konkrete Regel damit wir solche Chancen in Zukunft nicht mehr verpassen - max. 1 Satz]"""
    else:
        prompt = f"""Du bist ein erfahrener Risikoanalyst. Analysiere diesen fehlgeschlagenen Trade:

Asset: {analyse.asset}
Signal-Datum: {analyse.datum_signal}
Empfehlung: KAUFEN bei ${analyse.einstieg:,.2f}
Tatsaechliche Entwicklung:
  Nach 5 Tagen:  ${analyse.kurs_5d:,.2f}  ({analyse.rendite_5d:+.1f}%)
  Nach 10 Tagen: ${analyse.kurs_10d:,.2f} ({analyse.rendite_10d:+.1f}%)
Fehler-Typ: {analyse.fehler_typ}

Beantworte kurz und praezise:

URSACHE: [Was hat diesen Einbruch wahrscheinlich ausgeloest? Makro, Sentiment, Technisch?]

WARNSIGNALE: [Welche Signale haette man vorher sehen koennen?]

LEHRE: [Eine konkrete Regel die das System in Zukunft beachten soll - max. 1 Satz]"""

    try:
        for versuch in range(3):
            try:
                resp = _groq.chat.completions.create(
                    model=MODEL,
                    messages=[
                        {"role": "system", "content": "Du bist ein praeziser Markt-Risikoanalyst. Antworte strukturiert und kurz."},
                        {"role": "user",   "content": prompt}
                    ],
                    max_tokens=300,
                    temperature=0.2,
                )
                text = resp.choices[0].message.content.strip()

                # Lehre extrahieren
                lehre = ""
                for zeile in text.splitlines():
                    if zeile.strip().upper().startswith("LEHRE:"):
                        lehre = zeile.split(":", 1)[-1].strip()
                        break

                return text, lehre
            except Exception as e:
                if "429" in str(e) and versuch < 2:
                    time.sleep(30 * (versuch + 1))
                else:
                    raise
    except Exception as e:
        return f"KI-Analyse nicht verfuegbar: {e}", ""


# ---------------------------------------------------------------------------
# Haupt-Funktion
# ---------------------------------------------------------------------------

def fuehre_lernzyklus_durch() -> dict:
    """
    Kompletter Lernzyklus:
    1. Abweichungen analysieren
    2. Fehler mit KI untersuchen
    3. Erkenntnisse speichern
    4. Bericht erstellen
    """
    initialisiere_lern_db()

    print("  Lade vergangene Signale und vergleiche mit Kursen...")
    alle      = analysiere_abweichungen()
    fehler    = [a for a in alle if a.ist_fehler and a.fehler_typ != "KORREKT_KAUFEN"]
    verpasst  = [a for a in fehler if a.fehler_typ == "VERPASSTE_CHANCE"]
    verluste  = [a for a in fehler if a.fehler_typ != "VERPASSTE_CHANCE"]
    korrekte  = [a for a in alle if a.fehler_typ == "KORREKT_KAUFEN"]

    print(f"  {len(alle)} Signale geprueft — "
          f"{len(verluste)} Verlust-Fehler, "
          f"{len(verpasst)} verpasste Chancen, "
          f"{len(korrekte)} korrekte Calls")

    # KI-Analyse: erst die groessten Verluste, dann verpasste Chancen
    # Verluste nach Groesse sortieren, Chancen nach Groesse der verpassten Rendite
    kandidaten = (
        sorted(verluste,  key=lambda x: x.rendite_10d)[:2] +
        sorted(verpasst,  key=lambda x: -(x.rendite_10d or x.rendite_5d))[:1]
    )

    analysiert = 0
    for analyse in kandidaten[:MAX_ANALYSEN_PRO_TAG]:
        print(f"    Analysiere Fehler: {analyse.asset} ({analyse.rendite_5d:+.1f}% in 5d)...")
        ki_text, lehre = ki_analysiere_fehler(analyse)
        analyse.ki_analyse = ki_text
        analyse.lehre      = lehre

        # Speichern
        speichere_fehleranalyse({
            "datum_signal": analyse.datum_signal,
            "asset":        analyse.asset,
            "empfehlung":   analyse.empfehlung,
            "einstieg":     analyse.einstieg,
            "kurs_5d":      analyse.kurs_5d,
            "kurs_10d":     analyse.kurs_10d,
            "rendite_5d":   round(analyse.rendite_5d, 2),
            "rendite_10d":  round(analyse.rendite_10d, 2),
            "fehler_typ":   analyse.fehler_typ,
            "ki_analyse":   ki_text,
            "lehre":        lehre,
        })

        if lehre:
            speichere_lehre(
                kategorie=analyse.asset,
                lehre=lehre,
                beispiel=f"{analyse.datum_signal}: KAUFEN bei ${analyse.einstieg:,.0f} → {analyse.rendite_10d:+.1f}% in 10d"
            )

        analysiert += 1
        time.sleep(1)

    # Top-Lehren laden
    top_lehren = hole_top_lehren(8)

    # Lektions-Validierung: Welche Regeln haben nicht geholfen?
    print("  Prüfe Wirksamkeit aktiver Lektionen...")
    probleme  = validiere_lehren()
    angepasst = 0
    if probleme:
        ineffektiv = [p for p in probleme if p["status"] == "INEFFEKTIV"]
        if ineffektiv:
            print(f"  {len(ineffektiv)} ineffektive Lektion(en) — generiere staerkere Regeln...")
            angepasst = aktualisiere_ineffektive_lehren(ineffektiv)
            if angepasst:
                print(f"  {angepasst} Regel(n) ersetzt.")

    lern_ergebnis = {
        "signale_gesamt":    len(alle),
        "fehler":            len(verluste),
        "verpasste_chancen": len(verpasst),
        "korrekte":          len(korrekte),
        "trefferquote":      len(korrekte) / len(alle) * 100 if alle else 0,
        "analysen":          [a for a in kandidaten if a.ki_analyse],
        "alle_abweichungen": alle,
        "top_lehren":        top_lehren,
        "probleme":          probleme,
        "angepasst":         angepasst,
    }

    # Taeglich Lean-Bericht erstellen und speichern
    bericht_text = erstelle_tages_lern_report(lern_ergebnis, probleme, angepasst)
    speichere_tages_lern_report(bericht_text, lern_ergebnis, angepasst)

    return lern_ergebnis


def hole_aktive_lehren_als_text(max_lehren: int = 5) -> str:
    """
    Gibt die wichtigsten Erkenntnisse als formatierten Text zurueck —
    direkt einbettbar in KI-Prompts (Revision-Agent, Portfolio-Manager).
    Gibt leeren String zurueck wenn keine Erkenntnisse vorhanden.
    """
    lehren = hole_top_lehren(max_lehren)
    if not lehren:
        return ""

    zeilen = ["ERKENNTNISSE AUS VERGANGENEN FEHLERN (beachten!):"]
    for i, l in enumerate(lehren, 1):
        haeuf = f"[{l['haeufigkeit']}x bestaetigt]" if l["haeufigkeit"] > 1 else ""
        zeilen.append(f"  {i}. {l['lehre']} {haeuf}")
    return "\n".join(zeilen)


# ---------------------------------------------------------------------------
# Lektions-Validierung: Wirken unsere Regeln wirklich?
# ---------------------------------------------------------------------------

def validiere_lehren() -> list[dict]:
    """
    Prueft welche gespeicherten Lektionen NICHT gewirkt haben:
    Eine Lektion gilt als ineffektiv wenn haeufigkeit >= 3 (gleicher Fehler
    trat nach dem Lernen mindestens 2x erneut auf).
    """
    initialisiere_lern_db()
    with sqlite3.connect(LERN_DB) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT id, kategorie, lehre, beispiel, haeufigkeit, erstellt_am
            FROM system_lehren
            WHERE wirksam = 1
            ORDER BY haeufigkeit DESC
        """).fetchall()

    probleme = []
    for r in rows:
        if r["haeufigkeit"] >= 3:
            status = "INEFFEKTIV"
        elif r["haeufigkeit"] == 2:
            status = "TEILWEISE"
        else:
            continue
        probleme.append({
            "id":          r["id"],
            "kategorie":   r["kategorie"],
            "lehre":       r["lehre"],
            "beispiel":    r["beispiel"],
            "haeufigkeit": r["haeufigkeit"],
            "erstellt_am": r["erstellt_am"],
            "status":      status,
        })
    return probleme


def ki_meta_lehre(problem: dict) -> str:
    """
    Generiert eine staerkere Ersatz-Lektion fuer eine ineffektive Regel.
    Gibt die neue Formulierung zurueck.
    """
    prompt = f"""Eine Trading-Regel wurde {problem['haeufigkeit']} Mal gebrochen:

Regel: "{problem['lehre']}"
Kategorie: {problem['kategorie']}
Beispiel-Fehler: {problem['beispiel']}
Gespeichert seit: {problem['erstellt_am']}

Diese Regel war NICHT wirksam genug — derselbe Fehler-Typ trat immer wieder auf.

Generiere eine STAERKERE, PRAEZISERE Version dieser Regel:
- Konkreter: messbare Bedingungen statt vage Aussagen
- Absolut: keine "manchmal" oder "meistens" — klare Wenn-Dann-Regel
- Praegnant: max. 1 Satz

NEUE_LEHRE: [Neue, haertere Formulierung]"""

    try:
        for versuch in range(3):
            try:
                resp = _groq.chat.completions.create(
                    model=MODEL,
                    messages=[
                        {"role": "system", "content": "Du bist ein Risikomanager. Formuliere Trading-Regeln praezise und absolut."},
                        {"role": "user",   "content": prompt},
                    ],
                    max_tokens=150,
                    temperature=0.2,
                )
                text = resp.choices[0].message.content.strip()
                for zeile in text.splitlines():
                    if zeile.strip().upper().startswith("NEUE_LEHRE:"):
                        return zeile.split(":", 1)[-1].strip()
                return text.splitlines()[0][:200]
            except Exception as e:
                if "429" in str(e) and versuch < 2:
                    time.sleep(30 * (versuch + 1))
                else:
                    return ""
    except Exception:
        return ""


def aktualisiere_ineffektive_lehren(probleme: list[dict]) -> int:
    """
    Markiert ineffektive Lektionen als unwirksam und ersetzt sie durch
    staerkere Formulierungen. Gibt Anzahl angepasster Lektionen zurueck.
    """
    angepasst = 0
    for p in [x for x in probleme if x["status"] == "INEFFEKTIV"]:
        neue_lehre = ki_meta_lehre(p)
        if not neue_lehre:
            continue

        with sqlite3.connect(LERN_DB) as conn:
            # Alte Lektion als unwirksam markieren
            conn.execute(
                "UPDATE system_lehren SET wirksam=0, ersetzt_durch=? WHERE id=?",
                (neue_lehre[:200], p["id"])
            )
            # Neue, staerkere Lektion einfuegen
            conn.execute("""
                INSERT INTO system_lehren
                    (kategorie, lehre, beispiel, haeufigkeit, wirksam)
                VALUES (?, ?, ?, 1, 1)
            """, (
                p["kategorie"],
                neue_lehre[:200],
                f"Ersetzt ineffektive Regel vom {p['erstellt_am']}: {p['lehre'][:100]}",
            ))
        angepasst += 1
        time.sleep(1)

    return angepasst


# ---------------------------------------------------------------------------
# Taeglich Lean-Bericht
# ---------------------------------------------------------------------------

def erstelle_tages_lern_report(lern_ergebnis: dict, probleme: list[dict], angepasst: int) -> str:
    """
    Erstellt den vollstaendigen Lean-Bericht fuer den Tag.
    Wird gespeichert und im Dashboard angezeigt.
    """
    heute = datetime.now().strftime("%d.%m.%Y  %H:%M Uhr")
    sep   = "=" * 62
    sub   = "-" * 55
    zeilen = []

    zeilen.append(sep)
    zeilen.append(f"  LEAN LERN-REPORT  —  {heute}")
    zeilen.append(sep)

    # --- 1. Heutiger Abgleich ---
    zeilen.append(f"\n  1. PROGNOSE vs. REALITAET (letzte 30 Tage)")
    zeilen.append(f"  {sub}")
    zeilen.append(f"  Analysierte Signale   : {lern_ergebnis['signale_gesamt']}")
    zeilen.append(f"  Korrekte Calls        : {lern_ergebnis['korrekte']}  ({lern_ergebnis['trefferquote']:.1f}%)")
    zeilen.append(f"  Verlust-Fehler        : {lern_ergebnis['fehler']}")
    zeilen.append(f"  Verpasste Chancen     : {lern_ergebnis.get('verpasste_chancen', 0)}")

    if lern_ergebnis.get("analysen"):
        zeilen.append(f"\n  Groesste Abweichungen heute analysiert:")
        for a in lern_ergebnis["analysen"]:
            typ_label = "VERPASSTE CHANCE" if a.fehler_typ == "VERPASSTE_CHANCE" else "FEHLER"
            zeilen.append(f"\n    [{typ_label}] {a.asset}  |  Signal: {a.datum_signal}")
            zeilen.append(f"    Preis damals : ${a.einstieg:,.2f}")
            zeilen.append(f"    5d spaeter   : ${a.kurs_5d:,.2f}  ({a.rendite_5d:+.1f}%)")
            if a.kurs_10d:
                zeilen.append(f"    10d spaeter  : ${a.kurs_10d:,.2f}  ({a.rendite_10d:+.1f}%)")
            if a.ki_analyse:
                for zeile in a.ki_analyse.splitlines():
                    if zeile.strip():
                        zeilen.append(f"    {zeile}")

    # --- 2. Aktive Lektionen ---
    top_lehren   = hole_top_lehren(10)
    problem_ids  = {p["id"] for p in probleme}
    zeilen.append(f"\n  2. AKTIVE LEKTIONEN (heute in KI-Analyse eingesetzt)")
    zeilen.append(f"  {sub}")
    if top_lehren:
        for l in top_lehren:
            wirkung = "⚠ TEILWEISE" if l.get("id") in problem_ids else "✓ WIRKSAM"
            bestaet = f"  [{l['haeufigkeit']}x bestaetigt]"
            zeilen.append(f"  {wirkung}{bestaet}  {l['lehre']}")
            if l.get("beispiel"):
                zeilen.append(f"    Beispiel: {l['beispiel'][:90]}")
    else:
        zeilen.append("  Noch keine Lektionen (System sammelt Daten)")

    # --- 3. Ineffektive Regeln und Anpassungen ---
    if probleme:
        zeilen.append(f"\n  3. LEKTIONS-WIRKSAMKEIT — Regeln die nicht griffen")
        zeilen.append(f"  {sub}")
        for p in probleme:
            zeilen.append(f"\n  [{p['status']}] Kategorie: {p['kategorie']}")
            zeilen.append(f"  Regel        : \"{p['lehre'][:90]}\"")
            zeilen.append(f"  Aufgetreten  : {p['haeufigkeit']}x seit {p['erstellt_am']}")
            if p["status"] == "INEFFEKTIV":
                zeilen.append(f"  Aktion       : Neue staerkere Regel wurde generiert")

    if angepasst > 0:
        zeilen.append(f"\n  → {angepasst} Regel(n) durch staerkere Formulierungen ersetzt.")

    # --- 4. Lean-Prinzip ---
    zeilen.append(f"\n  4. LEAN PROCESSING — PDCA-ZYKLUS")
    zeilen.append(f"  {sub}")
    zeilen.append(f"  Plan   : Lektionen aus Fehlern ableiten")
    zeilen.append(f"  Do     : Lektionen in KI-Prompts einspeisen")
    zeilen.append(f"  Check  : Taeglich pruefen ob gleicher Fehler erneut auftrat")
    zeilen.append(f"  Act    : Ineffektive Regeln durch staerkere ersetzen")
    zeilen.append(f"\n  Offene Zyklen   : {len(probleme)}")
    zeilen.append(f"  Heute angepasst : {angepasst}")

    zeilen.append(f"\n{sep}")
    return "\n".join(zeilen)


def speichere_tages_lern_report(bericht_text: str, lern_ergebnis: dict, angepasst: int):
    """Speichert Bericht in DB und als Textdatei."""
    heute = datetime.now().strftime("%Y-%m-%d")
    initialisiere_lern_db()
    with sqlite3.connect(LERN_DB) as conn:
        conn.execute("""
            INSERT OR REPLACE INTO lern_tagesberichte
                (datum, bericht, trefferquote, neue_lehren, angepasste)
            VALUES (?, ?, ?, ?, ?)
        """, (
            heute, bericht_text,
            round(lern_ergebnis.get("trefferquote", 0), 1),
            lern_ergebnis.get("fehler", 0) + lern_ergebnis.get("verpasste_chancen", 0),
            angepasst,
        ))

    os.makedirs("output", exist_ok=True)
    datei = f"output/lern_report_{heute}.txt"
    with open(datei, "w", encoding="utf-8") as f:
        f.write(bericht_text)


def hole_lern_bericht() -> dict:
    """Schneller Bericht ohne neuen Lernzyklus — fuer Dashboard."""
    initialisiere_lern_db()
    top_lehren = hole_top_lehren(5)
    probleme   = validiere_lehren()

    with sqlite3.connect(LERN_DB) as conn:
        conn.row_factory = sqlite3.Row
        letzte_fehler = conn.execute("""
            SELECT asset, datum_signal, rendite_5d, rendite_10d,
                   fehler_typ, lehre
            FROM fehleranalysen
            ORDER BY datum_analyse DESC
            LIMIT 5
        """).fetchall()
        letzte_berichte = conn.execute("""
            SELECT datum, trefferquote, neue_lehren, angepasste
            FROM lern_tagesberichte
            ORDER BY datum DESC
            LIMIT 7
        """).fetchall()

    return {
        "letzte_fehler":   [dict(r) for r in letzte_fehler],
        "top_lehren":      top_lehren,
        "probleme":        probleme,
        "letzte_berichte": [dict(r) for r in letzte_berichte],
    }


# ---------------------------------------------------------------------------
# Ausgabe
# ---------------------------------------------------------------------------

def drucke_lernbericht(ergebnis: dict):
    print(f"\n{'='*62}")
    print(f"  TAEGLICH LERN-BERICHT")
    print(f"{'='*62}")
    print(f"  Signale geprueft    : {ergebnis['signale_gesamt']}")
    print(f"  Korrekte Calls      : {ergebnis['korrekte']}  ({ergebnis['trefferquote']:.1f}%)")
    print(f"  Verlust-Fehler      : {ergebnis['fehler']}")
    print(f"  Verpasste Chancen   : {ergebnis.get('verpasste_chancen', 0)}")

    if ergebnis["analysen"]:
        print(f"\n  KI-ANALYSEN (Fehler + verpasste Chancen):")
        for a in ergebnis["analysen"]:
            typ = "VERPASSTE CHANCE" if a.fehler_typ == "VERPASSTE_CHANCE" else "VERLUST"
            print(f"\n  [{typ}] {a.asset} ({a.datum_signal})")
            print(f"  Rendite: 5d={a.rendite_5d:+.1f}%  10d={a.rendite_10d:+.1f}%")
            for zeile in a.ki_analyse.splitlines()[:6]:
                if zeile.strip():
                    print(f"    {zeile}")

    if ergebnis["top_lehren"]:
        print(f"\n  AKTIVE ERKENNTNISSE (werden heute in Analyse eingesetzt):")
        for l in ergebnis["top_lehren"][:5]:
            bestaet = f" [{l['haeufigkeit']}x bestaetigt]" if l["haeufigkeit"] > 1 else ""
            print(f"  • {l['lehre']}{bestaet}")

    print(f"{'='*62}")


# ---------------------------------------------------------------------------
# Einstiegspunkt
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Trading Intelligence System — Lern-Agent\n")
    ergebnis = fuehre_lernzyklus_durch()
    drucke_lernbericht(ergebnis)
