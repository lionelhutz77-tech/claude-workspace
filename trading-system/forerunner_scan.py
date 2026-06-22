"""
Wöchentlicher Vorläufer-Scanner
Läuft montags via GitHub Actions und sucht nach Aktien mit frühem AMD/NVDA-Muster.
Kann auch manuell gestartet werden: python forerunner_scan.py
"""

import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "agents"))

from news_agent       import analysiere_nachrichten
from forerunner_agent import scanne_vorlaeufer, drucke_vorlaeufer_bericht
from telegram_agent   import sende_vorlaeufer_bericht

print("=" * 65)
print("  VORLÄUFER-SCANNER")
print("  Suche nach frühen AMD/NVDA-Mustern im Markt")
print("=" * 65)

# Aktuelle News laden (hilft beim Sentiment-Check)
print("\n  Lade aktuelle Nachrichten...")
try:
    nachrichten = analysiere_nachrichten(max_pro_quelle=10)
    print(f"  {len(nachrichten)} Artikel geladen.")
except Exception as e:
    print(f"  News-Fehler: {e} — fahre ohne News fort.")
    nachrichten = []

# Scanner ausführen
print()
ergebnisse = scanne_vorlaeufer(nachrichten=nachrichten)

# Konsolenausgabe
drucke_vorlaeufer_bericht(ergebnisse, top_n=5)

# Telegram-Report
print("\n  Sende Telegram-Bericht...")
if sende_vorlaeufer_bericht(ergebnisse, top_n=3):
    print("  Vorläufer-Bericht via Telegram gesendet.")
else:
    print("  Telegram nicht konfiguriert oder Fehler.")
