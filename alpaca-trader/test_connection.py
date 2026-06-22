# -*- coding: utf-8 -*-
"""
Verbindungstest fuer das Alpaca-Paper-Konto.
Liest die Keys aus .env und fragt den Kontostand ab.
Gibt KEINE Secrets aus.
"""
import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

KEY = os.getenv("ALPACA_API_KEY", "")
SECRET = os.getenv("ALPACA_SECRET_KEY", "")
PAPER = os.getenv("ALPACA_PAPER", "true").lower() == "true"

BASE = "https://paper-api.alpaca.markets" if PAPER else "https://api.alpaca.markets"

if not KEY or "HIER_" in KEY or not SECRET or "HIER_" in SECRET:
    print("FEHLER: In der .env stehen noch Platzhalter statt echter Keys.")
    sys.exit(1)

headers = {"APCA-API-KEY-ID": KEY, "APCA-API-SECRET-KEY": SECRET}

try:
    r = requests.get(f"{BASE}/v2/account", headers=headers, timeout=15)
except Exception as e:
    print(f"FEHLER: Keine Verbindung zu Alpaca ({e})")
    sys.exit(1)

if r.status_code == 403:
    print("FEHLER: Zugang abgelehnt (403). Keys falsch oder fuer Live statt Paper.")
    sys.exit(1)
if r.status_code != 200:
    print(f"FEHLER: HTTP {r.status_code} -> {r.text[:200]}")
    sys.exit(1)

a = r.json()
modus = "PAPER (Spielgeld)" if PAPER else "LIVE (echtes Geld!)"
print("=" * 48)
print(f"  VERBINDUNG OK  -  Modus: {modus}")
print("=" * 48)
print(f"  Konto-Nr.:        {a.get('account_number')}")
print(f"  Status:           {a.get('status')}")
print(f"  Waehrung:         {a.get('currency')}")
print(f"  Barbestand:       {float(a.get('cash', 0)):,.2f}")
print(f"  Portfolio-Wert:   {float(a.get('portfolio_value', 0)):,.2f}")
print(f"  Kaufkraft:        {float(a.get('buying_power', 0)):,.2f}")
print(f"  Handel gesperrt?: {a.get('trading_blocked')}")
print("=" * 48)
