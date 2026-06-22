# -*- coding: utf-8 -*-
"""
Baut aus den Rezept-Bildern + Musik das fertige Instagram-Reel (MP4).
Nutzt die bestehenden Funktionen aus agents/media_producer.py.

Ausführen: python -m tools.recipe_reel  (aus instagram-system/)
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from agents.media_producer import download_music, create_reel, MUSIC_ATTRIBUTION


def main():
    media_dir = Path("output/media/rezept_001")
    slides_dir = media_dir / "slides"

    # Slide-Reihenfolge mit Lesezeit: Titel -> Einkaufsliste -> Schritte -> Finale
    ordered = [slides_dir / "s1_titel.jpg",
               slides_dir / "s2_zutaten.jpg",
               slides_dir / "s3_schritte_1.jpg",
               slides_dir / "s3_schritte_2.jpg",
               slides_dir / "s9_finale.jpg"]
    missing = [p for p in ordered if not p.exists()]
    if missing:
        print(f"FEHLER: Slides fehlen: {[p.name for p in missing]}")
        print("Zuerst ausführen: python -m tools.recipe_slides")
        sys.exit(1)

    music_path = media_dir / "music.mp3"
    if not music_path.exists():
        if not download_music("calm", music_path):
            print("FEHLER: Musik-Download fehlgeschlagen.")
            sys.exit(1)

    video_path = media_dir / "reel_rezept_001.mp4"
    # 5 Slides x 7s = 35s, genug Zeit zum Mitlesen der Zutaten/Schritte
    if create_reel(ordered, music_path, video_path, duration=35):
        rezept = json.load(open("output/rezept_001_modern.json", encoding="utf-8"))
        queue_entry = {
            "title": rezept["titel_modern"],
            "caption": rezept["instagram_caption"] + "\n\n" + MUSIC_ATTRIBUTION,
            "video_file": str(video_path),
            "status": "ready",
        }
        qf = Path("output/publish_queue.json")
        queue = json.load(open(qf, encoding="utf-8")) if qf.exists() else []
        queue.append(queue_entry)
        json.dump(queue, open(qf, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        print(f"\nFERTIG: {video_path}")
        print("In Publish-Queue eingetragen.")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
