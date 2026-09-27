"""Minimaler, secrets-freier Verfügbarkeitstest der zentralen Groq-Routen."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "agents"))

from llm_config import groq_model  # noqa: E402


def main() -> int:
    load_dotenv(ROOT / ".env")
    if not os.environ.get("GROQ_API_KEY"):
        print(json.dumps({"status": "blocked", "reason": "GROQ_API_KEY_missing"}))
        return 2
    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    results = []
    for tier in ("routine", "deep"):
        model = groq_model(tier)
        started = time.perf_counter()
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "Antworte exakt mit OK."}],
                temperature=0,
                max_tokens=64,
                reasoning_effort="low",
            )
            text = (response.choices[0].message.content or "").strip()
            results.append({
                "tier": tier,
                "model": model,
                "status": "ok" if text else "empty_output",
                "latency_ms": round((time.perf_counter() - started) * 1000),
            })
        except Exception as exc:
            results.append({
                "tier": tier,
                "model": model,
                "status": "error",
                "error_type": type(exc).__name__,
            })
    print(json.dumps({"status": "ok" if all(row["status"] == "ok" for row in results) else "failed", "results": results}))
    return 0 if all(row["status"] == "ok" for row in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
