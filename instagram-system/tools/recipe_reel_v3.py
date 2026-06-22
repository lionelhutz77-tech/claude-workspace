# -*- coding: utf-8 -*-
"""
Baut das dynamische Rezept-Reel v3 (Template: vorlagen/template_dynamisch.json):
- 8 Shots im Dark-Food-Look (aus tools/recipe_images_v3.py)
- Ken-Burns-Effekt (langsamer Zoom rein/raus im Wechsel) per FFmpeg zoompan
- Kurze Text-Overlays (Hook + 1-Zeiler pro Szene) per Pillow
- Musik + Caption in die Publish-Queue

Ausführen: python -m tools.recipe_reel_v3  (aus instagram-system/)
"""

import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).parent.parent))
from agents.media_producer import download_music, MUSIC_ATTRIBUTION
from tools.recipe_slides import load_font, clean

W, H = 1080, 1920
FPS = 25

# (datei, dauer_s, text_overlay oder None)
TIMELINE = [
    ("v3_01_hook.jpg",        3.0, "Dieses Rezept ist 180 Jahre alt"),
    ("v3_02_fleisch.jpg",     2.5, "400 g Rind von der Theke"),
    ("v3_03_gemuese.jpg",     2.5, "1 Bund Suppengrün"),
    ("v3_04_topf.jpg",        2.5, "90 Min. sanft köcheln"),
    ("v3_05_abschoepfen.jpg", 2.5, "Schaum abschöpfen = klare Brühe"),
    ("v3_06_sieben.jpg",      2.5, "Durchsieben & mit Eiweiß klären"),
    ("v3_07_sahne.jpg",       2.5, "200 ml Sahne einziehen"),
    ("v3_08_hero.jpg",        4.0, "Bouillon wie 1845 - Rezept in der Caption"),
]


def add_text(src: Path, text: str, dst: Path):
    """Legt eine Textzeile im Reel-Stil (weiß, fett, Outline) aufs Bild."""
    img = Image.open(src).convert("RGB").resize((W, H))
    d = ImageDraw.Draw(img)
    font = load_font(58)
    text = clean(text)
    bbox = d.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    # Falls zu breit: kleinere Schrift
    if tw > W - 100:
        font = load_font(44)
        bbox = d.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
    x, y = (W - tw) / 2, 1500
    # Outline
    for dx in (-3, 0, 3):
        for dy in (-3, 0, 3):
            d.text((x + dx, y + dy), text, font=font, fill=(0, 0, 0))
    d.text((x, y), text, font=font, fill=(255, 255, 255))
    img.save(dst, quality=92)


def make_clip(img: Path, dur: float, zoom_in: bool, out: Path):
    """Erzeugt einen Clip mit Ken-Burns-Zoom aus einem Standbild."""
    frames = int(dur * FPS)
    if zoom_in:
        zexpr = f"min(1+0.10*on/{frames},1.10)"
    else:
        zexpr = f"max(1.10-0.10*on/{frames},1.0)"
    vf = (f"scale={W*2}:{H*2},"
          f"zoompan=z='{zexpr}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
          f":d={frames}:s={W}x{H}:fps={FPS}")
    cmd = ["ffmpeg", "-y", "-loop", "1", "-i", str(img), "-vf", vf,
           "-t", str(dur), "-c:v", "libx264", "-preset", "fast", "-crf", "21",
           "-pix_fmt", "yuv420p", str(out)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  FFmpeg-Fehler bei {img.name}: {r.stderr[-300:]}")
        return False
    return True


def main():
    base = Path("output/media/rezept_001/v3")
    work = base / "clips"
    work.mkdir(exist_ok=True)

    missing = [f for f, _, _ in TIMELINE if not (base / f).exists()]
    if missing:
        print(f"FEHLER: Bilder fehlen: {missing}")
        print("Zuerst: python -m tools.recipe_images_v3")
        sys.exit(1)

    # 1. Text-Overlays + Clips
    clips = []
    for i, (fname, dur, text) in enumerate(TIMELINE):
        src = base / fname
        if text:
            txt_img = work / f"txt_{fname}"
            add_text(src, text, txt_img)
            src = txt_img
        clip = work / f"clip_{i:02d}.mp4"
        print(f"[{i+1}/{len(TIMELINE)}] {fname} ({dur}s, zoom {'rein' if i%2==0 else 'raus'})")
        if not make_clip(src, dur, zoom_in=(i % 2 == 0), out=clip):
            sys.exit(1)
        clips.append(clip)

    # 2. Clips zusammenfügen
    filelist = work / "filelist.txt"
    with open(filelist, "w") as f:
        for c in clips:
            f.write(f"file '{c.absolute()}'\n")

    silent = base / "reel_v3_silent.mp4"
    r = subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0",
                        "-i", str(filelist), "-c", "copy", str(silent)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(f"Concat-Fehler: {r.stderr[-300:]}")
        sys.exit(1)

    # 3. Musik drunter
    music = Path("output/media/rezept_001/music.mp3")
    if not music.exists():
        download_music("calm", music)

    final = base / "reel_rezept_001_v3.mp4"
    r = subprocess.run(["ffmpeg", "-y", "-i", str(silent), "-i", str(music),
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
                        "-shortest", str(final)], capture_output=True, text=True)
    if r.returncode != 0:
        print(f"Audio-Fehler: {r.stderr[-300:]}")
        sys.exit(1)

    # 4. Publish-Queue aktualisieren
    rezept = json.load(open("output/rezept_001_modern.json", encoding="utf-8"))
    queue = [{
        "title": rezept["titel_modern"],
        "caption": rezept["instagram_caption"] + "\n\n" + MUSIC_ATTRIBUTION,
        "video_file": str(final),
        "status": "ready",
    }]
    json.dump(queue, open("output/publish_queue.json", "w", encoding="utf-8"),
              indent=2, ensure_ascii=False)

    print(f"\nFERTIG: {final}")


if __name__ == "__main__":
    main()
