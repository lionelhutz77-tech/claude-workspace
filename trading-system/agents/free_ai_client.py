"""Zentraler, begrenzter KI-Zugang fuer das Trading-System.

Nur der explizit gebaute Prompt wird an das gemeinsame Free-AI-Gateway gegeben.
Es gibt keinen stillen Wechsel zu einem anderen Anbieter. Aufrufer entscheiden
selbst, wie sie bei einem sichtbaren Fehler deterministisch weiterarbeiten.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path


GATEWAY_DIR = Path(__file__).resolve().parents[2] / "ai-gateway"
if str(GATEWAY_DIR) not in sys.path:
    sys.path.insert(0, str(GATEWAY_DIR))

from gateway import GatewayError, generate  # noqa: E402


def generate_text(
    system_prompt: str,
    user_prompt: str,
    *,
    task: str = "routine",
    max_tokens: int = 400,
    retries: int = 3,
) -> str:
    """Erzeugt begrenzten Text; wiederholt nur explizite Rate-Limit-Fehler."""

    prompt = f"SYSTEM:\n{system_prompt.strip()}\n\nAUFGABE:\n{user_prompt.strip()}"
    output_chars = max(192, min(6000, int(max_tokens) * 3))
    for attempt in range(retries):
        try:
            result = generate(
                prompt,
                task=task,
                sensitivity="project",
                max_output_chars=output_chars,
            )
            text = str(result.get("text", "")).strip()
            if not text:
                if attempt < retries - 1:
                    time.sleep(1)
                    continue
                raise GatewayError("Free-AI-Gateway returned empty output.")
            return text
        except GatewayError as exc:
            if "429" not in str(exc) or attempt >= retries - 1:
                raise
            wait_seconds = 30 * (attempt + 1)
            print(f" [Rate-Limit, warte {wait_seconds}s]", end="", flush=True)
            time.sleep(wait_seconds)
    raise GatewayError("Free-AI-Gateway failed without a result.")
