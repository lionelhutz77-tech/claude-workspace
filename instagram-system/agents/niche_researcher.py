"""
Niche Researcher Agent
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.gemini_client import generate_with_retry, extract_json


SYSTEM_PROMPT = """You are an Instagram niche research specialist identifying
emerging, underserved niches perfect for music-only visual content (no speech needed),
currently growing, not yet saturated, producible with AI-generated visuals."""


def research_niches(client, num_niches: int = 5) -> list[dict]:
    prompt = f"""{SYSTEM_PROMPT}

Identify {num_niches} emerging Instagram niches for music-only visual Reels in 2025-2026.

Return ONLY a valid JSON array. Each object must have:
niche_name, description, why_underserved, visual_style,
music_mood, competition_level, content_ideas (array of 3 strings)"""

    text = generate_with_retry(client, prompt)
    return extract_json(text)


def select_best_niche(client, niches: list[dict]) -> dict:
    prompt = f"""Select the single best niche from this list for an AI-run
Instagram account posting music-only visual Reels. Criteria: highest growth
potential, least saturated, best for AI video generation.

Niches: {json.dumps(niches, indent=2)}

Return ONLY a valid JSON object with key "account_niche" containing
the chosen niche object plus a "selection_reason" field."""

    text = generate_with_retry(client, prompt)
    return extract_json(text)


if __name__ == "__main__":
    from tools.gemini_client import get_client
    client = get_client()

    print("Recherchiere Nischen...")
    niches = research_niches(client)
    print(f"Gefunden: {len(niches)} Nischen.")
    selection = select_best_niche(client, niches)

    print("\n=== AUSGEWÄHLTE NISCHE ===")
    print(json.dumps(selection.get("account_niche", {}), indent=2, ensure_ascii=False))

    Path("../output").mkdir(exist_ok=True)
    with open("../output/niche_selection.json", "w") as f:
        json.dump(selection, f, indent=2, ensure_ascii=False)
    print("\nGespeichert: output/niche_selection.json")
