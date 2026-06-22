"""
Trend Scout v2 - "Wie sieht's heute aus?"
Findet strukturelle Nischen-Chancen aus 4-Wochen-Rising-Trends.
Filtert News/Personen automatisch raus, prueft Konkurrenz via DuckDuckGo.
"""

import os
import sys
import time
import json
from datetime import datetime

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
load_dotenv()

# ── Konfiguration ─────────────────────────────────────────────────────────────

# Breite Kategorie-Seeds: strukturelle Themen, keine News
SEEDS = [
    "Geld sparen", "Arbeit verlieren", "Nebeneinkommen", "Rente",
    "Energie sparen", "Wohnung mieten", "Gesundheit", "Weiterbildung",
    "KI lernen", "Schulden", "Steuern", "Freelancer", "Automatisierung",
    "Haushalt", "Versicherung"
]

GEO = "DE"


# ── Cache ─────────────────────────────────────────────────────────────────────

CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache_rising.json")
CACHE_MAX_AGE_H = 20  # Cache bis zu 20 Stunden gueltig (einmal taeglich reicht)


def load_cache():
    if not os.path.exists(CACHE_FILE):
        return None
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        age_h = (time.time() - data["ts"]) / 3600
        if age_h < CACHE_MAX_AGE_H:
            print(f"  Cache genutzt (Alter: {age_h:.1f}h, gueltig bis {CACHE_MAX_AGE_H}h)")
            return data["rising"]
        print(f"  Cache abgelaufen ({age_h:.1f}h) -- lade neu")
    except Exception:
        pass
    return None


def save_cache(rising):
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({"ts": time.time(), "rising": rising}, f, ensure_ascii=False)
    except Exception as e:
        print(f"  [!] Cache speichern fehlgeschlagen: {e}")


# ── Schritt 1: Rising Queries der letzten 4 Wochen ───────────────────────────

def get_rising_queries(seeds, timeframe="today 1-m", geo=GEO):
    """Holt steigende Suchanfragen fuer alle Seed-Kategorien."""
    try:
        from pytrends.request import TrendReq
    except ImportError:
        print("  [!] pytrends nicht installiert")
        return {}

    pt = TrendReq(hl="de-DE", tz=60, timeout=(10, 30))
    all_rising = {}

    # Pytrends erlaubt max 5 Keywords pro Request
    batches = [seeds[i:i+5] for i in range(0, len(seeds), 5)]

    for batch in batches:
        try:
            pt.build_payload(batch, timeframe=timeframe, geo=geo)
            related = pt.related_queries()
            for kw in batch:
                rising = related.get(kw, {}).get("rising")
                if rising is not None and not rising.empty:
                    # Nur Queries mit Breakout oder hohem Anstieg
                    top = rising.head(8)["query"].tolist()
                    all_rising[kw] = top
            time.sleep(2)
        except Exception as e:
            print(f"  [!] Batch {batch}: {e}")
            time.sleep(3)

    return all_rising


# ── Schritt 2: KI-Filter — Personen/Events rauswerfen ────────────────────────

def filter_structural_topics(rising_dict):
    """
    Groq filtert jeden Query: ist das ein strukturelles Thema (Bedarf)
    oder eine Person/ein Ereignis/eine News? Gibt nur strukturelle zurueck.
    """
    from groq import Groq

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("  [!] GROQ_API_KEY fehlt")
        return {}

    client = Groq(api_key=api_key)

    # Alle Queries als flache Liste zusammenstellen
    all_queries = []
    for seed, queries in rising_dict.items():
        for q in queries:
            all_queries.append({"seed": seed, "query": q})

    if not all_queries:
        return {}

    query_list = "\n".join(f"- {i+1}. [{q['seed']}] {q['query']}"
                           for i, q in enumerate(all_queries))

    prompt = f"""Du bist ein Filter-System. Klassifiziere jede Suchanfrage:

STRUKTURELL = anhaltender Bedarf, Problem, Informationsbedarf (z.B. "Miete erhoehen legal", "ALG1 berechnen", "ChatGPT fuer Excel")
NICHT-STRUKTURELL = Person, Promi, Sportereignis, Nachricht, Hoax, einmaliges Ereignis

Antworte NUR mit JSON-Array. Fuer jeden Eintrag: {{"nr": 1, "query": "...", "seed": "...", "typ": "STRUKTURELL" oder "NEIN"}}

Suchanfragen:
{query_list}

JSON:"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=2000,
            temperature=0,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = response.choices[0].message.content.strip()
        # JSON extrahieren
        start = raw.find("[")
        end = raw.rfind("]") + 1
        if start == -1:
            return {}
        data = json.loads(raw[start:end])
        structural = [d for d in data if d.get("typ") == "STRUKTURELL"]
        return structural
    except Exception as e:
        print(f"  [!] Filter-Fehler: {e}")
        return []


# ── Schritt 3: Konkurrenz-Check via DuckDuckGo ───────────────────────────────

def check_competition(candidates):
    """
    Fuer jeden strukturellen Kandidaten: sucht bestehende Produkte/Tools.
    Gibt Dict {query: [Konkurrenz-Snippets]} zurueck.
    """
    try:
        from ddgs import DDGS
    except ImportError:
        print("  [!] ddgs nicht installiert")
        return {}

    competition = {}

    for item in candidates[:12]:  # Max 12 um Zeit zu sparen
        query = item["query"]
        search_term = f"{query} Produkt Tool App kaufen Ratgeber deutsch"
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(search_term, max_results=4, region="de-de"))
            snippets = [f"{r['title']}: {r['body'][:120]}" for r in results]
            competition[query] = snippets
            time.sleep(1)
        except Exception as e:
            competition[query] = [f"Suche fehlgeschlagen: {e}"]

    return competition


# ── Schritt 4: Marktanalyse mit Groq ─────────────────────────────────────────

def analyze_opportunities(candidates, competition):
    """
    Groq bewertet jeden Kandidaten auf Marktluecke, Umsetzbarkeit,
    Monetarisierungspotenzial. Gibt die besten 3 mit vollstaendiger Analyse.
    """
    from groq import Groq

    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    # Kandidaten + Konkurrenz zusammenbauen
    blocks = []
    for item in candidates[:12]:
        q = item["query"]
        comp = competition.get(q, [])
        comp_text = "\n  ".join(comp) if comp else "keine Konkurrenz gefunden"
        blocks.append(f"THEMA: {q} (aus Kategorie: {item['seed']})\nKonkurrenz:\n  {comp_text}")

    kandidaten_text = "\n\n".join(blocks)

    prompt = f"""Du bist ein Produktstratege fuer passives Einkommen im deutschsprachigen Markt.
Heute: {datetime.now().strftime('%d.%m.%Y')}

Hier sind strukturell steigende Suchanfragen der letzten 4 Wochen aus Deutschland,
plus die tatsaechlich gefundenen Konkurrenzprodukte aus einer echten Websuche:

{kandidaten_text}

PFLICHTREGELN - KEINE AUSNAHMEN:

1. KONKURRENZ EXPLIZIT BENENNEN: Fuer jedes Thema musst du die gefundenen Konkurrenten
   namentlich nennen (z.B. "finanz-tools.de bietet bereits einen kostenlosen Rechner an").
   Vage Aussagen wie "Konkurrenz vorhanden" sind verboten.

2. EHRLICHE LÜCKEN-PRÜFUNG: Wenn die Konkurrenz das Thema bereits kostenlos und gut abdeckt,
   schreibe: "KEIN PRODUKT MOEGLICH - [Grund]" und gehe zum naechsten Thema.

3. NUR ECHTE LÜCKEN: Eine Marktluecke ist nur dann real, wenn du konkret benennen kannst
   WAS die vorhandenen Produkte nicht koennen oder fuer wen sie nicht geeignet sind.

4. KEINE ERFUNDENEN SCHWAECHEN: Behaupte keine Schwaechen der Konkurrenz, die du nicht
   aus den Suchergebnissen belegen kannst.

Analysiere ALLE {len(candidates[:12])} Themen kurz, dann praesentiere die TOP 3 (oder weniger,
falls nicht genuegend echte Luecken existieren) mit vollstaendiger Analyse:

## [RANG]. [Thema]
**Konkurrenz (namentlich):** (welche Anbieter, kostenlos oder bezahlt, wie gut?)
**Echte Luecke:** (was koennen diese nicht, oder welche Zielgruppe wird nicht bedient?)
**ODER: KEIN PRODUKT MOEGLICH** - (Grund in einem Satz)
**Produkt-Idee:** (nur wenn Luecke real: praezise beschreiben, z.B. "Python-Tool das X tut")
**MVP in 4 Wochen:** (was Version 1.0 kann, was nicht)
**Monetarisierung:** (Preis, Plattform, warum zahlen Nutzer dafuer und nicht fuer die Konkurrenz?)
**Groesstes Risiko:** (ein konkreter Satz)

Wenn es heute keine 3 echten Luecken gibt: sag das direkt.
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=3000,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Analyse-Fehler: {e}"


# ── Hauptprogramm ─────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print(f"  TREND SCOUT v2 -- {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    print("  Modus: 4-Wochen Rising Trends + Konkurrenzcheck")
    print("=" * 60)

    # Schritt 1
    print(f"\n[1/4] Lade steigende Suchanfragen (letzte 4 Wochen) ...")
    rising = load_cache()
    if rising is None:
        print(f"      Seeds: {len(SEEDS)} Kategorien werden abgefragt ...")
        rising = get_rising_queries(SEEDS, timeframe="today 1-m", geo=GEO)
        if rising:
            save_cache(rising)

    total = sum(len(v) for v in rising.values())
    print(f"      OK: {total} steigende Queries aus {len(rising)} Kategorien")

    if total == 0:
        print("\n  Keine Rising-Daten verfuegbar. Bitte spaeter erneut versuchen.")
        return

    # Schritt 2
    print(f"\n[2/4] KI filtert Personen/News/Events heraus ...")
    structural = filter_structural_topics(rising)
    print(f"      OK: {len(structural)} strukturelle Themen behalten")

    if not structural:
        print("\n  Keine strukturellen Themen gefunden. Trends heute zu nachrichtengetrieben.")
        return

    # Schritt 3
    print(f"\n[3/4] Konkurrenz-Check via DuckDuckGo ({min(len(structural), 12)} Themen) ...")
    competition = check_competition(structural)
    print(f"      OK: {len(competition)} Themen recherchiert")

    # Schritt 4
    print(f"\n[4/4] Marktanalyse -- Groq bewertet Chancen und Risiken ...")
    analysis = analyze_opportunities(structural, competition)

    # Ausgabe
    print("\n" + "=" * 60)
    print("  MARKTANALYSE -- TOP NISCHEN-CHANCEN")
    print("=" * 60 + "\n")
    print(analysis)

    # Report speichern
    report_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
    os.makedirs(report_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    filename = os.path.join(report_dir, f"report_{ts}.txt")

    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"TREND SCOUT v2 -- {datetime.now().strftime('%d.%m.%Y %H:%M')}\n")
        f.write("=" * 60 + "\n\n")
        f.write("RISING QUERIES (4 Wochen):\n")
        for seed, queries in rising.items():
            if queries:
                f.write(f"\n{seed}:\n" + "\n".join(f"  - {q}" for q in queries) + "\n")
        f.write(f"\nSTRUKTURELL ({len(structural)}):\n")
        for s in structural:
            f.write(f"  - [{s['seed']}] {s['query']}\n")
        f.write("\nANALYSE:\n\n")
        f.write(analysis)

    print(f"\n>> Report gespeichert: {filename}")


if __name__ == "__main__":
    main()
