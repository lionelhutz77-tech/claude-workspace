# -*- coding: utf-8 -*-
"""Beschriftet vorhandene Warteschlangen-Karussells neu (Tippfehler + Umbruch),
ohne die Bilder neu zu generieren."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.theme_generator import _normalize
from tools.carousel_builder import slide_voll, slide_paar


def rerender(base: Path):
    spec = json.load(open(base / "spec.json", encoding="utf-8"))
    _normalize(spec)
    json.dump(spec, open(base / "spec.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    raw = base / "raw"
    sl = base / "slides"
    slide_voll({"bild": "hook", "zeilen": spec["hook"]["zeilen"],
                "fusszeile": "Wische weiter  >>"}, raw, sl / "slide_01.jpg")
    for i, p in enumerate(spec["paare"]):
        slide_paar({"oben": (f"p{i}_oben", p["oben_text"]),
                    "unten": (f"p{i}_unten", p["unten_text"])},
                   raw, sl / f"slide_{i+2:02d}.jpg")
    n = len(spec["paare"]) + 2
    slide_voll({"bild": "cta", "zeilen": spec["cta"]["zeilen"],
                "fusszeile": None}, raw, sl / f"slide_{n:02d}.jpg")
    print(f"{base.name}: neu gerendert ({spec['thema']})")


if __name__ == "__main__":
    targets = sys.argv[1:] or [str(p) for p in sorted(Path("output/queue").glob("item_*"))]
    for t in targets:
        rerender(Path(t))
