# -*- coding: utf-8 -*-
"""
Erzeugt die Profil-Assets fuer @kiai1977:
  - profilbild.jpg  (1080x1080, quadratisch, fuer Profilfoto)
  - 3 Logo-Varianten zur Auswahl

Ausführen: python -m tools.profile_assets  (aus instagram-system/)
"""

import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.recipe_images import generate_image_flux

CANDIDATES = [
    ("cosmic_1", "Photorealistic ornate antique hourglass standing on dark "
     "ground, inside the glass a glowing cosmic galaxy with stars and nebula "
     "as the sand, warm golden sand at the bottom, glowing particles floating, "
     "dramatic dark moody background, cinematic lighting, mystical atmosphere, "
     "highly detailed, centered"),
    ("cosmic_2", "Photorealistic vintage hourglass, swirling nebula and "
     "stardust flowing inside the glass, deep blues purples and warm amber, "
     "dust particles in the air, dark dramatic background, volumetric light, "
     "magical cinematic mood, ultra detailed, centered composition"),
    ("cosmic_3", "Photorealistic hourglass with a miniature universe inside, "
     "golden cosmic sand falling, glowing softly, surrounded by floating "
     "embers and dust, very dark background, warm rim light, cinematic, "
     "atmospheric, premium mystical aesthetic, centered"),
    ("cosmic_4", "Photorealistic ornate hourglass on weathered dark surface, "
     "galaxy and constellations glowing within the glass chamber, warm amber "
     "and teal tones, sparks and dust drifting, deep shadow background, "
     "dramatic cinematic side light, highly detailed, centered"),
]


def square_center(path: Path, size: int = 1080):
    img = Image.open(path).convert("RGB")
    s = min(img.size)
    x = (img.width - s) // 2
    y = (img.height - s) // 2
    img.crop((x, y, x + s, y + s)).resize((size, size), Image.LANCZOS).save(path, quality=94)


def main():
    out = Path("output/profile")
    out.mkdir(parents=True, exist_ok=True)

    print("Generiere Profilbild-Varianten (FLUX)...")
    for name, prompt in CANDIDATES:
        target = out / f"{name}.jpg"
        if not generate_image_flux(prompt, target):
            print(f"  FEHLER bei {name}")
            continue
        square_center(target)
        print(f"  OK: {target}")

    print(f"\nFertig. Varianten in {out}")


if __name__ == "__main__":
    main()
