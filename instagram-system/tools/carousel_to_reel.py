# -*- coding: utf-8 -*-
"""
Macht aus den fertigen Karussell-Slides (1080x1350) ein hochformatiges
Reel (1080x1920) mit sanftem Ken-Burns-Zoom + Musik.

Zweck: Reichweiten-Hebel. Karussells erreichen kaum Fremde, Reels schon —
das Reel zieht Besucher aufs Profil, das Karussell macht daraus Follower.

  python -m tools.carousel_to_reel <slides_dir> [out.mp4]
  (ohne Argument: nimmt das heute gebaute Tages-Karussell)
"""

import subprocess
import sys
from datetime import date
from pathlib import Path

from PIL import Image, ImageFilter

sys.path.insert(0, str(Path(__file__).parent.parent))
from agents.media_producer import download_music

W, H, FPS = 1080, 1920, 25


def frame_9x16(slide_path: Path, out_path: Path):
    """Legt eine 4:5-Slide mittig auf einen 9:16-Rahmen mit unscharfem
    Hintergrund (gefuellt aus der Slide selbst)."""
    slide = Image.open(slide_path).convert("RGB")
    bg = slide.resize((W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(40))
    bg = Image.blend(bg, Image.new("RGB", (W, H), (0, 0, 0)), 0.35)
    sw = W
    sh = int(slide.height * W / slide.width)
    fg = slide.resize((sw, sh), Image.LANCZOS)
    bg.paste(fg, (0, (H - sh) // 2))
    bg.save(out_path, quality=92)


def make_clip(img: Path, dur: float, zoom_in: bool, out: Path):
    frames = int(dur * FPS)
    if zoom_in:
        z = f"min(1+0.08*on/{frames},1.08)"
    else:
        z = f"max(1.08-0.08*on/{frames},1.0)"
    vf = (f"scale={W*2}:{H*2},zoompan=z='{z}':x='iw/2-(iw/zoom/2)':"
          f"y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps={FPS}")
    cmd = ["ffmpeg", "-y", "-loop", "1", "-i", str(img), "-vf", vf, "-t", str(dur),
           "-c:v", "libx264", "-preset", "fast", "-crf", "21", "-pix_fmt", "yuv420p",
           str(out)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg: {r.stderr[-300:]}")


def build_reel(slides_dir: Path, out_path: Path):
    slides = sorted(slides_dir.glob("slide_*.jpg"))
    if len(slides) < 4:
        raise RuntimeError(f"Zu wenige Slides in {slides_dir}")

    # Auswahl: Hook, zwei/drei Kontrastpaare, CTA
    chosen = [slides[0], slides[1], slides[2 if len(slides) > 4 else 1],
              slides[3] if len(slides) > 4 else slides[-2], slides[-1]]
    # Mehr Lesezeit: Hook/CTA 4,5 s, Kontrastpaare 5,5 s (zwei Textzeilen)
    durations = [4.5, 5.5, 5.5, 5.5, 4.5]

    work = slides_dir.parent / "reel_work"
    work.mkdir(exist_ok=True)
    clips = []
    for i, (slide, dur) in enumerate(zip(chosen, durations)):
        frame = work / f"frame_{i}.jpg"
        frame_9x16(slide, frame)
        clip = work / f"clip_{i}.mp4"
        make_clip(frame, dur, zoom_in=(i % 2 == 0), out=clip)
        clips.append(clip)

    filelist = work / "list.txt"
    filelist.write_text("".join(f"file '{c.absolute()}'\n" for c in clips))
    silent = work / "silent.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i",
                    str(filelist), "-c", "copy", str(silent)],
                   capture_output=True, text=True, check=True)

    music = slides_dir.parent / "music.mp3"
    if not music.exists():
        download_music("calm", music)

    subprocess.run(["ffmpeg", "-y", "-i", str(silent), "-i", str(music),
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-shortest",
                    str(out_path)], capture_output=True, text=True, check=True)
    return out_path


def main():
    if len(sys.argv) > 1:
        slides_dir = Path(sys.argv[1])
    else:
        tag = date.today().isoformat()
        slides_dir = Path(f"output/media/daily_{tag}/slides")
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else slides_dir.parent / "reel.mp4"
    print(f"Baue Reel aus {slides_dir} ...")
    result = build_reel(slides_dir, out)
    print(f"FERTIG: {result}")


if __name__ == "__main__":
    main()
