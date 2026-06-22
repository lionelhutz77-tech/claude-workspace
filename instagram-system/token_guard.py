"""
Token Guard — läuft täglich automatisch über die Windows-Aufgabenplanung.

Logik:
- Restlaufzeit > 30 Tage:  nichts tun, nur loggen.
- Restlaufzeit <= 30 Tage: Token automatisch verlängern (refresh_token.py).
                           Bei Erfolg: kurzes Info-Popup (schliesst sich selbst).
- Restlaufzeit <= 5 Tage:  taeglich ein Warn-Popup (bleibt offen bis geklickt),
                           falls die Verlaengerung weiterhin fehlschlaegt.

Manueller Testlauf: python token_guard.py
Log: output/token_guard.log
"""

import json
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))

import os
from config.settings import ACCOUNT  # laedt auch die .env
from refresh_token import refresh_token

LOG_FILE = BASE / "output" / "token_guard.log"
STATE_FILE = BASE / "output" / "token_guard_state.json"
REFRESH_AT_DAYS_LEFT = 30   # ab dieser Restlaufzeit automatisch verlaengern
WARN_AT_DAYS_LEFT = 5       # ab dieser Restlaufzeit taeglich warnen


def log(msg: str):
    LOG_FILE.parent.mkdir(exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now():%Y-%m-%d %H:%M} | {msg}\n")


def popup(text: str, title: str, sticky: bool = False):
    """Windows-Popup. sticky=True bleibt offen, sonst schliesst es nach 20s."""
    timeout = 0 if sticky else 20
    ps = (
        f"(New-Object -ComObject WScript.Shell)"
        f".Popup('{text}', {timeout}, '{title}', 48)"
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps],
        capture_output=True,
    )


def already_warned_today() -> bool:
    if not STATE_FILE.exists():
        return False
    try:
        state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return state.get("last_warn") == str(date.today())
    except (json.JSONDecodeError, OSError):
        return False


def remember_warned_today():
    STATE_FILE.parent.mkdir(exist_ok=True)
    STATE_FILE.write_text(
        json.dumps({"last_warn": str(date.today())}), encoding="utf-8"
    )


def main():
    expires_str = os.environ.get("IG_TOKEN_EXPIRES", "")
    if not ACCOUNT["access_token"] or not expires_str:
        log("FEHLER: Kein Token oder kein Ablaufdatum in .env.")
        popup(
            "Instagram-Setup unvollstaendig: Token oder Ablaufdatum fehlt in .env. "
            "Bitte check_access.py ausfuehren.",
            "Instagram Token Guard", sticky=True,
        )
        return

    days_left = (date.fromisoformat(expires_str) - date.today()).days
    log(f"Token gueltig bis {expires_str} ({days_left} Tage uebrig).")

    if days_left > REFRESH_AT_DAYS_LEFT:
        return  # alles gut, nichts zu tun

    # Verlaengerung faellig — automatisch versuchen
    if refresh_token():
        new_expiry = os.environ.get("IG_TOKEN_EXPIRES", "?")
        log(f"Automatisch verlaengert. Neues Ablaufdatum: {new_expiry}.")
        popup(
            f"Instagram-Token automatisch verlaengert. Gueltig bis {new_expiry}.",
            "Instagram Token Guard",
        )
        return

    log("Verlaengerung FEHLGESCHLAGEN.")

    if days_left <= WARN_AT_DAYS_LEFT and not already_warned_today():
        popup(
            f"ACHTUNG: Instagram-Token laeuft in {days_left} Tagen ab und die "
            "automatische Verlaengerung schlaegt fehl! "
            "Bitte im Meta-Dashboard einen neuen Token generieren und "
            "check_access.py ausfuehren (siehe SETUP.md).",
            "Instagram Token Guard", sticky=True,
        )
        remember_warned_today()


if __name__ == "__main__":
    main()
