# -*- coding: utf-8 -*-
"""
Verdichtet die Rezeptschritte zu kurzen Video-Schritten (max. 8 Wörter)
und speichert sie als 'schritte_kurz' im Rezept-JSON.

Ausführen: python -m tools.recipe_shortsteps  (aus instagram-system/)
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.gemini_client import get_client, generate_with_retry, extract_json

PROMPT = """Verdichte diese Kochschritte zu maximal 6 kurzen Video-Untertiteln.
Jeder Untertitel: max. 10 Wörter, Imperativ, deutsch, für ein Instagram-Reel.
Fasse zusammen, wo möglich. Die wichtigsten Mengen/Zeiten beibehalten.

Schritte:
{schritte}

Antworte NUR mit JSON: {{"schritte_kurz": ["...", "..."]}}"""


def main():
    p = Path("output/rezept_001_modern.json")
    rezept = json.load(open(p, encoding="utf-8"))

    client = get_client()
    prompt = PROMPT.format(schritte="\n".join(
        f"{i+1}. {s}" for i, s in enumerate(rezept["schritte"])))
    result = extract_json(generate_with_retry(client, prompt))

    rezept["schritte_kurz"] = result["schritte_kurz"]
    json.dump(rezept, open(p, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print("Kurzschritte gespeichert:")
    for s in rezept["schritte_kurz"]:
        print(f"  - {s}")


if __name__ == "__main__":
    main()
