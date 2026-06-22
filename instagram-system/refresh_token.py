"""
Token-Refresh
Verlängert den langlebigen Access Token um weitere 60 Tage.
Funktioniert, sobald der Token mindestens 24h alt ist.

Ausführen mit: python refresh_token.py
(Später automatisiert per Scheduler, z.B. alle 30 Tage.)
"""

import sys
from datetime import date, timedelta
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
from config.settings import ACCOUNT, save_env_value


def refresh_token() -> bool:
    token = ACCOUNT["access_token"]
    if not token:
        print("FEHLER: Kein Token in .env. Erst check_access.py durchlaufen.")
        return False

    r = requests.get("https://graph.instagram.com/refresh_access_token", params={
        "grant_type": "ig_refresh_token",
        "access_token": token,
    })
    if not r.ok:
        err = r.json().get("error", {}).get("message", r.text)
        print(f"FEHLER beim Refresh: {err}")
        print("Hinweis: Refresh geht erst, wenn der Token mindestens 24h alt ist.")
        return False

    data = r.json()
    new_token = data["access_token"]
    days_valid = data.get("expires_in", 0) // 86400 or 60
    new_expiry = date.today() + timedelta(days=days_valid)
    save_env_value("IG_ACCESS_TOKEN", new_token)
    save_env_value("IG_TOKEN_EXPIRES", str(new_expiry))
    print(f"[OK] Token verlaengert — gueltig bis {new_expiry}. In .env gespeichert.")
    return True


if __name__ == "__main__":
    sys.exit(0 if refresh_token() else 1)
