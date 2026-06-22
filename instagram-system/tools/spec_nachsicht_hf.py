# -*- coding: utf-8 -*-
"""Legt den Bauplan fuer das Higgsfield-Karussell item_06 'Nachsicht' an.
Texte bleiben, Bilder kommen via Higgsfield Soul 2.0 nach raw/."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.theme_generator import _normalize

spec = {
    "thema": "Nachsicht statt Meckern",
    "quelle": "Higgsfield Soul 2.0",
    "hook": {"zeilen": ["Weißt du noch?", "Als wir uns Zeit nahmen", "füreinander?",
                        "", "Als ein bisschen Nachsicht", "selbstverständlich war?"],
             "prompt": "hook"},
    "paare": [
        {"oben_text": "Früher: Geduld beim Fahrradfahren lernen", "oben_prompt": "p0_oben",
         "unten_text": "Heute: Hupen auf langsame Radfahrer", "unten_prompt": "p0_unten"},
        {"oben_text": "Früher: Ruhiges Malen mit dem Kind", "oben_prompt": "p1_oben",
         "unten_text": "Heute: Schimpfen über das langsame Handy", "unten_prompt": "p1_unten"},
        {"oben_text": "Früher: Der Lehrer ließ einen zweiten Versuch", "oben_prompt": "p2_oben",
         "unten_text": "Heute: Fehler werden laut kritisiert", "unten_prompt": "p2_unten"},
        {"oben_text": "Früher: Der Freund kam spät, der Kaffee wartete", "oben_prompt": "p3_oben",
         "unten_text": "Heute: Der Ärger wird sofort gepostet", "unten_prompt": "p3_unten"},
        {"oben_text": "Früher: Man half beim Kleingeld zählen", "oben_prompt": "p4_oben",
         "unten_text": "Heute: Ungeduld bei langsamer Zahlung", "unten_prompt": "p4_unten"},
    ],
    "cta": {"zeilen": ["Wann hast du zuletzt", "Nachsicht gezeigt statt gemeckert?"],
            "prompt": "cta"},
    "caption": ("Weißt du noch? Früher nahmen wir uns Zeit füreinander - der Vater, "
                "der geduldig das Fahrradfahren beibrachte, der Lehrer, der einen "
                "zweiten Versuch erlaubte, der Freund, der zu spät kam und trotzdem "
                "willkommen war. Heute klingt jedes Zögern wie ein Fehltritt, und "
                "der Ärger ist schneller getippt als ein freundliches Wort. Dabei "
                "könnte ein bisschen Nachsicht Wunder wirken. Wann hast du zuletzt "
                "Nachsicht gezeigt statt zu meckern? Schreib mir EIN Wort in die "
                "Kommentare. 👇"),
    "hashtags": ("#Nachsicht #Geduld #Gelassenheit #Mitgefühl #Freundlichkeit "
                 "#Achtsamkeit #Miteinander #Verständnis #WenigerMeckern #Güte "
                 "#FrüherVsHeute #Lebensweisheiten #Nachdenklich #BewusstLeben "
                 "#Gedankenwelt #Menschlichkeit #Rücksicht #Empathie #Werte "
                 "#EinfachMalDurchatmen"),
}
_normalize(spec)

base = Path("output/queue/item_06")
for f in (base / "raw").glob("*.png"):
    f.unlink()
(base / "raw").mkdir(parents=True, exist_ok=True)
json.dump(spec, open(base / "spec.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
print("item_06 Bauplan (Higgsfield) gesetzt, alte FLUX-Bilder geloescht")
