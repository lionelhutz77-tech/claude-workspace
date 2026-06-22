# -*- coding: utf-8 -*-
"""Liest Kommentare (inkl. Antworten) zu einem Beitrag."""
import re
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))
API = "https://graph.instagram.com/v21.0"


def account():
    env = (Path(__file__).parent.parent / ".env").read_text(encoding="utf-8")
    def g(k):
        m = re.search(rf"{k}=(\S+)", env)
        return m.group(1) if m else None
    tok = g("IG_ACCESS_TOKEN") or g("ACCESS_TOKEN") or g("IG_TOKEN")
    uid = g("IG_USER_ID") or g("INSTAGRAM_USER_ID")
    return uid, tok


def latest_media_id(uid, tok):
    r = requests.get(f"{API}/{uid}/media",
                     params={"fields": "id,timestamp", "access_token": tok}, timeout=30)
    return r.json()["data"][0]["id"]


def read_comments(mid, tok):
    fields = "id,text,username,timestamp,replies{id,text,username,timestamp}"
    r = requests.get(f"{API}/{mid}/comments",
                     params={"fields": fields, "access_token": tok}, timeout=30)
    return r.json()


if __name__ == "__main__":
    uid, tok = account()
    mid = sys.argv[1] if len(sys.argv) > 1 else latest_media_id(uid, tok)
    data = read_comments(mid, tok)
    for c in data.get("data", []):
        print(f"[{c.get('username')}] {c.get('text')}")
        for rep in c.get("replies", {}).get("data", []):
            print(f"    -> [{rep.get('username')}] {rep.get('text')}")
    if not data.get("data"):
        print("(keine Kommentare oder Fehler)", data)
