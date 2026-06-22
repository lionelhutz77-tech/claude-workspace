# -*- coding: utf-8 -*-
"""
Tages-Pipeline @kiai1977: erzeugt und veroeffentlicht automatisch EIN
"Frueher & Heute"-Karussell.

  python daily_pipeline.py --dry            # nur bauen (Freigabe-Modus, morgens)
  python daily_pipeline.py --publish-today  # heute Gebautes posten (nach Freigabe)
  python daily_pipeline.py                  # bauen + sofort posten (Vollautomatik)
  python daily_pipeline.py --thema "Spontane Verabredungen"   # Thema vorgeben

Ablauf: Thema (Groq) -> Bilder (FLUX) -> Slides -> GitHub-Upload -> Post -> Aufraeumen.
"""

import argparse
import json
import sys
import time
import traceback
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from tools.theme_generator import generate_spec, build_caption
from tools.carousel_builder import build_from_spec
from tools.carousel_to_reel import build_reel
from tools.video_host import upload_video, delete_video
from tools.publish_carousel import publish_carousel, _account
from agents.publisher import upload_reel

LOG = Path("output/daily_pipeline.log")


def log(msg):
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')}  {msg}"
    print(line)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def run(dry=False, thema=None):
    tag = date.today().isoformat()
    base = Path(f"output/media/daily_{tag}")
    base.mkdir(parents=True, exist_ok=True)
    log(f"=== Tages-Pipeline {tag} (dry={dry}) ===")

    # 1. Thema + Bauplan
    spec = generate_spec(thema_override=thema)
    log(f"Thema: {spec['thema']}")
    json.dump(spec, open(base / "spec.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    # 2. Slides bauen
    slides = build_from_spec(spec, base, stil="nostalgie")
    log(f"{len(slides)} Slides gebaut: {base/'slides'}")

    # 2b. Reel aus den Slides bauen (Reichweiten-Hebel)
    try:
        reel = build_reel(base / "slides", base / "reel.mp4")
        log(f"Reel gebaut: {reel}")
    except Exception as e:
        log(f"WARN Reel-Bau fehlgeschlagen: {e}")

    if dry:
        log("DRY-RUN: nicht veroeffentlicht.")
        return {"status": "dry", "slides": [str(s) for s in slides], "spec": spec}

    # 3. Slides hochladen (eindeutige Namen)
    remote_names, urls = [], []
    for i, s in enumerate(slides, 1):
        name = f"daily_{tag}_{i:02d}.jpg"
        # ueberschreiben vermeiden: vorher loeschen falls vorhanden
        try:
            delete_video(name)
        except Exception:
            pass
        urls.append(upload_video(str(s), name))
        remote_names.append(name)
    log(f"{len(urls)} Slides hochgeladen.")

    # 4. Caption (einheitliche Struktur)
    caption = build_caption(spec)

    # 5. Veroeffentlichen
    try:
        result = publish_carousel(urls, caption)
        log(f"Veroeffentlicht: {result}")
    finally:
        for name in remote_names:
            try:
                delete_video(name)
            except Exception as e:
                log(f"WARN Aufraeumen {name}: {e}")
    return result


def publish_folder(base: Path):
    """Veroeffentlicht das in <base> gebaute Karussell (slides/ + spec.json)."""
    base = Path(base)
    slides = sorted((base / "slides").glob("slide_*.jpg"))
    spec_file = base / "spec.json"
    if not slides or not spec_file.exists():
        log(f"FEHLER: Kein gebautes Karussell in {base}.")
        sys.exit(1)
    spec = json.load(open(spec_file, encoding="utf-8"))
    log(f"Veroeffentliche Karussell aus {base.name}: {spec['thema']}")

    stamp = f"{base.name}_{int(time.time())}"
    remote_names, urls = [], []
    for i, s in enumerate(slides, 1):
        name = f"{stamp}_{i:02d}.jpg"
        urls.append(upload_video(str(s), name))
        remote_names.append(name)

    caption = build_caption(spec)
    try:
        result = publish_carousel(urls, caption)
        log(f"Veroeffentlicht: {result}")
    finally:
        for name in remote_names:
            try:
                delete_video(name)
            except Exception as e:
                log(f"WARN Aufraeumen {name}: {e}")
    # In der Warteschlange als veroeffentlicht markieren
    done = base / "PUBLISHED.txt"
    done.write_text(f"{time.strftime('%Y-%m-%d %H:%M')} {result}", encoding="utf-8")
    return result


def publish_today():
    """Veroeffentlicht das HEUTE gebaute Karussell, sonst das naechste aus der Schlange."""
    tag = date.today().isoformat()
    base = Path(f"output/media/daily_{tag}")
    if (base / "spec.json").exists():
        return publish_folder(base)
    # Fallback: naechstes offenes Element aus der Warteschlange
    nxt = next_queue_item()
    if not nxt:
        log("FEHLER: Weder Tages-Build noch Warteschlangen-Element vorhanden.")
        sys.exit(1)
    return publish_folder(nxt)


def next_queue_item():
    """Gibt den naechsten noch nicht veroeffentlichten Warteschlangen-Ordner zurueck."""
    qdir = Path("output/queue")
    if not qdir.exists():
        return None
    for item in sorted(qdir.glob("item_*")):
        if (item / "spec.json").exists() and not (item / "PUBLISHED.txt").exists():
            return item
    return None


def next_approved_item():
    """Naechstes FREIGEGEBENES (APPROVED.txt), noch nicht gepostetes Karussell."""
    qdir = Path("output/queue")
    if not qdir.exists():
        return None
    for item in sorted(qdir.glob("item_*")):
        if ((item / "spec.json").exists() and (item / "APPROVED.txt").exists()
                and not (item / "PUBLISHED.txt").exists()):
            return item
    return None


def publish_reel_today():
    """Veroeffentlicht das HEUTE gebaute Reel (Reichweiten-Hebel)."""
    tag = date.today().isoformat()
    base = Path(f"output/media/daily_{tag}")
    reel = base / "reel.mp4"
    spec_file = base / "spec.json"
    if not reel.exists() or not spec_file.exists():
        log(f"FEHLER: Kein gebautes Reel fuer {tag}.")
        sys.exit(1)
    spec = json.load(open(spec_file, encoding="utf-8"))
    uid, token = _account()
    name = f"reel_{tag}.mp4"
    try:
        delete_video(name)
    except Exception:
        pass
    url = upload_video(str(reel), name)
    # Reel-Caption: einheitliche Struktur + Pflicht-Musiknachweis (CC-BY)
    from agents.media_producer import MUSIC_ATTRIBUTION
    caption = build_caption(spec) + "\n" + MUSIC_ATTRIBUTION
    try:
        result = upload_reel(url, caption, {"instagram_user_id": uid,
                                            "access_token": token})
        log(f"Reel veroeffentlicht: {result}")
    finally:
        try:
            delete_video(name)
        except Exception as e:
            log(f"WARN Aufraeumen {name}: {e}")
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="nur bauen, nicht posten")
    ap.add_argument("--publish-today", action="store_true",
                    help="heute Gebautes Karussell posten (nach Freigabe)")
    ap.add_argument("--publish-reel-today", action="store_true",
                    help="heute Gebautes Reel posten (Reichweiten-Hebel)")
    ap.add_argument("--publish-queue", action="store_true",
                    help="naechstes Karussell aus der Warteschlange posten")
    ap.add_argument("--publish-approved", action="store_true",
                    help="naechstes FREIGEGEBENES Karussell posten (fuer Auto-Post 18:00)")
    ap.add_argument("--thema", default=None, help="Thema vorgeben")
    args = ap.parse_args()
    try:
        if args.publish_today:
            publish_today()
        elif args.publish_reel_today:
            publish_reel_today()
        elif args.publish_approved:
            nxt = next_approved_item()
            if not nxt:
                log("Kein freigegebenes Karussell im Vorrat - heute kein Auto-Post.")
                return
            publish_folder(nxt)
        elif args.publish_queue:
            nxt = next_queue_item()
            if not nxt:
                log("Warteschlange leer - nichts zu posten.")
                sys.exit(1)
            publish_folder(nxt)
        else:
            run(dry=args.dry, thema=args.thema)
    except Exception:
        log("FEHLER:\n" + traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
