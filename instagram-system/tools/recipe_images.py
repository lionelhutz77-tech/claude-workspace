# -*- coding: utf-8 -*-
"""
Erzeugt die Bilder für ein Rezept-Reel.

Primär:   Cloudflare Workers AI / FLUX.1 schnell (kostenlos, ~10k Neurons/Tag,
          deutlich realistischer — Account-Token in .env: CF_API_TOKEN)
Fallback: Stable Horde (kostenlos, anonym, langsam, ältere Modelle)
Pollinations.ai ist seit Juni 2026 kostenpflichtig (402) — nicht mehr nutzen.

FLUX liefert 1024x1024; das Bild wird auf 1080 Breite skaliert und auf
schwarzem 9:16-Hintergrund (1080x1920) zentriert — passt zum Dark-Food-Look.

Ausführen: python -m tools.recipe_images  (aus instagram-system/)
"""

import base64
import json
import re
import sys
import time
from pathlib import Path

import requests

CF_ACCOUNT_ID = "194cd867afb6b813f49633028da15987"


def _cf_token():
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        m = re.search(r"CF_API_TOKEN=(\S+)", env_file.read_text(encoding="utf-8"))
        if m:
            return m.group(1)
    return None


def generate_image_flux(prompt: str, out_path: Path) -> bool:
    """Generiert via Cloudflare Workers AI (FLUX.1 schnell) und bettet das
    quadratische Bild in einen schwarzen 1080x1920-Rahmen ein."""
    token = _cf_token()
    if not token:
        return False
    url = (f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}"
           f"/ai/run/@cf/black-forest-labs/flux-1-schnell")
    for attempt in range(3):
        try:
            r = requests.post(url, headers={"Authorization": f"Bearer {token}"},
                              json={"prompt": prompt, "steps": 8}, timeout=180)
            if r.status_code == 200:
                img_data = base64.b64decode(r.json()["result"]["image"])
                out_path.write_bytes(img_data)
                _to_reel_format(out_path)
                print(f"  OK (FLUX): {out_path.name} ({out_path.stat().st_size // 1024} KB)")
                return True
            print(f"  FLUX Versuch {attempt+1}: {r.status_code} {r.text[:150]}")
        except Exception as e:
            print(f"  FLUX Versuch {attempt+1}: {e}")
        time.sleep(10)
    return False


def _to_reel_format(path: Path):
    """Skaliert auf 1080 Breite und zentriert auf schwarzem 1080x1920-Grund."""
    from PIL import Image
    im = Image.open(path).convert("RGB")
    im = im.resize((1080, int(im.height * 1080 / im.width)), Image.LANCZOS)
    canvas = Image.new("RGB", (1080, 1920), (0, 0, 0))
    canvas.paste(im, (0, (1920 - im.height) // 2))
    canvas.save(path, quality=92)

API = "https://stablehorde.net/api/v2"
HEADERS = {"apikey": "0000000000", "Content-Type": "application/json"}
# 9:16, Vielfache von 64. Max 654x654=427k Pixel fuer anonyme Nutzer bei
# hoher Last (403 sonst) -> 448x832 = 373k Pixel bleibt darunter.
GEN_W, GEN_H = 448, 832
OUT_W, OUT_H = 1080, 1920     # Reel-Format


def generate_image(prompt: str, out_path: Path, seed: str = "42") -> bool:
    """Primär FLUX (Cloudflare), Fallback Stable Horde."""
    if generate_image_flux(prompt, out_path):
        return True
    print("  FLUX nicht verfügbar, weiche auf Stable Horde aus...")
    return generate_image_horde(prompt, out_path, seed)


def generate_image_horde(prompt: str, out_path: Path, seed: str = "42") -> bool:
    payload = {
        "prompt": prompt,
        "params": {
            "width": GEN_W, "height": GEN_H,
            "steps": 30, "cfg_scale": 7,
            "seed": seed,
            "sampler_name": "k_euler_a",
        },
        "models": [],  # leer = beliebiges verfügbares Modell (schnellste Queue)
        "nsfw": False,
    }
    # Einreichen mit Geduld: anonyme Slots (500) sind oft kurzzeitig voll (429)
    jid = None
    for attempt in range(10):
        r = requests.post(f"{API}/generate/async", headers=HEADERS, json=payload, timeout=60)
        if r.status_code == 202:
            jid = r.json()["id"]
            break
        if r.status_code == 429:
            print(f"  Horde ausgelastet (Versuch {attempt+1}/10), warte 90 s...")
            time.sleep(90)
            continue
        print(f"  FEHLER beim Einreichen: {r.status_code} {r.text[:200]}")
        return False
    if not jid:
        print("  FEHLER: Horde dauerhaft ausgelastet.")
        return False
    print(f"  Job {jid} eingereicht, warte...")

    for _ in range(90):  # max. 15 Minuten
        time.sleep(10)
        c = requests.get(f"{API}/generate/check/{jid}", timeout=30).json()
        if c.get("done"):
            break
        if c.get("faulted"):
            print("  FEHLER: Job fehlgeschlagen.")
            return False

    res = requests.get(f"{API}/generate/status/{jid}", timeout=30).json()
    gens = res.get("generations", [])
    if not gens:
        print("  FEHLER: Kein Bild erhalten (Timeout).")
        return False

    img_data = requests.get(gens[0]["img"], timeout=120).content
    out_path.write_bytes(img_data)

    # Auf Reel-Format hochskalieren
    try:
        from PIL import Image
        im = Image.open(out_path)
        im = im.resize((OUT_W, OUT_H), Image.LANCZOS)
        im.save(out_path, quality=92)
    except ImportError:
        print("  Hinweis: Pillow fehlt, Bild bleibt 576x1024 (pip install pillow)")

    print(f"  OK: {out_path.name} ({out_path.stat().st_size // 1024} KB)")
    return True


def main():
    rezept_file = Path("output/rezept_001_modern.json")
    if not rezept_file.exists():
        print("FEHLER: Erst agents/recipe_interpreter.py ausführen.")
        sys.exit(1)

    with open(rezept_file, encoding="utf-8") as f:
        rezept = json.load(f)

    media_dir = Path("output/media/rezept_001")
    media_dir.mkdir(parents=True, exist_ok=True)

    prompts = [
        ("Authentic 1845 German farmhouse kitchen, rustic wooden table, steaming "
         "cast iron pot of clear beef broth, antique ladle, candlelight, dark "
         "moody old master still life painting style, Biedermeier era, "
         "photorealistic, vertical composition", "01_original_1845.jpg", "1845"),
        ("Modern food photography, clear beef bouillon soup with root vegetables "
         "cream and green peas, elegant dish for two, bright natural daylight, "
         "minimalist white ceramic bowls, fresh parsley garnish, steam rising, "
         "shallow depth of field, professional food styling, vertical",
         "02_modern.jpg", "2026"),
        ("Ingredients flatlay for German beef broth, raw beef cut, soup vegetable "
         "bundle carrot leek celery parsley root, onion, cream cup, green peas, "
         "rustic wooden background, overhead shot, natural light, food "
         "photography, vertical", "03_zutaten.jpg", "99"),
    ]

    print(f"Generiere {len(prompts)} Bilder via Stable Horde...")
    ok = 0
    for prompt, fname, seed in prompts:
        print(f"\n[{fname}]")
        if generate_image(prompt, media_dir / fname, seed):
            ok += 1

    print(f"\nFertig: {ok}/{len(prompts)} Bilder in {media_dir}")


if __name__ == "__main__":
    main()
