# -*- coding: utf-8 -*-
"""Markiert ein Karussell als FREIGEGEBEN (APPROVED.txt) -> darf um 18:00
automatisch gepostet werden. Aufruf: python -m tools.approve output/queue/item_05"""
import sys
import time
from pathlib import Path

for d in sys.argv[1:]:
    base = Path(d)
    if not (base / "spec.json").exists():
        print(f"FEHLER: {base} hat keine spec.json")
        continue
    (base / "APPROVED.txt").write_text(
        f"Freigegeben am {time.strftime('%Y-%m-%d %H:%M')}\n", encoding="utf-8")
    print(f"Freigegeben: {base.name}")
