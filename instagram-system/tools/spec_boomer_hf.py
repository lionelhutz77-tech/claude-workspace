# -*- coding: utf-8 -*-
"""Bauplan fuer das Boomer-Listen-Karussell item_16 (Gegenstueck zu item_15):
'9 Saetze, an denen du einen echten Boomer erkennst'.
Bilder = alte Gemaelde via Higgsfield Soul 2.0 (bekleidet, europaeisch),
Text via slide_liste. Die 'prompt'-Felder dokumentieren die Higgsfield-Prompts."""
import json
from pathlib import Path

STYLE = ("classical 19th-century oil painting in old master style, warm "
         "candle-lit museum lighting, ornate, fair-skinned white European "
         "subjects, fully clothed, full figures, natural hands with five "
         "fingers, dignified")

spec = {
    "thema": "Boomer-Art: Saetze, an denen man einen Boomer erkennt",
    "format": "liste",
    "quelle": "Higgsfield Soul 2.0",
    "hook": {
        "zeilen": ["9 Sätze, an denen du", "einen echten Boomer",
                   "sofort erkennst"],
        "prompt": ("a distinguished elderly European gentleman with grey hair "
                   "and reading glasses, seated in a warm study, looking "
                   "thoughtfully at the viewer, ornate background, 19th century "
                   "suit, empty space at the bottom, " + STYLE)
    },
    "items": [
        {"text": "„Das hat damals 5 Mark gekostet – und läuft heute noch.“",
         "prompt": ("a thrifty elderly European burgher counting coins at a "
                    "wooden table, content expression, Dutch golden age "
                    "interior, " + STYLE)},
        {"text": "„Leg das Ding mal weg, wir sind hier zum Reden.“",
         "prompt": ("an elderly European patriarch at a candle-lit family "
                    "dinner table gesturing for attention, relatives listening, "
                    "warm interior, " + STYLE)},
        {"text": "„Warum schreibst du? Anrufen geht schneller.“",
         "prompt": ("a stern elderly European lady seated at a writing desk "
                    "with quill and paper, slightly impatient, Victorian "
                    "parlor, " + STYLE)},
        {"text": "„Wer hat hier überall das Licht anlassen?!“",
         "prompt": ("an elderly European woman holding a candle lantern in a "
                    "dim hallway at night, frugal expression, 19th century "
                    "house interior, " + STYLE)},
        {"text": "„Wegwerfen? Das kann man doch noch reparieren.“",
         "prompt": ("an old European craftsman repairing a wooden chair at his "
                    "workbench, focused, warm workshop, tools around, full "
                    "figure, " + STYLE)},
        {"text": "„Lass den Quatsch mit dem Navi – ich kenn den Weg.“",
         "prompt": ("a confident elderly European traveler standing outdoors "
                    "holding a folded paper map, pointing the way along a "
                    "country road, 19th century landscape, full figure, " + STYLE)},
        {"text": "„Bei dem bisschen Regen sind wir früher trotzdem raus.“",
         "prompt": ("European people walking through a rainy 19th century "
                    "street with umbrellas, cobblestones, moody warm light, "
                    "full figures, " + STYLE)},
        {"text": "„Brauchst du dafür echt 'ne App? Geht doch auf Papier.“",
         "prompt": ("an elderly European clerk at a desk surrounded by ledgers "
                    "and stacks of paper, quill in inkpot, warm office, " + STYLE)},
        {"text": "„Google? Frag lieber gleich mich.“",
         "prompt": ("a wise elderly European professor in a grand library full "
                    "of books, confident knowing smile, warm light, full upper "
                    "body, " + STYLE)},
    ],
    "cta": {
        "zeilen": ["Welcher Boomer-Satz", "fällt bei dir zu Hause?",
                   "Schreib ihn in die Kommentare.",
                   "", "Folge @kiai1977", "für mehr."],
        "prompt": ("a warm gathering of an extended European family around a "
                   "table, elderly grandparents smiling invitingly, cozy "
                   "candle-lit room, full figures, " + STYLE)
    },
    "caption": ("9 Sätze, an denen du einen echten Boomer erkennst. 😄 "
                "Hand aufs Herz – welcher fällt bei dir zu Hause? Schreib "
                "die Nummer in die Kommentare!"),
    "hashtags": ("#Boomer #TypischBoomer #Generationen #Früher #Nostalgie "
                 "#Familie #Humor #Relatable #Sprüche #Alltag #FürDich "
                 "#Comedy #Wahrheit #Eltern #Erinnerungen #BabyBoomer "
                 "#Generationenkonflikt #LustigeSprüche #Memes #Kindheit"),
}

base = Path("output/queue/item_16")
(base / "raw").mkdir(parents=True, exist_ok=True)
json.dump(spec, open(base / "spec.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
print("item_16 Bauplan (Boomer Listen-Format) angelegt:", base)
