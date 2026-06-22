"""
Instagram Access Token Generator (FALLBACK)
Holt per OAuth-Flow einen langlebigen Access Token (60 Tage gültig).

HINWEIS: Der einfachere Hauptweg ist der Token-Generator im Meta-Dashboard
(siehe SETUP.md) + check_access.py. Dieses Skript nur nutzen, falls der
Dashboard-Weg nicht funktioniert. Voraussetzung: REDIRECT_URI muss in der
Meta-App unter Business-Login-Einstellungen exakt so eingetragen sein.

Ausführen mit: python get_token.py
"""

import http.server
import threading
import webbrowser
import urllib.parse
import requests
import sys

sys.path.insert(0, ".")
from config.settings import APP_ID, APP_SECRET, save_env_value

REDIRECT_URI = "http://localhost:8888/callback"
SCOPES = "instagram_business_basic,instagram_business_content_publish,instagram_manage_comments"

# ─── OAuth Server ─────────────────────────────────────────────────────────────
auth_code = None

class CallbackHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if "code" in params:
            auth_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h1>Erfolg! Du kannst dieses Fenster schliessen.</h1>")
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"<h1>Fehler: Kein Code erhalten.</h1>")

    def log_message(self, format, *args):
        pass  # Stille Logs


def get_token():
    if not APP_ID or not APP_SECRET:
        print("FEHLER: Trage APP_ID und APP_SECRET in get_token.py ein.")
        print("Diese findest du in der Facebook Developer App unter:")
        print("  Anwendungsfälle → Anpassen → Instagram-App-ID / Instagram-App-Geheimcode")
        sys.exit(1)

    # 1. Lokalen Server starten
    server = http.server.HTTPServer(("localhost", 8888), CallbackHandler)
    thread = threading.Thread(target=server.handle_request)
    thread.start()

    # 2. Browser öffnen für Instagram Login
    auth_url = (
        f"https://www.instagram.com/oauth/authorize"
        f"?client_id={APP_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&scope={SCOPES}"
        f"&response_type=code"
    )
    print("Browser öffnet sich für Instagram Login...")
    print(f"Falls nicht: {auth_url}")
    webbrowser.open(auth_url)

    # 3. Warten auf Callback
    thread.join(timeout=120)
    server.server_close()

    if not auth_code:
        print("FEHLER: Kein Code erhalten. Timeout.")
        sys.exit(1)

    print("Code erhalten. Tausche gegen Token...")

    # 4. Code gegen kurzlebigen Token tauschen
    r = requests.post("https://api.instagram.com/oauth/access_token", data={
        "client_id": APP_ID,
        "client_secret": APP_SECRET,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI,
        "code": auth_code,
    })
    r.raise_for_status()
    short_token = r.json()["access_token"]
    user_id = r.json().get("user_id") or r.json().get("ig_user_id")
    print(f"Kurzlebiger Token erhalten. User ID: {user_id}")

    # 5. Gegen langlebigen Token tauschen (60 Tage)
    r2 = requests.get("https://graph.instagram.com/access_token", params={
        "grant_type": "ig_exchange_token",
        "client_secret": APP_SECRET,
        "access_token": short_token,
    })
    r2.raise_for_status()
    long_token = r2.json()["access_token"]
    print("Langlebiger Token erhalten (gültig 60 Tage)!")

    # 6. Instagram User ID holen
    r3 = requests.get("https://graph.instagram.com/me", params={
        "fields": "id,username",
        "access_token": long_token,
    })
    r3.raise_for_status()
    ig_id = r3.json()["id"]
    username = r3.json()["username"]
    print(f"Instagram Account: @{username} (ID: {ig_id})")

    # 7. In .env speichern
    save_env_value("IG_ACCESS_TOKEN", long_token)
    save_env_value("IG_USER_ID", ig_id)
    save_env_value("IG_USERNAME", username)

    print("\n=== FERTIG ===")
    print("Token und User ID wurden in .env gespeichert.")
    print("Zur Kontrolle: python check_access.py")


if __name__ == "__main__":
    get_token()
