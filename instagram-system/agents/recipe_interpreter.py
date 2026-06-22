# -*- coding: utf-8 -*-
"""
Rezept-Interpreter: Nimmt ein historisches Original-Rezept (Davidis, 1845)
und erstellt eine moderne Interpretation für 2 Personen.

Regeln (User-Vorgaben):
- Immer für 2 Personen konzipiert
- Deutsche Standard-Packungsgrößen verwenden (Sahne 200 ml, Butter 250 g,
  Joghurt 150 g/500 g, Milch 1 l, Schmand 200 g, Crème fraîche 150 g ...)
- Keine Reste: gekaufte Packungen sollen vollständig verwendet werden
  (lose Ware wie Fleisch/Gemüse von der Theke darf grammgenau sein)

Ausführen: python -m agents.recipe_interpreter  (aus instagram-system/)
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.gemini_client import get_client, generate_with_retry, extract_json

PROMPT_TEMPLATE = """Du bist ein erfahrener deutscher Koch und Rezeptentwickler.

Hier ist ein ORIGINAL-Rezept aus dem "Praktischen Kochbuch" von Henriette Davidis (1845):

---
{original}
---

Erstelle daraus eine MODERNE INTERPRETATION als vollwertiges Gericht. Regeln:

1. FÜR GENAU 2 PERSONEN konzipiert.
2. DEUTSCHE STANDARD-PACKUNGSGRÖSSEN: Abgepackte Zutaten nur in Mengen, die
   es im deutschen Supermarkt wirklich gibt, und zwar so, dass die Packung
   KOMPLETT aufgebraucht wird (keine Reste!). Beispiele:
   - Sahne: 200 ml Becher
   - Butter: 250 g (Teilverbrauch ok, Butter hält sich)
   - Schmand: 200 g, Crème fraîche: 150 g
   - Suppengrün: 1 Bund (Möhre, Lauch, Sellerie, Petersilienwurzel)
   - TK-Erbsen: 450 g Beutel (Teilverbrauch ok bei TK, da wiederverschließbar)
   Lose Ware (Fleischtheke, Gemüse einzeln, Kräuter) darf grammgenau sein.
   Grundvorräte (Salz, Pfeffer, Öl, Mehl, Gewürze) zählen nicht als Packung.
3. Wenn eine Packungsgröße nicht restlos aufgeht, ändere das Rezept so,
   dass sie aufgeht — oder wähle eine andere Zutat.
4. Moderner Kochstil: heutige Geräte, realistische Zeiten, klare Schritte.
5. Bleibe im Geist des Originals erkennbar.

Antworte NUR mit JSON in genau diesem Format:
{{
  "titel_original": "...",
  "titel_modern": "...",
  "jahr_original": 1845,
  "kurzbeschreibung": "1-2 Sätze, was das Gericht ist und was es mit dem Original verbindet",
  "portionen": 2,
  "zeit_minuten": 0,
  "zutaten": [
    {{"menge": "...", "zutat": "...", "einkauf": "z.B. '1 Becher (200 ml)' oder 'Fleischtheke, 400 g' oder 'Vorrat'", "restlos": true}}
  ],
  "schritte": ["Schritt 1 ...", "Schritt 2 ..."],
  "einkaufsliste": ["1 Becher Sahne (200 ml)", "..."],
  "tipp": "Ein kurzer Profi-Tipp",
  "instagram_caption": "Caption für den Post, deutsch, mit Bezug auf 1845, max 150 Wörter, am Ende Hashtags und den Hinweis '🤖 Erstellt mit KI'"
}}"""


def interpret(original_text: str) -> dict:
    client = get_client()
    prompt = PROMPT_TEMPLATE.format(original=original_text[:4000])
    raw = generate_with_retry(client, prompt)
    return extract_json(raw)


def main():
    src = Path("output/rezept_001_original.txt")
    if not src.exists():
        print("FEHLER: output/rezept_001_original.txt fehlt.")
        sys.exit(1)

    original = src.read_text(encoding="utf-8")
    print("Erstelle moderne Interpretation (Groq)...")
    result = interpret(original)

    out = Path("output/rezept_001_modern.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"Gespeichert: {out}")
    print(f"\n{result['titel_modern']} ({result['zeit_minuten']} Min., 2 Personen)")
    print(f"\n{result['kurzbeschreibung']}\n")
    print("EINKAUFSLISTE:")
    for item in result["einkaufsliste"]:
        print(f"  - {item}")


if __name__ == "__main__":
    main()
