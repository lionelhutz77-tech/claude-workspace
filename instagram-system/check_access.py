"""
Zugriffs-Check
Prüft, ob der Access Token funktioniert und alle nötigen Berechtigungen hat.

Ausführen mit: python check_access.py
Optional: python check_access.py <TOKEN>  — trägt einen neuen Token in .env ein und prüft ihn.
"""

import sys
from datetime import date, timedelta

import requests

sys.path.insert(0, ".")
from config.settings import ACCOUNT, save_env_value

GRAPH_API_BASE = "https://graph.instagram.com/v21.0"


def check_access(token: str, is_new_token: bool = False) -> bool:
    # 1. Identität prüfen
    r = requests.get(f"{GRAPH_API_BASE}/me", params={
        "fields": "id,username,account_type",
        "access_token": token,
    })
    if not r.ok:
        print(f"FEHLER bei /me: {r.status_code} — {r.json().get('error', {}).get('message', r.text)}")
        return False

    me = r.json()
    user_id = me["id"]
    print(f"[OK] Verbunden als @{me.get('username', '?')} (ID: {user_id}, Typ: {me.get('account_type', '?')})")

    # 2. Publish-Berechtigung prüfen (geht nur mit instagram_business_content_publish)
    r2 = requests.get(f"{GRAPH_API_BASE}/{user_id}/content_publishing_limit", params={
        "access_token": token,
    })
    if not r2.ok:
        print(f"FEHLER bei content_publishing_limit: {r2.json().get('error', {}).get('message', r2.text)}")
        print("-> Vermutlich fehlt die Berechtigung 'instagram_business_content_publish' am Token.")
        return False

    quota = r2.json().get("data", [{}])[0]
    used = quota.get("quota_usage", "?")
    print(f"[OK] Publish-Berechtigung aktiv. API-Posts in den letzten 24h: {used}/100")

    # 3. Daten in .env speichern
    save_env_value("IG_ACCESS_TOKEN", token)
    save_env_value("IG_USER_ID", user_id)
    save_env_value("IG_USERNAME", me.get("username", ""))
    if is_new_token:
        # Frisch generierte Tokens (Dashboard/OAuth) gelten 60 Tage
        save_env_value("IG_TOKEN_EXPIRES", str(date.today() + timedelta(days=60)))
    print("[OK] Token, User-ID und Username in .env gespeichert.")

    print("\n=== ZUGRIFF VOLLSTAENDIG EINGERICHTET ===")
    return True


if __name__ == "__main__":
    import os
    # Neuer Token: als Argument uebergeben ODER frisch in .env eingetragen
    # (erkennbar daran, dass noch kein Ablaufdatum gespeichert ist)
    if len(sys.argv) > 1:
        token, is_new = sys.argv[1], True
    else:
        token = ACCOUNT["access_token"]
        is_new = not os.environ.get("IG_TOKEN_EXPIRES")
    if not token:
        print("Kein Token vorhanden.")
        print("Entweder IG_ACCESS_TOKEN in .env eintragen oder aufrufen mit:")
        print("  python check_access.py <TOKEN>")
        sys.exit(1)
    sys.exit(0 if check_access(token, is_new) else 1)
