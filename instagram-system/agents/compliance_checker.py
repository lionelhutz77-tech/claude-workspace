"""
Compliance Checker Agent
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.gemini_client import generate_with_retry, extract_json


RULES = """
- Instagram: No inauthentic behavior, no misleading content, no harassment
- EU AI Act: AI-generated content must be clearly disclosed
- Ethics: No manipulation, no false promises, respectful to all groups
- Policy: Every post must contain "🤖 KI-generiert / AI-generated" in caption
"""


def check_compliance(client, brief: dict) -> dict:
    prompt = f"""Review this Instagram Reels brief for compliance.

Rules: {RULES}

Brief: {json.dumps(brief, indent=2)}

Return ONLY a valid JSON object with:
approved (true/false), risk_level ("low"/"medium"/"high"),
issues (array), required_changes (array), notes (string)"""

    text = generate_with_retry(client, prompt)
    return extract_json(text)


def check_all_briefs(client, briefs: list[dict], label: str = "Account") -> tuple[list, list]:
    approved, rejected = [], []
    for brief in briefs:
        result = check_compliance(client, brief)
        brief["compliance"] = result
        if result.get("approved"):
            approved.append(brief)
        else:
            print(f"  ABGELEHNT '{brief.get('title', '?')}': {result.get('issues', [])}")
            rejected.append(brief)
    print(f"  {len(approved)}/{len(briefs)} Briefs genehmigt ({label})")
    return approved, rejected


if __name__ == "__main__":
    from tools.gemini_client import get_client
    client = get_client()

    briefs_file = Path("../output/briefs.json")
    if not briefs_file.exists():
        print("Zuerst content_ideator.py ausführen.")
        exit(1)

    with open(briefs_file) as f:
        briefs = json.load(f)

    print(f"Prüfe {len(briefs)} Briefs...")
    approved, rejected = check_all_briefs(client, briefs)

    with open("../output/approved.json", "w") as f:
        json.dump(approved, f, indent=2, ensure_ascii=False)
    with open("../output/rejected.json", "w") as f:
        json.dump(rejected, f, indent=2, ensure_ascii=False)
    print("Fertig.")
