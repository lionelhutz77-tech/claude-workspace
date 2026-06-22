# -*- coding: utf-8 -*-
"""
Rendert die Reel-Slides mit Text-Overlays (Pillow):
  1. Titel-Slide        (1845-Bild + Titel/Jahr)
  2. Zutaten-Slide      (Flatlay + Einkaufsliste)
  3+ Schritt-Slides     (modernes Bild abgedunkelt + Kurzschritte)
  letzte: Finale        (modernes Gericht + "Guten Appetit" + KI-Hinweis)

Ausführen: python -m tools.recipe_slides  (aus instagram-system/)
"""

import json
import sys
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 1920
FONT = "C:/Windows/Fonts/arialbd.ttf"
FONT_REG = "C:/Windows/Fonts/arial.ttf"


def load_font(size, bold=True):
    return ImageFont.truetype(FONT if bold else FONT_REG, size)


def clean(text):
    """Ersetzt Zeichen, die Arial nicht darstellen kann (Kästchen-Glyphen)."""
    return (text.replace("‑", "-")   # non-breaking hyphen
                .replace("–", "-")
                .replace(" ", " "))


def darken(img, factor=0.45):
    """Dunkelt das Bild ab, damit Text lesbar ist."""
    overlay = Image.new("RGB", img.size, (0, 0, 0))
    return Image.blend(img, overlay, factor)


def draw_centered(draw, text, y, font, fill=(255, 255, 255), max_width=W - 120):
    """Zeichnet Text zentriert mit Zeilenumbruch; gibt neues y zurück."""
    text = clean(text)
    avg = font.getbbox("Mm")[2] / 2
    wrap = max(10, int(max_width / avg * 1.9))
    for line in textwrap.wrap(text, width=wrap):
        bbox = draw.textbbox((0, 0), line, font=font)
        lw = bbox[2] - bbox[0]
        draw.text(((W - lw) / 2, y), line, font=font, fill=fill)
        y += (bbox[3] - bbox[1]) + 18
    return y


def slide_titel(rezept, base_img, out):
    img = darken(Image.open(base_img).resize((W, H)), 0.35)
    d = ImageDraw.Draw(img)
    y = 480
    y = draw_centered(d, "REZEPT AUS DEM JAHR", y, load_font(54), (230, 200, 140))
    y = draw_centered(d, str(rezept["jahr_original"]), y + 10, load_font(170), (230, 200, 140))
    y = draw_centered(d, rezept["titel_original"], y + 60, load_font(72))
    y = draw_centered(d, "— neu interpretiert —", y + 40, load_font(48, bold=False), (200, 200, 200))
    y = draw_centered(d, f"für 2 Personen · {rezept['zeit_minuten']} Min.", y + 30,
                      load_font(44, bold=False), (200, 200, 200))
    img.save(out, quality=92)


def slide_zutaten(rezept, base_img, out):
    img = darken(Image.open(base_img).resize((W, H)), 0.55)
    d = ImageDraw.Draw(img)
    y = 260
    y = draw_centered(d, "EINKAUFSLISTE", y, load_font(76), (230, 200, 140))
    y += 50
    f = load_font(46, bold=False)
    for item in rezept["einkaufsliste"]:
        y = draw_centered(d, "• " + item, y, f) + 14
    y += 40
    y = draw_centered(d, "+ Vorrat: Salz, Pfeffer, Mehl, 2 Eier", y,
                      load_font(40, bold=False), (190, 190, 190))
    img.save(out, quality=92)


def slide_schritte(rezept, base_img, out_prefix):
    """Teilt die Kurzschritte auf 2 Slides auf."""
    steps = rezept.get("schritte_kurz") or rezept["schritte"]
    half = (len(steps) + 1) // 2
    paths = []
    for idx, chunk in enumerate([steps[:half], steps[half:]]):
        if not chunk:
            continue
        img = darken(Image.open(base_img).resize((W, H)), 0.6)
        d = ImageDraw.Draw(img)
        y = 300
        y = draw_centered(d, f"SO GEHT'S ({idx+1}/2)", y, load_font(70), (230, 200, 140))
        y += 60
        f = load_font(48, bold=False)
        for i, s in enumerate(chunk):
            nr = idx * half + i + 1
            y = draw_centered(d, f"{nr}. {s}", y, f) + 36
        p = Path(f"{out_prefix}_{idx+1}.jpg")
        img.save(p, quality=92)
        paths.append(p)
    return paths


def slide_finale(rezept, base_img, out):
    img = Image.open(base_img).resize((W, H))
    # Unteres Drittel mit dunklem Verlauf hinterlegen, damit der Text lesbar ist
    grad = Image.new("L", (1, H), 0)
    for yy in range(H):
        grad.putpixel((0, yy), min(200, max(0, int((yy - 1150) / (H - 1150) * 220))))
    black = Image.new("RGB", (W, H), (0, 0, 0))
    img = Image.composite(black, img, grad.resize((W, H)))
    d = ImageDraw.Draw(img)
    y = 1380
    y = draw_centered(d, "Guten Appetit!", y, load_font(96))
    y = draw_centered(d, "Ganzes Rezept in der Caption", y + 30, load_font(44, bold=False),
                      (220, 220, 220))
    y = draw_centered(d, "Erstellt mit KI", y + 40, load_font(38, bold=False), (180, 180, 180))
    img.save(out, quality=92)


def main():
    rezept = json.load(open("output/rezept_001_modern.json", encoding="utf-8"))
    media = Path("output/media/rezept_001")
    slides = Path("output/media/rezept_001/slides")
    slides.mkdir(exist_ok=True)

    img_1845 = media / "01_original_1845.jpg"
    img_modern = media / "02_modern.jpg"
    img_zutaten = media / "03_zutaten.jpg"

    print("Rendere Slides...")
    slide_titel(rezept, img_1845, slides / "s1_titel.jpg")
    slide_zutaten(rezept, img_zutaten, slides / "s2_zutaten.jpg")
    step_paths = slide_schritte(rezept, img_modern, slides / "s3_schritte")
    slide_finale(rezept, img_modern, slides / "s9_finale.jpg")

    all_slides = [slides / "s1_titel.jpg", slides / "s2_zutaten.jpg",
                  *step_paths, slides / "s9_finale.jpg"]
    print(f"Fertig: {len(all_slides)} Slides in {slides}")
    for s in all_slides:
        print(f"  - {s.name}")


if __name__ == "__main__":
    main()
