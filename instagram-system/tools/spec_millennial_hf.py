# -*- coding: utf-8 -*-
"""Bauplan fuer das erste Listen-Karussell (viraler Stil) item_15:
'9 Wege auf Millennial-Art zu sagen, dass man heute Abend daheim bleibt'.
Bilder = alte Gemaelde via Higgsfield (bekleidet), Text via slide_liste."""
import json
from pathlib import Path

spec = {
    "thema": "Millennial-Art: heute Abend absagen",
    "format": "liste",
    "quelle": "Higgsfield Soul 2.0",
    "hook": {
        "zeilen": ["9 Wege auf Millennial-Art", "zu sagen, dass man heute Abend",
                   "doch nicht mehr rausgeht"],
        "prompt": "hook"
    },
    "items": [
        {"text": "Mein Sozialakku ist auf 1 % – Energiesparmodus aktiviert.", "prompt": "i0"},
        {"text": "Ich committe mich heute Abend voll und ganz meiner Couch.", "prompt": "i1"},
        {"text": "Ich arbeite gerade dringend an meiner Work-Life-Balance. Auf dem Sofa.", "prompt": "i2"},
        {"text": "Adulting war heute genug – ich logge mich aus.", "prompt": "i3"},
        {"text": "Das Bett und ich haben was Festes, sorry.", "prompt": "i4"},
        {"text": "Ich ghoste nicht dich, nur den Plan.", "prompt": "i5"},
        {"text": "Self-Care-Abend – ich priorisiere gerade mich.", "prompt": "i6"},
        {"text": "Ich brauche Me-Time. Sofort. An einem Dienstag.", "prompt": "i7"},
        {"text": "Netflix hat zuerst gefragt – ist jetzt halt verbindlich.", "prompt": "i8"},
    ],
    "cta": {
        "zeilen": ["Welcher bist du?", "Schreib die Nummer", "in die Kommentare.",
                   "", "Folge @kiai1977", "für mehr."],
        "prompt": "cta"
    },
    "caption": ("9 Wege auf Millennial-Art zu sagen, dass man heute Abend doch "
                "lieber daheim bleibt. 😅 Welcher bist du - 1 bis 9? Schreib die "
                "Nummer in die Kommentare!"),
    "hashtags": ("#Millennials #MillennialLife #Sozialakku #Couch #IntrovertProblems "
                 "#Adulting #SelfCare #MeTime #Humor #Relatable #Memes #Alltag "
                 "#TypischMillennial #LustigeSprüche #FürDich #Comedy #Wahrheit "
                 "#KeinBock #Couchabend #Nachtmensch"),
}

base = Path("output/queue/item_15")
(base / "raw").mkdir(parents=True, exist_ok=True)
for f in (base / "raw").glob("*.png"):
    f.unlink()
json.dump(spec, open(base / "spec.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
print("item_15 Bauplan (Listen-Format) angelegt:", base)
