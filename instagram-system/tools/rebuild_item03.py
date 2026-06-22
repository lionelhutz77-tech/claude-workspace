# -*- coding: utf-8 -*-
"""Setzt item_03 (Smartwatch) mit 5 distinkten Facetten komplett neu auf."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.carousel_builder import build_from_spec
from tools.carousel_to_reel import build_reel

spec = {
    "thema": "Smartwatch als Fessel",
    "hook": {
        "zeilen": ["Weißt du noch?", "Als eine Uhr nur eines tat:",
                   "die Zeit zeigen?", "", "Als man wirklich",
                   "abschalten konnte?"],
        "prompt": ("a young person lying relaxed in a sunny meadow watching the "
                   "clouds, completely free and unbothered, no devices")
    },
    "paare": [
        {"oben_text": "Früher: Die Uhr zeigte nur die Zeit",
         "oben_prompt": "a person calmly glancing at a simple analog wristwatch to check the time, relaxed quiet moment",
         "unten_text": "Heute: Sie vibriert bei jeder Nachricht",
         "unten_prompt": "close-up of a smartwatch on a wrist lighting up with a buzzing message notification, person glancing at it distracted, modern setting"},
        {"oben_text": "Früher: Auf dem Spaziergang war man weg",
         "oben_prompt": "a person walking peacefully along a sunny forest path, free and relaxed, no devices",
         "unten_text": "Heute: Die Arbeit erreicht dich am Arm",
         "unten_prompt": "a person on a walk looking annoyed at a work email notification on their smartwatch, urban path"},
        {"oben_text": "Früher: Man aß in Ruhe zusammen",
         "oben_prompt": "a family enjoying a calm dinner together at a table, talking and laughing, cozy warm light",
         "unten_text": "Heute: Beim Essen blinkt es am Arm",
         "unten_prompt": "a person at a dinner table distracted by a glowing notification on their smartwatch, plate of food in front"},
        {"oben_text": "Früher: Man bewegte sich aus Freude",
         "oben_prompt": "children joyfully running and playing outdoors in a green meadow, pure fun and laughter",
         "unten_text": "Heute: Die Uhr zählt jeden Schritt",
         "unten_prompt": "a jogger stopping to obsessively check the step count and statistics on their smartwatch, focused on the numbers"},
        {"oben_text": "Früher: Nachts war einfach Ruhe",
         "oben_prompt": "a person sleeping peacefully in a calm dark bedroom, serene, soft moonlight",
         "unten_text": "Heute: Selbst der Schlaf wird vermessen",
         "unten_prompt": "a person lying awake in bed at night checking sleep-tracking data on their glowing smartwatch in the dark"},
    ],
    "cta": {
        "zeilen": ["Wann hast du zuletzt", "bewusst alles abgelegt?"],
        "prompt": ("a relaxed happy person smiling peacefully outdoors without "
                   "any device, enjoying the moment, head and shoulders")
    },
    "caption": ("Weißt du noch? Früher zeigte eine Uhr einfach nur die Zeit – "
                "und sonst nichts. Man ging spazieren und war wirklich weg, man "
                "aß in Ruhe, bewegte sich aus reiner Freude und nachts war "
                "einfach Ruhe. Heute sitzt an unserem Handgelenk ein kleines "
                "Gerät, das vibriert, zählt, misst und uns nie ganz loslässt. "
                "Wann hast du zuletzt bewusst alles abgelegt und warst einfach "
                "nur da? Schreib mir EIN Wort in die Kommentare. 👇"),
    "hashtags": ("#Smartwatch #DigitalDetox #Achtsamkeit #Entschleunigung "
                 "#Erreichbarkeit #InnehaltenStattScrollen #weniger ist mehr "
                 "#Abschalten #Momente #Gedankenwelt #ZeitFürMich #SlowLiving "
                 "#BewusstLeben #Handysucht #DigitaleBalance #ZurückZurRuhe "
                 "#FrüherVsHeute #Nachdenklich #Lebensweisheiten #EchteMomente")
}

base = Path("output/queue/item_03")
json.dump(spec, open(base / "spec.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
for f in (base / "raw").glob("*.png"):
    f.unlink()
print("Neue Spec gesetzt, alte Bilder geloescht -> baue neu")
build_from_spec(spec, base, stil="nostalgie")
build_reel(base / "slides", base / "reel.mp4")
print("item_03 (Smartwatch) neu gebaut mit 5 distinkten Facetten")
