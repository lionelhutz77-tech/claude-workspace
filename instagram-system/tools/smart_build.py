# -*- coding: utf-8 -*-
"""
Kluges Nachproduzieren: Baut NUR dann ein neues Karussell, wenn der Vorrat
unter den Zielwert faellt. So bleibt immer etwas zum Pruefen/Posten da, ohne
FLUX-Budget zu verschwenden, wenn der Vorrat schon voll ist.

Laeuft morgens (frisches FLUX-Budget). Gebaute Karussells sind ENTWUERFE
(ohne APPROVED.txt) — der User prueft und gibt frei, erst dann Auto-Post 18:00.

  python -m tools.smart_build        # baut 1, falls Vorrat < Ziel
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

TARGET = 3   # so viele unveroeffentlichte Karussells im Vorrat halten
LOG = Path("output/smart_build.log")


def log(msg):
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')}  {msg}"
    print(line)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def pending_count():
    qdir = Path("output/queue")
    if not qdir.exists():
        return 0
    return sum(1 for it in qdir.glob("item_*")
               if (it / "spec.json").exists() and not (it / "PUBLISHED.txt").exists())


def main():
    n = pending_count()
    if n >= TARGET:
        log(f"Vorrat ausreichend ({n}/{TARGET}) - kein Neubau noetig.")
        return
    log(f"Vorrat niedrig ({n}/{TARGET}) - baue 1 neues Karussell (Entwurf).")
    try:
        from tools.build_queue import build_n
        built = build_n(1)
        for base, thema in built:
            log(f"Entwurf gebaut: {base.name} - {thema} (wartet auf Freigabe)")
    except Exception as e:
        log(f"FEHLER beim Bauen: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
