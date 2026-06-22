# -*- coding: utf-8 -*-
"""
Generiert die 8 Shots für das dynamische Rezept-Reel (Template: vorlagen/
template_dynamisch.json). Look: dunkel, dramatisches Seitenlicht, Close-ups.

Ausführen: python -m tools.recipe_images_v3  (aus instagram-system/)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.recipe_images import generate_image

STYLE = ("dark moody food photography, black background, dramatic side "
         "lighting, shallow depth of field, warm golden tones, professional "
         "food styling, vertical 9:16 composition")

SHOTS = [
    ("v3_01_hook", "Steaming rustic pot of golden clear beef broth on dark "
     "wooden table, dramatic light from the side, steam rising, "),
    ("v3_02_fleisch", "Extreme close-up of raw beef cut on dark butcher paper, "
     "marbled texture, coarse salt crystals scattered, "),
    ("v3_03_gemuese", "Fresh soup vegetables bundle - carrot leek celery "
     "parsley root - tied with twine, water droplets, extreme close-up, "),
    ("v3_04_topf", "Pot of simmering broth, bubbles on surface, rising steam "
     "backlit by warm light, extreme close-up of surface, "),
    ("v3_05_abschoepfen", "Ladle skimming foam from simmering golden broth, "
     "motion, extreme close-up, steam, "),
    ("v3_06_sieben", "Golden clear broth being poured through fine sieve into "
     "white bowl, liquid in motion, pouring action shot, "),
    ("v3_07_sahne", "Cream being poured into golden soup, white swirl forming "
     "in liquid, extreme close-up, motion, "),
    ("v3_08_hero", "Elegant white bowl of clear beef consomme with carrot and "
     "green peas, steam rising, garnished with fresh parsley, hero shot at "
     "eye level on dark slate plate, "),
]


def main():
    out_dir = Path("output/media/rezept_001/v3")
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Generiere {len(SHOTS)} Shots im Dark-Food-Look...")
    ok = 0
    for i, (name, prompt) in enumerate(SHOTS):
        target = out_dir / f"{name}.jpg"
        if target.exists():
            print(f"\n[{name}] existiert schon, überspringe.")
            ok += 1
            continue
        print(f"\n[{name}]")
        if generate_image(prompt + STYLE, target, seed=str(1000 + i)):
            ok += 1

    print(f"\nFertig: {ok}/{len(SHOTS)} Shots in {out_dir}")


if __name__ == "__main__":
    main()
