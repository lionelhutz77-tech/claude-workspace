"""
Alle Emojis aus Scraper-Dateien entfernen (auch Unicode-Escapes)
"""

import re
from pathlib import Path

# Unicode-Codes für Emojis
emoji_patterns = {
    r"\U0001f4cd": "[PIN]",  # 📍
    r"\U0001f504": "[REFRESH]",  # 🔄
    r"\U00002705": "[OK]",  # ✅
    r"\U0001f914": "[THINK]",  # 🤔
    r"\U00002139": "[INFO]",  # ℹ️
    r"\U00002198": "[DATA]",  # ↘️
    r"\U0001f50d": "[SEARCH]",  # 🔍
    r"\U0001f57f": "[HAND]",  # 🕿
}

scraper_dir = Path("scrapers")

for scraper_file in scraper_dir.glob("*.py"):
    if scraper_file.name == "template.py":
        continue

    with open(scraper_file, "r", encoding="utf-8") as f:
        content = f.read()

    # Replace unicode emoji codes
    for emoji_code, replacement in emoji_patterns.items():
        content = re.sub(emoji_code, replacement, content)

    # Also replace visual emojis
    visual_map = {
        "🔄": "[REFRESH]",
        "✅": "[OK]",
        "❌": "[ERROR]",
        "⚠️": "[WARNING]",
        "🔗": "[LINK]",
        "📊": "[DATA]",
        "💾": "[SAVE]",
        "📋": "[INFO]",
        "📍": "[PIN]",
        "🤔": "[THINK]",
        "ℹ️": "[INFO]",
    }

    for visual, replacement in visual_map.items():
        content = content.replace(visual, replacement)

    with open(scraper_file, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"[OK] {scraper_file.name}")

print("[DONE] Alle Emojis (inkl. Unicode-Escapes) entfernt!")
