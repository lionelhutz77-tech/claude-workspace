# -*- coding: utf-8 -*-
"""Generiert NUR die Texte eines Karussells (keine Bilder) zur Freigabe."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.theme_generator import generate_spec

thema = sys.argv[1] if len(sys.argv) > 1 else None
s = generate_spec(thema_override=thema)
print("THEMA:", s["thema"])
print("\nHOOK:")
for z in s["hook"]["zeilen"]:
    if z:
        print("  ", z)
print("\n5 VERGLEICHE:")
for i, p in enumerate(s["paare"], 1):
    print(f"  {i}. FRUEHER: {p['oben_text']}")
    print(f"     HEUTE:   {p['unten_text']}")
    print(f"     (Bild frueher: {p['oben_prompt'][:70]}...)")
    print(f"     (Bild heute:   {p['unten_prompt'][:70]}...)")
print("\nCTA:")
for z in s["cta"]["zeilen"]:
    if z:
        print("  ", z)
print("\nCAPTION:")
print(" ", s["caption"])
# Spec fuer spaeteres Bauen ablegen (noch ohne Bilder)
import json
out = Path("output/preview_spec.json")
json.dump(s, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"\n(Text-Bauplan gespeichert: {out})")
