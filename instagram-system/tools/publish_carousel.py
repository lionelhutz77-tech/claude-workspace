# -*- coding: utf-8 -*-
"""
Veröffentlicht ein Bild-Karussell auf Instagram (Graph API, Instagram Login).

Ablauf (3 Schritte laut Instagram-Doku):
  1. Pro Bild einen Child-Container anlegen (is_carousel_item=true)
  2. Einen CAROUSEL-Container mit allen Children + Caption anlegen
  3. Auf FINISHED warten, dann media_publish

Die Slide-Bilder müssen öffentlich erreichbar sein (hier: GitHub raw-URLs).

Ausführen: python -m tools.publish_carousel  (aus instagram-system/)
"""

import re
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

API = "https://graph.instagram.com/v21.0"
REPO_RAW = "https://raw.githubusercontent.com/lionelhutz77-tech/ig-media/main"
SLIDE_COUNT = 7


def _account():
    env = (Path(__file__).parent.parent / ".env").read_text(encoding="utf-8")
    def g(k):
        m = re.search(rf"{k}=(\S+)", env)
        return m.group(1) if m else None
    tok = g("IG_ACCESS_TOKEN") or g("ACCESS_TOKEN") or g("IG_TOKEN")
    uid = g("IG_USER_ID") or g("INSTAGRAM_USER_ID")
    if not tok or not uid:
        from config.settings import ACCOUNT
        tok = tok or ACCOUNT["access_token"]
        uid = uid or ACCOUNT["instagram_user_id"]
    return uid, tok


def publish_carousel(image_urls, caption):
    uid, token = _account()

    # 1. Child-Container
    children = []
    for i, url in enumerate(image_urls, 1):
        r = requests.post(f"{API}/{uid}/media", data={
            "image_url": url,
            "is_carousel_item": "true",
            "access_token": token,
        }, timeout=60)
        r.raise_for_status()
        cid = r.json()["id"]
        children.append(cid)
        print(f"  Slide {i}/{len(image_urls)} -> Container {cid}")

    # 2. Carousel-Container
    r = requests.post(f"{API}/{uid}/media", data={
        "media_type": "CAROUSEL",
        "children": ",".join(children),
        "caption": caption,
        "access_token": token,
    }, timeout=60)
    r.raise_for_status()
    carousel_id = r.json()["id"]
    print(f"  Karussell-Container: {carousel_id}")

    # 3. Auf FINISHED warten
    for _ in range(18):
        time.sleep(5)
        s = requests.get(f"{API}/{carousel_id}", params={
            "fields": "status_code", "access_token": token}, timeout=30)
        status = s.json().get("status_code")
        print(f"  Status: {status}")
        if status == "FINISHED":
            break
        if status == "ERROR":
            return {"success": False, "error": "Container-Verarbeitung fehlgeschlagen"}

    # 4. Veröffentlichen
    p = requests.post(f"{API}/{uid}/media_publish", data={
        "creation_id": carousel_id, "access_token": token}, timeout=60)
    p.raise_for_status()
    post_id = p.json()["id"]
    print(f"  VERÖFFENTLICHT! Post-ID: {post_id}")
    return {"success": True, "post_id": post_id}


def main():
    caption = Path("output/media/carousel_001/caption.txt").read_text(encoding="utf-8").strip()
    urls = [f"{REPO_RAW}/slide_{i:02d}.jpg" for i in range(1, SLIDE_COUNT + 1)]
    print(f"Veröffentliche Karussell mit {len(urls)} Slides...")
    result = publish_carousel(urls, caption)
    print("\nErgebnis:", result)


if __name__ == "__main__":
    main()
