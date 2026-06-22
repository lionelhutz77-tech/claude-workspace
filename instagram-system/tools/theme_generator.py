# -*- coding: utf-8 -*-
"""
Erzeugt mit Groq einen kompletten Karussell-Bauplan zu einem "Früher & Heute"-
Thema – streng nach den Leitplanken in vorlagen/content_richtlinien.json
(warm/positiv, jugendfrei, ausgewogene Vielfalt, authentisch).

Ausführen (Test): python -m tools.theme_generator
"""

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.gemini_client import get_client, generate_with_retry, extract_json

RICHTLINIEN = Path("vorlagen/content_richtlinien.json")
VERLAUF = Path("output/themen_verlauf.json")

PROMPT = """Du entwickelst einen Instagram-Karussell-Post fuer den deutschen Account
"Frueher & Heute" (@kiai1977). Konzept: warmherzige Vergleiche zwischen frueher
(Kindheit der 70er-90er) und heute, die zum Nachdenken anregen.

STRIKTE REGELN:
- Ton: warm, wehmuetig, positiv, einladend. NIEMALS anklagend, zynisch oder mit
  erhobenem Zeigefinger. Der Betrachter soll laecheln und nicken.
- Sprich den Betrachter IMMER mit "du" an (informell, niemals "Sie").
- Variiere die Hook-Eroeffnung - NICHT immer "Erinnerst du dich noch". Nutze
  abwechslungsreiche Einstiege (z.B. "Weisst du noch...", "Es gab eine Zeit...",
  "Frueher war es ganz normal...", eine ueberraschende Aussage, eine Frage).
- Jugendfrei (FSK 0): keine Gewalt, Nacktheit, Politik, Religion, Diskriminierung.
- Vielfalt ueber die Bilder: abwechselnd maennlich/weiblich, jung/alt, Kinder,
  Familien, Paare. Natuerlich, nicht aufgesetzt.
- Authentisch und konkret, keine hohlen Floskeln.
- Bild-Szenen ohne Text beschreiben (englisch, knapp, bildhaft, MIT Angabe der
  Person: z.B. 'a young girl', 'an older man', 'two boys', 'a family').
- HAENDE-REGEL (FLUX ist schwach bei Haenden): VERMEIDE fehleranfaellige Posen —
  KEINE offenen Handflaechen zur Kamera, KEINE extremen Hand-Nahaufnahmen, keine
  vielen Haende dicht beieinander. Bevorzuge natuerliche, entspannte Haltungen:
  von hinten/seitlich, etwas Abstand (full figure/wide), Haende ruhig an der
  Seite, in der Tasche, am Tisch ruhend oder verdeckt. So entstehen weniger
  Anatomie-Fehler.

WICHTIGSTE REGEL — KEINE WIEDERHOLUNGEN:
- Die 5 Vergleiche muessen 5 VOELLIG VERSCHIEDENE, KONKRETE Facetten zeigen.
  NIEMALS dieselbe Aussage umformulieren! Jeder Vergleich = ein ANDERER Aspekt,
  eine ANDERE konkrete Situation, ein ANDERES Objekt, ein anderer Sinn/Moment.
  (Schlecht, weil 5x dasselbe: "Geschenk war besonders / wir schaetzten es /
  war ein Erlebnis / war ein Zeichen der Liebe / freuten uns darueber".
  Gut, weil 5 verschiedene Facetten beim Thema Geschenke: 1) das wochenlange
  Warten/Vorfreude, 2) EIN Spielzeug monatelang bespielt, 3) der Dankesbrief
  danach, 4) das Auspack-Ritual mit der Familie, 5) selbst etwas gebastelt statt
  gekauft.)
- ECHTER KONTRAST im Bild: Frueher-Szene und Heute-Szene zeigen UNTERSCHIEDLICHE
  Objekte/Situationen — nicht zweimal dasselbe Objekt (nicht oben Geschenk und
  unten auch Geschenk). Der visuelle Gegensatz muss sofort erkennbar sein.
- KONKRET & SINNLICH statt abstrakt: nenne ein greifbares Detail, Objekt oder
  eine Geste. Vermeide leere Floskeln wie "war besonders", "verliert sich",
  "hat sich geaendert".

THEMA HEUTE: "{thema}"
{thema_detail}

Erstelle GENAU dieses JSON (deutsch fuer Texte, englisch fuer prompts):
{{
  "thema": "kurzer Titel",
  "hook": {{
    "zeilen": ["Zeile1","Zeile2","","Zeile3","Zeile4"],
    "prompt": "warme Szene von frueher passend zum Thema, english, mit Person"
  }},
  "paare": [
    {{"oben_text":"Früher: ... (max 11 Woerter, korrekte Umlaute ä ö ü ß verwenden)",
      "oben_prompt":"warme Szene frueher, english, mit konkreter Person",
      "unten_text":"Heute: ... (max 11 Woerter, korrekte Umlaute ä ö ü ß)",
      "unten_prompt":"moderne Szene heute, english, mit konkreter Person"}}
  ],
  "cta": {{
    "zeilen": ["Frage an Community Zeile1","Zeile2","","Schreib es in die Kommentare."],
    "prompt": "warme einladende Schluss-Szene, english, mit Person die laechelt/winkt"
  }},
  "caption": "Instagram-Caption-FLIESSTEXT: 4-6 warme Saetze zum Thema, endet mit der konkreten Community-Frage und der Aufforderung EIN Wort in die Kommentare zu schreiben. KEINE Hashtags, KEIN 'Folge @kiai1977', KEIN KI-Hinweis hier (das wird automatisch ergaenzt).",
  "hashtags": "20-30 passende deutsche Hashtags mit # getrennt durch Leerzeichen, Mischung aus grossen und nischigen"
}}

WICHTIG: Genau 5 Eintraege in "paare". Jeder Vergleich konkret und bildhaft.
Im CTA-Slide KEIN 'Folge @kiai1977' (steht spaeter in der Caption) - nur Frage + Aufforderung zu kommentieren."""


_TYPO = {
    "Frueher": "Früher", "FRUEHER": "FRÜHER",
    "Erinnnerst": "Erinnerst", "Erinnnern": "Erinnern", "erinnnerst": "erinnerst",
    # haeufige ASCII-Transliterationen, die Groq trotz Vorgabe einstreut
    "Weisst": "Weißt", "weisst": "weißt", "heisst": "heißt", "Heisst": "Heißt",
    "Ueber": "Über", "ueber": "über", "Strasse": "Straße", "strasse": "straße",
    "groesser": "größer", "schoener": "schöner", "schoen": "schön",
}

# Feste, konstante Caption-Struktur (Wunsch User: Kontinuitaet wie erster Post)
CAPTION_FOOTER = ("Folge @kiai1977 für mehr Reisen zwischen Früher & Heute.\n"
                  "🤖 Bilder mit KI erstellt.")


def build_caption(spec):
    """Setzt die Caption immer gleich zusammen:
    Fliesstext + Frage  ->  Leerzeile  ->  Folge-Zeile + KI-Hinweis  ->  Hashtags."""
    body = (spec.get("caption") or "").strip()
    # evtl. vom Modell doch eingefuegte Footer-/Hashtag-Zeilen entfernen
    keep = []
    for line in body.splitlines():
        low = line.lower()
        if low.startswith("#") or "@kiai1977" in low or "ki erstellt" in low \
                or low.startswith("folge "):
            continue
        keep.append(line)
    body = "\n".join(keep).strip()
    hashtags = (spec.get("hashtags") or "").strip()
    return f"{body}\n\n{CAPTION_FOOTER}\n\n.\n.\n.\n{hashtags}"


def _fix(s):
    if not isinstance(s, str):
        return s
    for bad, good in _TYPO.items():
        s = s.replace(bad, good)
    return s


# Kompaktes, einheitliches CTA-Ende im Bild (die volle Folge-Zeile + KI-Hinweis
# stehen ohnehin in der Caption). Kurz, damit es unter Gesichtern Platz hat.
CTA_TAIL = ["", "Schreib es in die Kommentare.", "", "Folge @kiai1977"]


def _normalize(spec):
    """Bereinigt Tippfehler und erzwingt eine EINHEITLICHE CTA-Struktur."""
    for p in spec.get("paare", []):
        p["oben_text"] = _fix(p.get("oben_text", ""))
        p["unten_text"] = _fix(p.get("unten_text", ""))
    for key in ("hook", "cta"):
        if key in spec and "zeilen" in spec[key]:
            spec[key]["zeilen"] = [_fix(z) for z in spec[key]["zeilen"]]
    spec["caption"] = _fix(spec.get("caption", ""))

    # Einheitliches CTA-Ende: die VOLLSTAENDIGE Frage behalten (auch mehrzeilig),
    # also alle fuehrenden nicht-leeren Zeilen bis einschliesslich der "?"-Zeile;
    # danach fester, kurzer Schluss. So bleibt die Frage komplett und es rutschen
    # keine Tail-Reste durch.
    cta = spec.get("cta", {})
    frage = []
    for z in cta.get("zeilen", []):
        if not z.strip():
            if frage:
                break  # Frage ist zu Ende (Leerzeile nach Fragezeilen)
            continue   # fuehrende Leerzeilen ueberspringen
        frage.append(z)
        if z.strip().endswith("?"):
            break      # Fragezeichen = Ende der Frage
    cta["zeilen"] = frage[:2] + CTA_TAIL
    spec["cta"] = cta


def _load_richtlinien():
    if RICHTLINIEN.exists():
        return json.load(open(RICHTLINIEN, encoding="utf-8"))
    return {}


def _pick_thema(richtlinien):
    """Waehlt ein noch nicht (kuerzlich) genutztes persoenliches Thema."""
    themen = richtlinien.get("persoenliche_themen", [])
    themen = [t for t in themen if isinstance(t, dict)]
    verlauf = json.load(open(VERLAUF, encoding="utf-8")) if VERLAUF.exists() else []
    letzte = set(verlauf[-4:])  # die letzten 4 nicht wiederholen
    frei = [t for t in themen if t["thema"] not in letzte] or themen
    return random.choice(frei)


def generate_spec(thema_override=None):
    richtlinien = _load_richtlinien()
    if thema_override:
        thema, detail = thema_override, ""
    else:
        t = _pick_thema(richtlinien)
        thema = t["thema"]
        detail = (f"Kern frueher: {t.get('frueher','')}\n"
                  f"Kern heute: {t.get('heute','')}\n"
                  f"Gefuehl: {t.get('gefuehl','')}")

    client = get_client()
    raw = generate_with_retry(client, PROMPT.format(thema=thema, thema_detail=detail))
    spec = extract_json(raw)
    spec["paare"] = spec["paare"][:5]  # sicherstellen: genau 5
    _normalize(spec)

    # Verlauf fortschreiben
    verlauf = json.load(open(VERLAUF, encoding="utf-8")) if VERLAUF.exists() else []
    verlauf.append(thema)
    VERLAUF.parent.mkdir(parents=True, exist_ok=True)
    json.dump(verlauf, open(VERLAUF, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    return spec


def main():
    spec = generate_spec()
    print(json.dumps(spec, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
