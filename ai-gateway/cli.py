from __future__ import annotations

import argparse
import json
import sys

from gateway import GatewayError, generate, preflight, route, status, usage_summary


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Lionel OS Free-AI-Gateway")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    sub.add_parser("usage")
    sub.add_parser("preflight")

    route_parser = sub.add_parser("route")
    route_parser.add_argument("--task", default="routine")
    route_parser.add_argument("--sensitivity", default="project", choices=("public", "project", "personal"))

    generate_parser = sub.add_parser("generate")
    generate_parser.add_argument("--prompt", required=True)
    generate_parser.add_argument("--task", default="routine")
    generate_parser.add_argument("--sensitivity", default="project", choices=("public", "project", "personal"))
    generate_parser.add_argument("--max-output-chars", type=int)

    health_parser = sub.add_parser("health")
    health_parser.add_argument("--task", default="routine", choices=("routine", "deep", "coding"))
    args = parser.parse_args()
    try:
        if args.command == "status":
            result = status()
        elif args.command == "usage":
            result = usage_summary()
        elif args.command == "preflight":
            result = preflight()
        elif args.command == "route":
            result = route(args.task, args.sensitivity).__dict__
        elif args.command == "health":
            response = generate("Antworte exakt mit OK.", task=args.task, sensitivity="public")
            result = {key: response[key] for key in ("provider", "model", "latency_ms")}
            result["ok"] = response["text"].strip().upper().startswith("OK")
        else:
            result = generate(args.prompt, args.task, args.sensitivity, args.max_output_chars)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except GatewayError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
