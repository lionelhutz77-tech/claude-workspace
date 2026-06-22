# -*- coding: utf-8 -*-
"""
Baut einen Vorrat von N Karussells (+ Reels) in die Warteschlange
output/queue/item_NN/ — zum Vorausschauen und spaeteren Freigeben.

  python -m tools.build_queue 3      # 3 Karussells auf Vorrat bauen
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.theme_generator import generate_spec
from tools.carousel_builder import build_from_spec
from tools.carousel_to_reel import build_reel

QUEUE = Path("output/queue")


def _next_index():
    QUEUE.mkdir(parents=True, exist_ok=True)
    existing = [int(p.name.split("_")[1]) for p in QUEUE.glob("item_*") if p.name.split("_")[1].isdigit()]
    return (max(existing) + 1) if existing else 1


def build_n(n=3):
    built = []
    for k in range(n):
        idx = _next_index()
        base = QUEUE / f"item_{idx:02d}"
        base.mkdir(parents=True, exist_ok=True)
        print(f"\n=== Vorrat {k+1}/{n} -> {base.name} ===")
        spec = generate_spec()
        json.dump(spec, open(base / "spec.json", "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
        print(f"Thema: {spec['thema']}")
        build_from_spec(spec, base, stil="nostalgie")
        try:
            build_reel(base / "slides", base / "reel.mp4")
        except Exception as e:
            print(f"WARN Reel: {e}")
        built.append((base, spec["thema"]))
    print("\nFERTIG. Warteschlange:")
    for base, thema in built:
        print(f"  {base.name}: {thema}")
    return built


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    build_n(n)


if __name__ == "__main__":
    main()
