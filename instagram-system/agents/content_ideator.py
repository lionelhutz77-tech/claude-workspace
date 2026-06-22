"""
Content Ideator Agent
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.gemini_client import generate_with_retry, extract_json


def generate_content_briefs(client, niche: dict, num_briefs: int = 7) -> list[dict]:
    prompt = f"""Create {num_briefs} Instagram Reels briefs for this niche:
{json.dumps(niche, indent=2)}

Rules: music-only (no speech), engaging 2-second hook, 15-30 seconds, loops well,
AI disclosure in caption.

Return ONLY a valid JSON array. Each object must have:
brief_id, title, hook_description, visual_sequence (array of 3 shots),
music_mood, music_tempo, color_palette, emotional_arc,
caption_text (with "🤖 KI-generiert / AI-generated" + hashtags), duration_seconds"""

    text = generate_with_retry(client, prompt)
    return extract_json(text)


if __name__ == "__main__":
    from tools.gemini_client import get_client
    client = get_client()

    niche_file = Path("../output/niche_selection.json")
    if not niche_file.exists():
        print("Zuerst niche_researcher.py ausführen.")
        exit(1)

    with open(niche_file) as f:
        selection = json.load(f)

    niche = selection.get("account_niche", {})
    print(f"Erstelle Briefs für: {niche.get('niche_name', '')}...")
    briefs = generate_content_briefs(client, niche)
    print(f"Erstellt: {len(briefs)} Briefs.")

    out = Path("../output/briefs.json")
    with open(out, "w") as f:
        json.dump(briefs, f, indent=2, ensure_ascii=False)
    print(f"Gespeichert: {out}")
