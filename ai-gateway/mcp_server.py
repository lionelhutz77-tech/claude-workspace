from __future__ import annotations

import json
import sys
from typing import Any

from gateway import GatewayError, generate, preflight, route, status, usage_summary


TOOLS = [
    {
        "name": "free_ai_status",
        "description": "Show configured free/local AI routes without exposing credentials.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "free_ai_route",
        "description": "Choose the cheapest permitted AI provider/model without sending prompt text.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task": {"type": "string", "default": "routine"},
                "sensitivity": {"type": "string", "enum": ["public", "project", "personal"], "default": "project"},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "free_ai_usage",
        "description": "Summarize local provider call metadata without prompts, outputs or credentials.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "free_ai_preflight",
        "description": "Run local read-only readiness checks without consuming model quota.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "free_ai_generate",
        "description": "Send only the explicitly supplied, size-limited, secret-scanned text to the selected free/local model.",
        "inputSchema": {
            "type": "object",
            "required": ["prompt"],
            "properties": {
                "prompt": {"type": "string"},
                "task": {"type": "string", "default": "routine"},
                "sensitivity": {"type": "string", "enum": ["public", "project", "personal"], "default": "project"},
                "max_output_chars": {"type": "integer", "minimum": 192, "maximum": 6000},
            },
            "additionalProperties": False,
        },
    },
]


def _result(value: Any, error: bool = False) -> dict[str, Any]:
    return {
        "content": [{"type": "text", "text": json.dumps(value, ensure_ascii=False, indent=2)}],
        "isError": error,
    }


def handle(message: dict[str, Any]) -> dict[str, Any] | None:
    method = message.get("method")
    request_id = message.get("id")
    if request_id is None:
        return None
    if method == "initialize":
        value = {
            "protocolVersion": "2025-03-26",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "lionel-free-ai-gateway", "version": "1.0.0"},
        }
    elif method == "ping":
        value = {}
    elif method == "tools/list":
        value = {"tools": TOOLS}
    elif method == "tools/call":
        params = message.get("params", {})
        name = params.get("name")
        arguments = params.get("arguments", {})
        try:
            if name == "free_ai_status":
                value = _result(status())
            elif name == "free_ai_usage":
                value = _result(usage_summary())
            elif name == "free_ai_preflight":
                value = _result(preflight())
            elif name == "free_ai_route":
                value = _result(route(arguments.get("task", "routine"), arguments.get("sensitivity", "project")).__dict__)
            elif name == "free_ai_generate":
                value = _result(generate(
                    arguments["prompt"],
                    arguments.get("task", "routine"),
                    arguments.get("sensitivity", "project"),
                    arguments.get("max_output_chars"),
                ))
            else:
                value = _result({"error": f"Unknown tool: {name}"}, True)
        except (GatewayError, KeyError, TypeError) as exc:
            value = _result({"error": str(exc)}, True)
    else:
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": "Method not found"}}
    return {"jsonrpc": "2.0", "id": request_id, "result": value}


def main() -> None:
    for line in sys.stdin:
        try:
            message = json.loads(line)
            response = handle(message)
            if response is not None:
                print(json.dumps(response, ensure_ascii=False), flush=True)
        except Exception as exc:
            print(json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32603, "message": str(exc)}}), flush=True)


if __name__ == "__main__":
    main()
