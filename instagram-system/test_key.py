"""Schneller Test ob der Groq API Key funktioniert."""
import sys
sys.path.insert(0, ".")
from config.settings import GROQ_API_KEY

print(f"Key geladen: {GROQ_API_KEY[:10]}..." if GROQ_API_KEY else "FEHLER: Key ist leer!")

try:
    from groq import Groq
    client = Groq(api_key=GROQ_API_KEY)
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": "Say hello in one word."}],
        max_tokens=10,
    )
    print(f"API Antwort: {response.choices[0].message.content}")
    print("KEY FUNKTIONIERT!")
except Exception as e:
    print(f"FEHLER: {e}")
