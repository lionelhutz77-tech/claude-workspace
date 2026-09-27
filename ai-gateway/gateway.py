from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parent
GPT_OSS_REASONING_BUFFER = 512
CONFIG_PATH = ROOT / "config.json"
TELEMETRY_PATH = ROOT / "telemetry.jsonl"

SECRET_PATTERNS = (
    re.compile(r"(?i)\b(?:api[_ -]?key|secret|password|token)\b\s*[:=]\s*[^\s,;]{8,}"),
    re.compile(r"\b(?:gsk|sk-proj|sk-ant)-[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"\b(?:AIza[0-9A-Za-z_-]{30,}|ya29\.[0-9A-Za-z_-]{20,})\b"),
    re.compile(r"\b(?:ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[A-Z0-9]{16})\b"),
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~-]{16,}\b"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)


class GatewayError(RuntimeError):
    pass


@dataclass(frozen=True)
class Route:
    provider: str
    model: str
    depth: str
    reason: str


def _record_telemetry(event: dict[str, Any]) -> None:
    """Append local metadata only; never prompts, outputs, credentials or errors."""
    allowed = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": event.get("status"),
        "provider": event.get("provider"),
        "model": event.get("model"),
        "task": event.get("task"),
        "depth": event.get("depth"),
        "input_chars": event.get("input_chars"),
        "output_chars": event.get("output_chars"),
        "output_limit_chars": event.get("output_limit_chars"),
        "latency_ms": event.get("latency_ms"),
        "truncated": event.get("truncated"),
        "error_type": event.get("error_type"),
    }
    try:
        with TELEMETRY_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(allowed, ensure_ascii=False) + "\n")
    except OSError:
        pass


def usage_summary() -> dict[str, Any]:
    """Summarize local metadata without reading or exposing prompt content."""
    events: list[dict[str, Any]] = []
    if TELEMETRY_PATH.is_file():
        for line in TELEMETRY_PATH.read_text(encoding="utf-8", errors="ignore").splitlines()[-5000:]:
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    providers: dict[str, dict[str, int]] = {}
    for event in events:
        name = str(event.get("provider") or "unknown")
        item = providers.setdefault(name, {"calls": 0, "errors": 0, "input_chars": 0, "output_chars": 0})
        item["calls"] += 1
        item["errors"] += int(event.get("status") == "error")
        item["input_chars"] += int(event.get("input_chars") or 0)
        item["output_chars"] += int(event.get("output_chars") or 0)
    return {
        "tracked_calls": len(events),
        "successful_calls": sum(event.get("status") == "ok" for event in events),
        "failed_calls": sum(event.get("status") == "error" for event in events),
        "providers": providers,
        "contains_prompt_content": False,
    }


def load_config() -> dict[str, Any]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def _read_env_key(name: str) -> str | None:
    """Read one known key locally; never return or log any other .env content."""
    value = os.environ.get(name)
    if value:
        return value
    for path in (WORKSPACE / "trading-system" / ".env", WORKSPACE / "instagram-system" / ".env"):
        if not path.is_file():
            continue
        for raw_line in path.read_text(encoding="utf-8-sig", errors="ignore").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, candidate = line.split("=", 1)
            if key.strip() == name:
                return candidate.strip().strip("\"'") or None
    return None


def scan_text(text: str) -> list[str]:
    findings: list[str] = []
    for index, pattern in enumerate(SECRET_PATTERNS, start=1):
        if pattern.search(text):
            findings.append(f"secret_pattern_{index}")
    return findings


def _select_profile(routing: dict[str, Any], normalized_task: str) -> tuple[str, dict[str, Any]]:
    profile_name = routing["default_profile"]
    profile = routing["profiles"][profile_name]
    for candidate_name, candidate in routing["profiles"].items():
        if normalized_task in candidate["tasks"]:
            return candidate_name, candidate
    return profile_name, profile


def route(task: str = "routine", sensitivity: str = "project") -> Route:
    config = load_config()
    providers = config["providers"]
    routing = config["routing"]
    normalized_task = task.strip().lower()

    if normalized_task in routing["deterministic_local_tasks"]:
        raise GatewayError(
            f"Task '{normalized_task}' needs no AI provider; execute it deterministically and locally."
        )

    profile_name, profile = _select_profile(routing, normalized_task)
    depth = profile["depth"]

    ollama = providers["ollama"]
    if sensitivity == "personal":
        if ollama["enabled"]:
            return Route(
                "ollama",
                ollama[f"{depth}_model"],
                depth,
                "Private Inhalte bleiben ausschließlich auf der lokalen Ollama-API.",
            )
        raise GatewayError("Personal data is blocked until a local provider is enabled.")

    preferred_name = profile["provider"]
    preferred = providers[preferred_name]
    if preferred["enabled"] and sensitivity in preferred["allowed_sensitivity"]:
        model = preferred.get("model") or preferred[f"{depth}_model"]
        return Route(preferred_name, model, depth, f"Profil '{profile_name}': {profile['reason']}")

    if ollama["enabled"] and sensitivity in ollama["allowed_sensitivity"]:
        return Route("ollama", ollama[f"{depth}_model"], depth, "Bevorzugter Provider ist deaktiviert; lokaler, transparenter Ersatzweg.")
    raise GatewayError("No enabled provider is permitted for this sensitivity.")


def _post_json(url: str, payload: dict[str, Any], headers: dict[str, str], timeout: int) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "lionel-os-free-ai-gateway/1.0",
            **headers,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:500]
        raise GatewayError(f"Provider HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise GatewayError(f"Provider unavailable: {exc.reason}") from exc


def _run_groq_with_reserve(
    provider: dict[str, Any], api_key: str, model: str, prompt: str, max_tokens: int, timeout: int
) -> tuple[dict[str, Any], str, str | None]:
    """Use verified same-provider reserves only after an explicit HTTP 429."""
    candidates = [model, *provider.get("reserve_models", [])]
    candidates = list(dict.fromkeys(candidates))
    fallback_from: str | None = None
    last_rate_error: GatewayError | None = None
    for candidate in candidates:
        payload: dict[str, Any] = {
            "model": candidate,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_completion_tokens": max_tokens,
        }
        if candidate.startswith("qwen/"):
            payload["reasoning_effort"] = "none"
        elif candidate.startswith("openai/gpt-oss"):
            # Reasoning-Tokens zaehlen zum Limit; ohne Puffer bleibt die Antwort bei
            # kleinen Limits leer. Die Zeichenlaenge begrenzt das Gateway danach selbst.
            payload["reasoning_effort"] = "low"
            payload["max_completion_tokens"] = max_tokens + GPT_OSS_REASONING_BUFFER
        try:
            data = _post_json(
                provider["base_url"].rstrip("/") + "/chat/completions",
                payload,
                {"Authorization": f"Bearer {api_key}"},
                timeout,
            )
            return data, candidate, fallback_from
        except GatewayError as exc:
            message = str(exc)
            if (
                last_rate_error is not None
                and "Provider HTTP 404:" in message
                and "model_not_found" in message
            ):
                # Retired reserve model: skip it, the visible error stays the 429.
                continue
            if "Provider HTTP 429:" not in message:
                raise
            last_rate_error = exc
            fallback_from = fallback_from or model
    if last_rate_error is not None:
        raise last_rate_error
    raise GatewayError("No Groq model candidate is configured.")


def _get_json(url: str, timeout: int = 3) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "lionel-os-free-ai-gateway/1.0"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError) as exc:
        raise GatewayError(f"Local service unavailable: {type(exc).__name__}") from exc


def _gemini_paths(provider: dict[str, Any]) -> tuple[str | None, Path | None, Path]:
    node = shutil.which("node")
    launcher = shutil.which("gemini.cmd") or shutil.which("gemini")
    entrypoint = None
    if launcher:
        candidate = Path(launcher).resolve().parent / "node_modules" / "@google" / "gemini-cli" / "bundle" / "gemini.js"
        if candidate.is_file():
            entrypoint = candidate
    home = (ROOT / provider["home_dir"]).resolve()
    return node, entrypoint, home


def _gemini_authenticated(provider: dict[str, Any]) -> bool:
    _, _, home = _gemini_paths(provider)
    gemini_dir = home / ".gemini"
    return (gemini_dir / "oauth_creds.json").is_file() or (gemini_dir / "gateway-authenticated").is_file()


def _gemini_auth_selected(provider: dict[str, Any]) -> bool:
    _, _, home = _gemini_paths(provider)
    gemini_dir = home / ".gemini"
    settings_path = gemini_dir / "settings.json"
    if not settings_path.is_file():
        return False
    try:
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    selected_type = settings.get("security", {}).get("auth", {}).get("selectedType")
    return selected_type == "gemini-api-key"


def _gemini_environment(home: Path) -> dict[str, str]:
    allowed = (
        "APPDATA",
        "COMSPEC",
        "HOMEDRIVE",
        "HOMEPATH",
        "LOCALAPPDATA",
        "PATH",
        "PATHEXT",
        "SYSTEMDRIVE",
        "SYSTEMROOT",
        "TEMP",
        "TMP",
        "USERPROFILE",
        "WINDIR",
    )
    environment = {key: os.environ[key] for key in allowed if key in os.environ}
    environment["GEMINI_CLI_HOME"] = str(home)
    environment["NO_COLOR"] = "1"
    return environment


def _run_gemini(prompt: str, provider: dict[str, Any], timeout: int) -> dict[str, Any]:
    node, entrypoint, home = _gemini_paths(provider)
    if not node or not entrypoint:
        raise GatewayError("Gemini CLI is not installed.")
    home.mkdir(parents=True, exist_ok=True)
    command = [
        node,
        str(entrypoint),
        "--prompt",
        "",
        "--output-format",
        "json",
        "--approval-mode",
        "plan",
        "--skip-trust",
    ]
    try:
        with tempfile.TemporaryDirectory(prefix="lionel-gemini-") as workdir:
            completed = subprocess.run(
                command,
                input=prompt,
                text=True,
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                cwd=workdir,
                env=_gemini_environment(home),
                timeout=timeout,
                check=False,
            )
    except subprocess.TimeoutExpired as exc:
        raise GatewayError(f"Gemini CLI timed out after {timeout} seconds.") from exc
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "unknown error").strip()[:500]
        raise GatewayError(f"Gemini CLI failed with exit code {completed.returncode}: {detail}")
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise GatewayError("Gemini CLI returned invalid JSON.") from exc
    marker = home / ".gemini" / "gateway-authenticated"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text("verified\n", encoding="utf-8")
    return result


def generate(
    prompt: str,
    task: str = "routine",
    sensitivity: str = "project",
    max_output_chars: int | None = None,
) -> dict[str, Any]:
    config = load_config()
    limits = config["limits"]
    if not isinstance(prompt, str) or not prompt.strip():
        raise GatewayError("Prompt must be non-empty text.")
    if len(prompt) > limits["max_input_chars"]:
        raise GatewayError(f"Input exceeds {limits['max_input_chars']} characters.")
    findings = scan_text(prompt)
    if findings:
        raise GatewayError("Input blocked by secret scanner: " + ", ".join(findings))

    profile_name, _ = _select_profile(config["routing"], task.strip().lower())
    profile_limit = limits["profile_output_chars"][profile_name]
    configured_output_limit = min(limits["max_output_chars"], profile_limit)
    if max_output_chars is None:
        output_limit = configured_output_limit
    elif not isinstance(max_output_chars, int) or max_output_chars < 192:
        raise GatewayError("max_output_chars must be an integer of at least 192.")
    else:
        output_limit = min(max_output_chars, configured_output_limit)

    selected = route(task, sensitivity)
    started = time.perf_counter()
    max_tokens = max(64, min(2048, output_limit // 3))

    try:
        if selected.provider == "groq":
            provider = config["providers"]["groq"]
            api_key = _read_env_key("GROQ_API_KEY")
            if not api_key:
                raise GatewayError("GROQ_API_KEY is not configured locally.")
            data, actual_model, fallback_from = _run_groq_with_reserve(
                provider,
                api_key,
                selected.model,
                prompt,
                max_tokens,
                limits["request_timeout_seconds"],
            )
            if actual_model != selected.model:
                selected = Route(
                    selected.provider,
                    actual_model,
                    selected.depth,
                    f"{selected.reason} Reserve nach explizitem HTTP 429; Ausgangsmodell: {fallback_from}.",
                )
            text = data["choices"][0]["message"]["content"]
        elif selected.provider == "gemini_cli":
            provider = config["providers"]["gemini_cli"]
            data = _run_gemini(prompt, provider, limits["request_timeout_seconds"])
            text = data.get("response", "")
            models = list(data.get("stats", {}).get("models", {}).keys())
            if models:
                selected = Route(selected.provider, ",".join(models), selected.depth, selected.reason)
        elif selected.provider == "ollama":
            provider = config["providers"]["ollama"]
            data = _post_json(
                provider["base_url"].rstrip("/") + "/api/generate",
                {"model": selected.model, "prompt": prompt, "stream": False},
                {},
                limits["request_timeout_seconds"],
            )
            text = data["response"]
        else:
            raise GatewayError(f"Unsupported provider: {selected.provider}")
    except Exception as exc:
        _record_telemetry({
            "status": "error",
            "provider": selected.provider,
            "model": selected.model,
            "task": task,
            "depth": selected.depth,
            "input_chars": len(prompt),
            "output_limit_chars": output_limit,
            "latency_ms": round((time.perf_counter() - started) * 1000),
            "error_type": type(exc).__name__,
        })
        raise

    raw_text = str(text)
    text = raw_text[:output_limit]
    result = {
        "provider": selected.provider,
        "model": selected.model,
        "depth": selected.depth,
        "text": text,
        "profile": profile_name,
        "output_limit_chars": output_limit,
        "latency_ms": round((time.perf_counter() - started) * 1000),
        "truncated": len(raw_text) > output_limit,
        "rate_limit_fallback_from": fallback_from if selected.provider == "groq" else None,
    }
    _record_telemetry({
        "status": "ok",
        "provider": result["provider"],
        "model": result["model"],
        "task": task,
        "depth": result["depth"],
        "input_chars": len(prompt),
        "output_chars": len(text),
        "output_limit_chars": output_limit,
        "latency_ms": result["latency_ms"],
        "truncated": result["truncated"],
    })
    return result


def status() -> dict[str, Any]:
    config = load_config()
    gemini = config["providers"]["gemini_cli"]
    gemini_node, gemini_entrypoint, _ = _gemini_paths(gemini)
    return {
        "gateway": "ready",
        "groq": {
            "enabled": config["providers"]["groq"]["enabled"],
            "configured": bool(_read_env_key("GROQ_API_KEY")),
            "routine_model": config["providers"]["groq"]["routine_model"],
            "deep_model": config["providers"]["groq"]["deep_model"],
            "reserve_models": config["providers"]["groq"].get("reserve_models", []),
            "reserve_policy": config["providers"]["groq"].get("reserve_policy"),
        },
        "gemini_cli": {
            "enabled": gemini["enabled"],
            "installed": bool(gemini_node and gemini_entrypoint),
            "authenticated": _gemini_authenticated(gemini),
            "auth_selected": _gemini_auth_selected(gemini),
            "model": gemini["model"],
            "task_types": gemini["task_types"],
        },
        "ollama": {
            "enabled": config["providers"]["ollama"]["enabled"],
            "local_only": config["providers"]["ollama"]["local_only"],
            "base_url": config["providers"]["ollama"]["base_url"],
            "routine_model": config["providers"]["ollama"]["routine_model"],
            "deep_model": config["providers"]["ollama"]["deep_model"],
        },
        "claude_code": config["providers"]["claude_code"],
        "openai_api": config["providers"]["openai_api"],
        "codex_cli": config["providers"]["codex_cli"],
        "omniroute": config["providers"]["omniroute"],
        "limits": config["limits"],
        "routing": config["routing"],
    }


def _evaluate_lionel_truth(
    project_state: dict[str, Any], task: dict[str, Any], active_entry_count: int
) -> tuple[str, str]:
    """Classify the canonical task pointer without treating it as an open run."""
    task_id = str(task.get("task_id", ""))
    pointer = str(project_state.get("active_task_id", ""))
    task_status = str(task.get("status", ""))
    if not pointer or pointer != task_id:
        return "fail", "Lionel-Projektstatus und nächste Aufgabe fehlen oder widersprechen sich."
    if task_status == "blocked" or project_state.get("overall_status") == "blocked":
        return "fail", f"Lionel-Aufgabe {task_id} ist blockiert; Recovery oder Nutzerentscheidung nötig."
    if task_status == "completed":
        if active_entry_count:
            return "fail", f"Lionel-Aufgabe {task_id} ist abgeschlossen, aber ein aktiver Lauf ist verblieben."
        return "pass", f"Letzte Lionel-Aufgabe {task_id} ist abgeschlossen; kein aktiver Lauf."
    # For nonterminal tasks the event store, not next-task.status, owns the live
    # run state; a prepared task may still say ready after OPEN.
    return "pass", f"Lionel-Aufgabe {task_id} hat Status {task_status or 'nicht gesetzt'}."


def _claude_review_configured(provider: dict[str, Any]) -> bool:
    """Review-only is separate from the intentionally disabled generation provider."""
    return (
        provider.get("mode") == "review_only"
        and bool(shutil.which("claude.cmd") or shutil.which("claude"))
        and (WORKSPACE / "lionel-os" / "src" / "lionel_core" / "review_bridge.py").is_file()
    )


def _lionel_validation_is_current(
    lionel_root: Path, validation: dict[str, Any], *, completed_task: bool = False
) -> bool:
    """A green historical gate is not evidence for changed or added source files."""
    if not isinstance(validation, dict):
        return False
    if validation.get("overall_exit_code") != 0 or not validation.get("source_set_sha256"):
        return False
    saved_files = validation.get("source_files")
    if not isinstance(saved_files, list):
        return False
    source_root = str(lionel_root / "src")
    sys.path.insert(0, source_root)
    try:
        from lionel_core.orchestration import digest_value, verification_source_inventory

        if digest_value(saved_files) != validation["source_set_sha256"]:
            return False
        inventory = verification_source_inventory(lionel_root)
        if completed_task:
            # Archiving closes next-task.json after the bound gate. The task
            # pointer/status is validated separately by lionel_truth.
            inventory = [item for item in inventory if item["path"] != "control/next-task.json"]
            saved_files = [item for item in saved_files if item["path"] != "control/next-task.json"]
        return inventory == saved_files
    except (ImportError, OSError, RuntimeError, TypeError, ValueError):
        return False
    finally:
        sys.path.remove(source_root)


def preflight() -> dict[str, Any]:
    """Run local, read-only readiness checks without consuming any model quota."""
    config = load_config()
    current = status()
    checks: list[dict[str, str]] = []

    def add(check_id: str, state: str, detail: str) -> None:
        checks.append({"id": check_id, "state": state, "detail": detail})

    required_truth = ("AGENTS.md", "ORCHESTRATION.md", "PROMPTATHON-6H.md", "OFFENE-IDEEN.md")
    missing_truth = [name for name in required_truth if not (WORKSPACE / name).is_file()]
    add(
        "project_truth",
        "pass" if not missing_truth else "fail",
        "Alle zentralen Regeldateien vorhanden." if not missing_truth else f"Fehlt: {', '.join(missing_truth)}",
    )

    ollama = config["providers"]["ollama"]
    local_url = ollama["base_url"].rstrip("/")
    local_only = local_url in {"http://127.0.0.1:11434", "http://localhost:11434"} and ollama.get("local_only") is True
    add("ollama_local_only", "pass" if local_only else "fail", f"Konfiguriert: {local_url}")
    try:
        tags = _get_json(local_url + "/api/tags") if local_only else {}
        if not isinstance(tags, dict) or not isinstance(tags.get("models"), list):
            raise GatewayError("Local Ollama returned a malformed model list.")
        models = tags["models"]
        if any(not isinstance(item, dict) for item in models):
            raise GatewayError("Local Ollama returned a malformed model entry.")
        model_names = {str(item.get("name")) for item in models}
        expected_model = ollama["routine_model"]
        model_ready = expected_model in model_names
        add(
            "ollama_runtime",
            "pass" if model_ready else "warn",
            f"Lokales Modell {expected_model} verfügbar." if model_ready else f"Lokales Modell {expected_model} nicht gemeldet.",
        )
    except GatewayError:
        add("ollama_runtime", "warn", "Lokale Ollama-API antwortet momentan nicht.")

    groq = current["groq"]
    add("groq_config", "pass" if groq["enabled"] and groq["configured"] else "warn", "Groq ist lokal konfiguriert." if groq["configured"] else "Groq-Schlüssel fehlt oder Provider ist aus.")
    gemini = current["gemini_cli"]
    gemini_ready = gemini["enabled"] and gemini["installed"] and gemini["authenticated"]
    add("gemini_worker", "pass" if gemini_ready else "warn", "Gemini-Worker ist installiert und authentifiziert." if gemini_ready else "Gemini-Worker ist nicht vollständig bereit.")

    claude = current["claude_code"]
    claude_review_ready = _claude_review_configured(claude)
    add(
        "claude_review",
        "pass" if claude_review_ready else "warn",
        "Separater Read-only-Review-Weg lokal vorhanden; Anmeldung wird vor dem Review geprüft."
        if claude_review_ready else "Claude-Code-CLI oder Read-only-Brücke lokal nicht verfügbar.",
    )

    trading_root = WORKSPACE / "trading-system"
    trading_files = (trading_root / "data" / "portfolio.db", trading_root / "data" / "multi_depot.db")
    missing_trading = [path.name for path in trading_files if not path.is_file()]
    add(
        "trading_data",
        "pass" if not missing_trading else "fail",
        "Legacy- und Segmentdatenbanken vorhanden." if not missing_trading else f"Fehlt: {', '.join(missing_trading)}",
    )
    dashboard = trading_root / "output" / "dashboard_aktuell.html"
    add("trading_dashboard", "pass" if dashboard.is_file() else "warn", "Aktuelles Trading-Dashboard vorhanden." if dashboard.is_file() else "Kein aktuelles Trading-Dashboard gefunden.")

    lionel_root = WORKSPACE / "lionel-os"
    task_completed = False
    try:
        lionel_state = json.loads((lionel_root / "control" / "project-state.json").read_text(encoding="utf-8"))
        lionel_task = json.loads((lionel_root / "control" / "next-task.json").read_text(encoding="utf-8"))
        if not isinstance(lionel_state, dict) or not isinstance(lionel_task, dict):
            raise ValueError("Lionel control truth is not an object")
        active_entry_count = sum(1 for _ in (lionel_root / "orchestration" / "active").iterdir())
        lionel_truth_state, lionel_truth_detail = _evaluate_lionel_truth(
            lionel_state, lionel_task, active_entry_count
        )
        task_completed = lionel_truth_state == "pass" and lionel_task.get("status") == "completed"
    except (OSError, ValueError):
        lionel_truth_state = "fail"
        lionel_truth_detail = "Lionel-Projektstatus und nächste Aufgabe fehlen oder widersprechen sich."
    add("lionel_truth", lionel_truth_state, lionel_truth_detail)

    try:
        validation = json.loads(
            (lionel_root / "evidence" / "orchestration-validation.json").read_text(encoding="utf-8")
        )
        validation_green = _lionel_validation_is_current(
            lionel_root, validation, completed_task=task_completed
        )
    except (OSError, ValueError):
        validation_green = False
    add(
        "lionel_validation",
        "pass" if validation_green else "warn",
        "Letzte gebundene Lionel-Vollvalidierung ist grün."
        if validation_green
        else "Die gebundene Lionel-Vollvalidierung fehlt, ist fehlgeschlagen oder stammt von einem älteren Quellbestand.",
    )

    state_path = WORKSPACE / "ARBEITSSTAND.json"
    try:
        work_state = json.loads(state_path.read_text(encoding="utf-8"))
        if not isinstance(work_state, dict):
            raise ValueError("resume checkpoint is not an object")
        state_ok = bool(work_state.get("goal") and work_state.get("next_step"))
    except (OSError, ValueError):
        work_state = {}
        state_ok = False
    add("resume_checkpoint", "pass" if state_ok else "fail", "Maschinenlesbarer Resume-Punkt vorhanden." if state_ok else "ARBEITSSTAND.json fehlt oder ist unvollständig.")

    failures = sum(item["state"] == "fail" for item in checks)
    warnings = sum(item["state"] == "warn" for item in checks)
    ready_workers = int(groq["enabled"] and groq["configured"]) + int(gemini_ready)
    if failures or ready_workers == 0:
        overall = "blocked"
    elif warnings:
        overall = "ready_with_warnings"
    else:
        overall = "ready"
    return {
        "overall": overall,
        "quota_calls": 0,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        # The full checkpoint remains on disk. Returning its history on every
        # preflight needlessly consumes the calling assistant's context budget.
        "work_state": {
            key: work_state[key]
            for key in ("phase", "status", "active_task", "next_step")
            if key in work_state
        },
        "work_state_path": str(state_path),
    }
