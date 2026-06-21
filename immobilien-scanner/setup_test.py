#!/usr/bin/env python
"""
Setup-Validierungs-Script
Prüft: Python-Version, Dependencies, .env, Groq-API, Mail-Config
"""

import sys
import os
from pathlib import Path

def check_python_version():
    """Python 3.8+ erforderlich"""
    if sys.version_info < (3, 8):
        print(f"❌ Python 3.8+ erforderlich, hast: {sys.version}")
        return False
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}")
    return True


def check_dependencies():
    """Installierte Packages prüfen"""
    required = [
        ("pyyaml", "yaml"),
        ("python-dotenv", "dotenv"),
        ("groq", "groq"),
        ("requests", "requests"),
        ("beautifulsoup4", "bs4"),
        ("playwright", "playwright"),
    ]

    all_ok = True
    for package, import_name in required:
        try:
            __import__(import_name)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} fehlt → pip install -r requirements.txt")
            all_ok = False

    return all_ok


def check_env_file():
    """Prüfe .env vorhanden und gefüllt"""
    env_path = Path(".env")

    if not env_path.exists():
        print("❌ .env nicht gefunden")
        print("   → cp .env.example .env")
        return False

    print("✅ .env existiert")

    # Prüfe kritische Keys
    with open(env_path) as f:
        env_content = f.read()

    critical_keys = ["GMX_USER", "GMX_APP_PASSWORD", "GROQ_API_KEY"]
    for key in critical_keys:
        if key not in env_content or f"{key}=your_" in env_content:
            print(f"❌ {key} in .env nicht gefüllt")
            return False
        print(f"✅ {key} vorhanden")

    return True


def check_groq_api():
    """Teste Groq-API-Verbindung"""
    try:
        from groq import Groq
        import os
        from dotenv import load_dotenv

        load_dotenv()
        api_key = os.getenv("GROQ_API_KEY")

        if not api_key or api_key.startswith("gsk_"):
            client = Groq(api_key=api_key)
            # Schneller Test-Call
            msg = client.messages.create(
                model="llama-3.3-70b-versatile",
                max_tokens=10,
                messages=[{"role": "user", "content": "test"}]
            )
            print("✅ Groq-API erreichbar")
            return True
        else:
            print("⚠️  GROQ_API_KEY sieht ungültig aus (sollte mit 'gsk_' starten)")
            return False

    except Exception as e:
        print(f"❌ Groq-API Fehler: {e}")
        return False


def check_config():
    """Prüfe config.yaml"""
    try:
        import yaml
        with open("config.yaml") as f:
            config = yaml.safe_load(f)

        if not config:
            print("❌ config.yaml ist leer oder ungültig")
            return False

        print("✅ config.yaml geladen")

        # Prüfe wichtige Keys
        if config["mail"]["to_email"] == "hutz.erkan@gmx.de":
            print("✅ E-Mail-Adresse korrekt")
        else:
            print(f"⚠️  E-Mail: {config['mail']['to_email']}")

        return True

    except Exception as e:
        print(f"❌ config.yaml Fehler: {e}")
        return False


def main():
    print("\n" + "=" * 60)
    print("🔍 IMMOBILIEN-SCANNER SETUP-CHECK")
    print("=" * 60 + "\n")

    checks = [
        ("Python Version", check_python_version),
        ("Dependencies", check_dependencies),
        ("config.yaml", check_config),
        (".env Secrets", check_env_file),
        ("Groq-API", check_groq_api),
    ]

    results = []
    for name, check_func in checks:
        print(f"\n▶️  {name}:")
        try:
            result = check_func()
            results.append(result)
        except Exception as e:
            print(f"❌ Fehler: {e}")
            results.append(False)

    print("\n" + "=" * 60)
    if all(results):
        print("✅ SETUP OK — Ready to run: python main.py")
    else:
        print("❌ Setup unvollständig — Siehe Fehler oben")
    print("=" * 60 + "\n")

    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
