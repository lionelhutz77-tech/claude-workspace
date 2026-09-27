"""Zentrale, kostenbewusste Groq-Modellwahl.

Modellnamen bleiben über Umgebungsvariablen austauschbar. So müssen Agenten
bei Provider-Änderungen nicht einzeln umprogrammiert werden.
"""

from __future__ import annotations

import os


ROUTINE_MODEL_DEFAULT = "openai/gpt-oss-20b"
DEEP_MODEL_DEFAULT = "openai/gpt-oss-120b"


def groq_model(tier: str = "routine") -> str:
    """Liefert einen zentral konfigurierten Modellnamen für den Aufgabentyp."""

    normalized = tier.strip().lower()
    if normalized == "routine":
        return os.environ.get("GROQ_MODEL_ROUTINE", ROUTINE_MODEL_DEFAULT).strip()
    if normalized == "deep":
        return os.environ.get("GROQ_MODEL_DEEP", DEEP_MODEL_DEFAULT).strip()
    raise ValueError(f"Unbekannte Groq-Modellstufe: {tier}")


def groq_reasoning_effort(tier: str = "routine") -> str:
    """Begrenzt Reasoning-Tokens: low für Routine, medium für tiefe Synthese."""

    normalized = tier.strip().lower()
    if normalized == "routine":
        return os.environ.get("GROQ_REASONING_ROUTINE", "low").strip()
    if normalized == "deep":
        return os.environ.get("GROQ_REASONING_DEEP", "medium").strip()
    raise ValueError(f"Unbekannte Groq-Modellstufe: {tier}")
