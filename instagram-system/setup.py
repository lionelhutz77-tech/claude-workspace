"""
Setup-Script: Prüft ob alle benötigten Tools installiert sind.
Ausführen mit: python setup.py
"""

import subprocess
import sys


def check(name, cmd):
    try:
        subprocess.run(cmd, capture_output=True, check=True)
        print(f"  ✓ {name}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print(f"  ✗ {name} — NICHT gefunden")
        return False


print("=== System-Check ===\n")

# Python Pakete
try:
    from google import genai
    print("  ✓ google-genai")
except ImportError:
    print("  ✗ google-genai — führe aus: pip install google-genai")

try:
    import requests
    print("  ✓ requests")
except ImportError:
    print("  ✗ requests — führe aus: pip install requests")

# FFmpeg
ffmpeg_ok = check("FFmpeg", ["ffmpeg", "-version"])

# API Key
try:
    sys.path.insert(0, ".")
    from config.settings import GEMINI_API_KEY
    if GEMINI_API_KEY:
        print(f"  ✓ Gemini API Key ({GEMINI_API_KEY[:8]}...)")
    else:
        print("  ✗ Gemini API Key — leer in config/settings.py")
except Exception as e:
    print(f"  ✗ config/settings.py — {e}")

print()
if not ffmpeg_ok:
    print("FFmpeg installieren:")
    print("  Option 1 (empfohlen): winget install ffmpeg")
    print("  Option 2: https://ffmpeg.org/download.html#build-windows")
    print()

print("=== Fertig ===")
