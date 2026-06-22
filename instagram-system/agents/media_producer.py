"""
Media Producer Agent
Erstellt automatisch Videos für Instagram Reels:
1. Bilder generieren via Pollinations.ai (kostenlos, kein API Key)
2. Musik herunterladen via Pixabay (kostenlos, kein API Key)
3. Video zusammenbauen via FFmpeg (kostenlos, lokal)
"""

import requests
import json
import time
import subprocess
import sys
import os
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).parent.parent))


# ─── BILD-GENERIERUNG ────────────────────────────────────────────────────────

def generate_image(prompt: str, output_path: Path, width: int = 1080, height: int = 1920) -> bool:
    """
    Generiert ein Bild via Pollinations.ai (kostenlos, kein Key nötig).
    Format: 1080x1920 = Instagram Reels Format (9:16)
    """
    encoded = quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded}?width={width}&height={height}&nologo=true"

    print(f"  Generiere Bild: {prompt[:50]}...")
    for attempt in range(3):
        try:
            r = requests.get(url, timeout=60)
            if r.status_code == 200:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, "wb") as f:
                    f.write(r.content)
                print(f"  Bild gespeichert: {output_path.name}")
                return True
        except Exception as e:
            print(f"  Versuch {attempt+1} fehlgeschlagen: {e}")
            time.sleep(5)
    return False


def generate_image_sequence(visual_shots: list[str], output_dir: Path) -> list[Path]:
    """Generiert mehrere Bilder für eine Bildsequenz."""
    images = []
    for i, shot in enumerate(visual_shots):
        out = output_dir / f"frame_{i:02d}.jpg"
        if generate_image(shot, out):
            images.append(out)
        time.sleep(2)  # Kurze Pause zwischen Anfragen
    return images


# ─── MUSIK ───────────────────────────────────────────────────────────────────

# Kevin MacLeod / incompetech.com — Lizenz CC BY 4.0.
# WICHTIG: Namensnennung in der Caption erforderlich:
#   "Music: Kevin MacLeod (incompetech.com), CC BY 4.0"
# (Die alten Pixabay-CDN-Links sind seit Juni 2026 tot.)
FREE_TRACKS = {
    "calm": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Fretless.mp3",
    "ambient": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Fretless.mp3",
    "uplifting": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Carefree.mp3",
    "energetic": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Carefree.mp3",
}

MUSIC_ATTRIBUTION = "🎵 Music: Kevin MacLeod (incompetech.com), CC BY 4.0"


def download_music(mood: str, output_path: Path) -> bool:
    """Liefert passende Hintergrundmusik (CC BY 4.0, Kevin MacLeod).
    Nutzt zuerst lokal gebündelte Tracks (assets/music/), damit nichts von
    einem externen Link abhängt; nur als Fallback wird heruntergeladen."""
    import shutil
    mood_lower = mood.lower()

    # 1. Lokal gebündelte Tracks bevorzugen (kein Netz-/Link-Risiko)
    assets = Path(__file__).parent.parent / "assets" / "music"
    local_key = "uplifting" if ("uplift" in mood_lower or "energet" in mood_lower) else "calm"
    local = assets / f"{local_key}.mp3"
    if local.exists():
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(local, output_path)
        print(f"  Musik (lokal, CC BY): {local.name}")
        return True


    # Passenden Track suchen
    track_url = None
    for key in FREE_TRACKS:
        if key in mood_lower:
            track_url = FREE_TRACKS[key]
            break
    if not track_url:
        track_url = FREE_TRACKS["ambient"]  # Fallback

    print(f"  Lade Musik herunter (Mood: {mood})...")
    try:
        r = requests.get(track_url, timeout=120, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code == 200:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(r.content)
            print(f"  Musik gespeichert: {output_path.name}")
            return True
    except Exception as e:
        print(f"  Musik-Download fehlgeschlagen: {e}")
    return False


# ─── VIDEO ZUSAMMENBAUEN ─────────────────────────────────────────────────────

def check_ffmpeg() -> bool:
    """Prüft ob FFmpeg installiert ist."""
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def create_reel(images: list[Path], music_path: Path, output_path: Path,
                duration: int = 20) -> bool:
    """
    Kombiniert Bilder + Musik zu einem Instagram Reel (MP4).
    Jedes Bild wird gleich lang angezeigt.
    """
    if not check_ffmpeg():
        print("  FEHLER: FFmpeg nicht installiert.")
        print("  Download: https://ffmpeg.org/download.html")
        print("  Oder: winget install ffmpeg")
        return False

    if not images:
        print("  FEHLER: Keine Bilder vorhanden.")
        return False

    seconds_per_image = duration / len(images)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Bildliste für FFmpeg erstellen
    filelist = output_path.parent / "filelist.txt"
    with open(filelist, "w") as f:
        for img in images:
            f.write(f"file '{img.absolute()}'\n")
            f.write(f"duration {seconds_per_image}\n")
        # Letztes Bild nochmal (FFmpeg braucht das)
        f.write(f"file '{images[-1].absolute()}'\n")

    print(f"  Erstelle Video ({duration}s, {len(images)} Bilder)...")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", str(filelist),
        "-i", str(music_path),
        "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-t", str(duration),
        "-shortest",
        str(output_path)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    filelist.unlink(missing_ok=True)

    if result.returncode == 0:
        print(f"  Video gespeichert: {output_path.name}")
        return True
    else:
        print(f"  FFmpeg Fehler: {result.stderr[-300:]}")
        return False


# ─── HAUPTFUNKTION ───────────────────────────────────────────────────────────

def produce_reel(brief: dict, output_dir: Path) -> dict:
    """
    Produziert ein komplettes Reel aus einem Content Brief.
    Gibt Pfade zu den erstellten Dateien zurück.
    """
    brief_id = brief.get("brief_id", "unknown")
    title = brief.get("title", "untitled")
    shots = brief.get("visual_sequence", [brief.get("hook_description", "abstract visual")])
    mood = brief.get("music_mood", "ambient")
    duration = brief.get("duration_seconds", 20)

    work_dir = output_dir / f"reel_{brief_id}"
    work_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nProduziere: {title}")

    # 1. Bilder generieren
    images = generate_image_sequence(shots, work_dir / "frames")

    # 2. Musik herunterladen
    music_path = work_dir / "music.mp3"
    music_ok = download_music(mood, music_path)

    # 3. Video erstellen
    result = {
        "brief_id": brief_id,
        "title": title,
        "caption": brief.get("caption_text", ""),
        "images": [str(p) for p in images],
        "music": str(music_path) if music_ok else None,
        "video": None,
        "status": "failed"
    }

    if images and music_ok:
        video_path = work_dir / f"reel_{brief_id}.mp4"
        if create_reel(images, music_path, video_path, duration):
            result["video"] = str(video_path)
            result["status"] = "ready"

    return result


if __name__ == "__main__":
    # Test mit einem einzelnen Brief
    approved_file = Path("../output/approved.json")
    if not approved_file.exists():
        print("Zuerst run_pipeline.py --step compliance ausführen.")
        exit(1)

    with open(approved_file) as f:
        approved = json.load(f)

    if not approved:
        print("Keine genehmigten Briefs gefunden.")
        exit(1)

    # Ersten genehmigten Brief produzieren
    brief = approved[0]
    output_dir = Path("../output/videos")
    result = produce_reel(brief, output_dir)

    print(f"\nErgebnis: {result['status']}")
    if result["video"]:
        print(f"Video: {result['video']}")

    # Ergebnis speichern
    queue_file = Path("../output/publish_queue.json")
    queue = []
    if queue_file.exists():
        with open(queue_file) as f:
            queue = json.load(f)
    queue.append(result)
    with open(queue_file, "w") as f:
        json.dump(queue, f, indent=2, ensure_ascii=False)
    print(f"In Publish-Queue gespeichert.")
