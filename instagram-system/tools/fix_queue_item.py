# -*- coding: utf-8 -*-
"""
Generiert gezielt einzelne (fehlerhafte) Bilder eines Warteschlangen-Karussells
neu und baut Slides + Reel neu. Postet NICHT (Claude prueft danach redaktionell).

  python -m tools.fix_queue_item <item_dir> <img_id1> <img_id2> ...
  Beispiel: python -m tools.fix_queue_item output/queue/item_02 hook p0_oben p0_unten cta
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.carousel_builder import build_from_spec
from tools.carousel_to_reel import build_reel

LOG = Path("output/fix_queue.log")


def log(msg):
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')}  {msg}"
    print(line)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def main():
    if len(sys.argv) < 3:
        print("Aufruf: python -m tools.fix_queue_item <item_dir> <img_id> [<img_id> ...]")
        sys.exit(1)
    base = Path(sys.argv[1])
    img_ids = sys.argv[2:]

    # Die zu ersetzenden Rohbilder loeschen -> build_from_spec generiert genau diese neu
    for iid in img_ids:
        f = base / "raw" / f"{iid}.png"
        if f.exists():
            f.unlink()
            log(f"geloescht (Neu-Generierung): {f.name}")

    spec = json.load(open(base / "spec.json", encoding="utf-8"))
    log(f"Starte Korrektur {base.name}: {spec['thema']} ({len(img_ids)} Bilder)")
    try:
        build_from_spec(spec, base, stil="nostalgie")   # regeneriert nur fehlende + rendert alle Slides
        build_reel(base / "slides", base / "reel.mp4")
        log(f"FERTIG: {base.name} neu gebaut. Claude muss jetzt redaktionell pruefen.")
    except Exception as e:
        log(f"FEHLER (evtl. FLUX noch erschoepft): {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
