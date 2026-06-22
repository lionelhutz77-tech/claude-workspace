"""Test: kostenlose Bilderzeugung via Pollinations.ai (anonym, 1 Anfrage/IP)."""

import time
import urllib.parse
from pathlib import Path

import requests

OUT = Path(__file__).parent.parent / "output" / "media" / "pollinations_test.jpg"

prompt = urllib.parse.quote(
    "ancient roman bread loaf panis quadratus on rustic wooden table, photorealistic, warm light"
)
url = f"https://image.pollinations.ai/prompt/{prompt}?width=720&height=1280&nologo=true"

for attempt in range(4):
    if attempt:
        time.sleep(45)
    try:
        r = requests.get(url, timeout=180)
        ctype = r.headers.get("content-type", "")
        print(f"Versuch {attempt + 1}: Status {r.status_code} ({ctype})")
        if r.ok and "image" in ctype:
            OUT.write_bytes(r.content)
            print(f"ERFOLG: {len(r.content)} Bytes -> {OUT.name}")
            break
        print(f"  Antwort: {r.text[:200]}")
    except requests.RequestException as e:
        print(f"Versuch {attempt + 1}: {e}")
else:
    print("ALLE VERSUCHE FEHLGESCHLAGEN")
