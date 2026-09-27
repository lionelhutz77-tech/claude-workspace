"""Neutraler Live-Smoke-Test fuer die drei Trading-KI-Routen."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "agents"))

from free_ai_client import generate_text  # noqa: E402


def main() -> int:
    results = []
    for task in ("routine", "deep", "research"):
        started = time.perf_counter()
        try:
            text = generate_text(
                "Antworte exakt und ohne Erlaeuterung.",
                "Antworte exakt mit OK.",
                task=task,
                max_tokens=150,
                retries=2,
            )
            results.append({
                "task": task,
                "status": "ok" if text.strip().upper().startswith("OK") else "unexpected",
                "latency_ms": round((time.perf_counter() - started) * 1000),
            })
        except Exception as exc:
            results.append({
                "task": task,
                "status": "error",
                "error_type": type(exc).__name__,
                "detail": str(exc)[:300],
            })
    ok = all(item["status"] == "ok" for item in results)
    print(json.dumps({"status": "ok" if ok else "failed", "results": results}))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
