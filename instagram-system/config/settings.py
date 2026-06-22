"""
Central configuration for the Instagram automation system.
Secrets live in the .env file next to the project root (never committed).
"""

import os
from pathlib import Path

# ─── Mini .env loader (no extra dependency) ──────────────────────────────────
_ENV_FILE = Path(__file__).parent.parent / ".env"

def _load_env():
    if not _ENV_FILE.exists():
        return
    for line in _ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())

_load_env()


def save_env_value(key: str, value: str):
    """Update a single key in the .env file (used by token scripts)."""
    lines = _ENV_FILE.read_text(encoding="utf-8").splitlines()
    found = False
    for i, line in enumerate(lines):
        if line.strip().startswith(f"{key}="):
            lines[i] = f"{key}={value}"
            found = True
            break
    if not found:
        lines.append(f"{key}={value}")
    _ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.environ[key] = value


# ─── Meta Developer App ───────────────────────────────────────────────────────
APP_ID = os.environ.get("IG_APP_ID", "")
APP_SECRET = os.environ.get("IG_APP_SECRET", "")

# ─── Instagram Account ────────────────────────────────────────────────────────
ACCOUNT = {
    "username": os.environ.get("IG_USERNAME", ""),
    "access_token": os.environ.get("IG_ACCESS_TOKEN", ""),
    "instagram_user_id": os.environ.get("IG_USER_ID", ""),
}

# ─── LLM Provider ─────────────────────────────────────────────────────────────
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# Free video generation tools
VIDEO_TOOLS = {
    "kling_api_key": "",     # kling.ai — free tier
    "runway_api_key": "",    # runwayml.com — free tier
}

# Posting schedule
POST_SCHEDULE = {
    "posts_per_day": 1,
    "preferred_time_utc": "17:00",  # 6pm CET — peak engagement
}

# Compliance
AI_DISCLOSURE_TEXT = "🤖 This content was created by AI"
CONTENT_LANGUAGE_PRIMARY = "music-only"
CONTENT_LANGUAGE_FALLBACK = "de"
