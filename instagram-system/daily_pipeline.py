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
import re
import sys
import time
import traceback
from datetime import date, datetime, timezone
from pathlib import Path

import requests

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


# ---------------------------------------------------------------------------
# Doppelpost-Schutz: Die lokale PUBLISHED.txt ist unzuverlaessig, weil
# media_publish gelegentlich 403 zurueckgibt, OBWOHL der Post live geht.
# Darum pruefen wir die ECHTE Account-Lage (Graph API) als Quelle der Wahrheit.
# ---------------------------------------------------------------------------

def _caption_sig(text: str) -> str:
    """Distinktive, normalisierte Signatur einer Caption (ohne den allen
    gemeinsamen 'Weisst du noch? Frueher'-Prefix)."""
    t = re.sub(r"[^a-zäöüß0-9 ]", "", (text or "").lower()).strip()
    if t.startswith("weißt du noch") or t.startswith("weisst du noch"):
        return t[22:62].strip()
    return t[:40].strip()


def _account_captions(limit: int = 25):
    """Holt die letzten Account-Captions + Zeitstempel. Gibt (sigs, neueste_ts)
    zurueck oder (None, None), wenn die API nicht erreichbar ist."""
    try:
        uid, token = _account()
        url = f"https://graph.instagram.com/v21.0/{uid}/media"
        r = requests.get(url, params={
            "fields": "caption,timestamp", "limit": limit,
            "access_token": token}, timeout=30)
        r.raise_for_status()
        data = r.json().get("data", [])
        sigs = [_caption_sig(m.get("caption", "")) for m in data if m.get("caption")]
        neueste = data[0].get("timestamp") if data else None
        return sigs, neueste
    except Exception as e:
        log(f"WARN Account-Abgleich nicht moeglich: {e}")
        return None, None


def _ist_live(sig: str, account_sigs) -> bool:
    """True, wenn die Signatur bereits in den Account-Captions auftaucht."""
    if not sig or not account_sigs:
        return False
    kern = sig[:28]
    return any(kern and kern in a for a in account_sigs)


def _stunden_seit(ts_iso: str):
    """Stunden seit einem ISO-Zeitstempel (UTC) der Graph API."""
    if not ts_iso:
        return None
    try:
        dt = datetime.strptime(ts_iso[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - dt).total_seconds() / 3600.0
    except Exception:
        return None


def _markiere_published(base: Path, info) -> None:
    (base / "PUBLISHED.txt").write_text(
        f"{time.strftime('%Y-%m-%d %H:%M')} {info}", encoding="utf-8")


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
    """Veroeffentlicht das in <base> gebaute Karussell (slides/ + spec.json).
    Idempotent: prueft vor UND nach dem Posten die echte Account-Lage, damit
    der 403-trotz-Live-Quirk keine Doppelposts mehr erzeugt."""
    base = Path(base)
    slides = sorted((base / "slides").glob("slide_*.jpg"))
    spec_file = base / "spec.json"
    if not slides or not spec_file.exists():
        log(f"FEHLER: Kein gebautes Karussell in {base}.")
        sys.exit(1)
    spec = json.load(open(spec_file, encoding="utf-8"))
    caption = build_caption(spec)
    sig = _caption_sig(caption)

    account_sigs, neueste_ts = _account_captions()

    # GUARD 1: Inhalt schon live? -> nur markieren, NICHT erneut posten.
    if _ist_live(sig, account_sigs):
        log(f"{base.name} ('{spec['thema']}') ist bereits live — uebersprungen (Doppelpost verhindert).")
        _markiere_published(base, "bereits live (Dedup-Guard)")
        return {"success": True, "skipped": "already_live"}

    # GUARD 2: heute schon gepostet? -> max. 1 Post/Tag.
    std = _stunden_seit(neueste_ts)
    if account_sigs is not None and std is not None and std < 12:
        log(f"Vor {std:.1f}h wurde bereits gepostet — uebersprungen (max 1/Tag).")
        return {"success": True, "skipped": "already_today"}

    log(f"Veroeffentliche Karussell aus {base.name}: {spec['thema']}")
    stamp = f"{base.name}_{int(time.time())}"
    remote_names, urls = [], []
    for i, s in enumerate(slides, 1):
        name = f"{stamp}_{i:02d}.jpg"
        urls.append(upload_video(str(s), name))
        remote_names.append(name)

    fehler = None
    try:
        result = publish_carousel(urls, caption)
        log(f"Veroeffentlicht: {result}")
    except Exception as e:
        fehler = e
        result = {"success": False, "error": str(e)}
        log(f"WARN publish_carousel meldete Fehler: {e}")
    finally:
        for name in remote_names:
            try:
                delete_video(name)
            except Exception as e:
                log(f"WARN Aufraeumen {name}: {e}")

    # GUARD 3: Bei (gemeldetem) Fehler nachpruefen, ob der Post TROTZDEM live ging
    # (403-trotz-Live-Quirk). Wenn ja -> als veroeffentlicht markieren, sonst echter Fehlschlag.
    if not result.get("success"):
        time.sleep(8)
        caps2, _ = _account_captions()
        if _ist_live(sig, caps2):
            log(f"{base.name} ging trotz API-Fehler live — als veroeffentlicht markiert.")
            result = {"success": True, "recovered_from_error": True}
        else:
            log(f"FEHLER: {base.name} wurde NICHT veroeffentlicht ({fehler}). Nicht markiert.")
            return result

    _markiere_published(base, result)
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
