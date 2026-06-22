"""
AI Client - nutzt Groq (kostenlos, schnell, kein Kreditkarte nötig)
Modell: llama-3.3-70b-versatile
"""

import time
import sys
import os
from pathlib import Path


def get_client():
    """Lädt API Key und gibt einen Groq-Client zurück."""
    try:
        from groq import Groq
    except ImportError:
        print("FEHLER: Groq nicht installiert. Führe aus: pip install groq")
        sys.exit(1)

    api_key = os.environ.get("GROQ_API_KEY")

    if not api_key:
        try:
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from config.settings import GROQ_API_KEY
            api_key = GROQ_API_KEY
        except Exception:
            pass

    if not api_key:
        print("FEHLER: Kein Groq API Key gefunden.")
        print("Trage deinen Key in config/settings.py ein: GROQ_API_KEY = '...'")
        sys.exit(1)

    return Groq(api_key=api_key)


# Reihenfolge: bestes Modell zuerst. Groq-Rate-Limits gelten PRO Modell —
# bei Tageslimit (TPD) wird daher aufs nächste Modell ausgewichen.
MODEL_FALLBACKS = [
    "llama-3.3-70b-versatile",
    "openai/gpt-oss-120b",
    "llama-3.1-8b-instant",
]


def generate_with_retry(client, prompt: str, max_retries: int = 4, model: str = None) -> str:
    """Sendet eine Anfrage mit automatischer Wiederholung bei Rate-Limit.
    Bei Tageslimit weicht sie automatisch auf ein anderes Groq-Modell aus."""

    models = [model] if model else list(MODEL_FALLBACKS)
    model_idx = 0

    for attempt in range(max_retries):
        try:
            time.sleep(2)
            response = client.chat.completions.create(
                model=models[model_idx],
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=4000,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            err = str(e).lower()
            print(f"  Fehler (Versuch {attempt+1}, Modell {models[model_idx]}): {e}")
            if "rate" in err or "429" in err or "limit" in err:
                # Tageslimit ("per day"/TPD): Warten bringt nichts -> Modellwechsel
                if ("per day" in err or "tpd" in err) and model_idx + 1 < len(models):
                    model_idx += 1
                    print(f"  Tageslimit erreicht. Wechsle auf Modell: {models[model_idx]}")
                    continue
                wait = 30 * (attempt + 1)
                print(f"  Rate-Limit. Warte {wait} Sekunden...")
                time.sleep(wait)
            else:
                raise

    raise Exception("Max Wiederholungen erreicht.")


def extract_json(text: str):
    """Extrahiert JSON aus einem Antworttext."""
    import json
    text = text.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()
    return json.loads(text)
