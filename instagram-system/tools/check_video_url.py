"""
Video-URL-Diagnose
Prüft, ob Instagram ein Video von einer öffentlichen URL akzeptiert,
OHNE etwas zu posten: Es wird nur ein Media-Container erstellt und dessen
Verarbeitung beobachtet. Nicht veröffentlichte Container verfallen nach 24h
von selbst und erscheinen nie auf dem Profil.

Ausführen mit: python tools/check_video_url.py <VIDEO_URL>
"""

import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import ACCOUNT

GRAPH_API_BASE = "https://graph.instagram.com/v21.0"


def check_video_url(video_url: str) -> bool:
    user_id = ACCOUNT["instagram_user_id"]
    token = ACCOUNT["access_token"]

    print(f"Erstelle Test-Container (wird NICHT veroeffentlicht) ...")
    r = requests.post(f"{GRAPH_API_BASE}/{user_id}/media", data={
        "media_type": "REELS",
        "video_url": video_url,
        "caption": "URL-Test (wird nie veroeffentlicht)",
        "access_token": token,
    })
    if not r.ok:
        err = r.json().get("error", {}).get("message", r.text)
        print(f"FEHLER beim Container erstellen: {err}")
        return False

    container_id = r.json()["id"]
    print(f"Container {container_id} erstellt. Warte auf Instagrams Verarbeitung ...")

    for i in range(18):  # max ~3 Minuten
        time.sleep(10)
        s = requests.get(f"{GRAPH_API_BASE}/{container_id}", params={
            "fields": "status_code,status",
            "access_token": token,
        }).json()
        code = s.get("status_code", "?")
        print(f"  [{(i + 1) * 10:3d}s] Status: {code}")
        if code == "FINISHED":
            print("\n[OK] Instagram hat das Video von dieser URL akzeptiert und verarbeitet.")
            print("(Der Container wird nicht veroeffentlicht und verfaellt nach 24h.)")
            return True
        if code == "ERROR":
            print(f"\nFEHLGESCHLAGEN — Detail: {s.get('status', 'keine Angabe')}")
            return False

    print("\nTIMEOUT — Verarbeitung dauert ungewoehnlich lange.")
    return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Aufruf: python tools/check_video_url.py <VIDEO_URL>")
        sys.exit(1)
    sys.exit(0 if check_video_url(sys.argv[1]) else 1)
