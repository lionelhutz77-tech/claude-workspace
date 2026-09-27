from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import gateway  # noqa: E402


class GatewayTests(unittest.TestCase):
    def test_routes_routine_and_deep_to_separate_groq_models(self) -> None:
        self.assertEqual(gateway.route("routine").model, "openai/gpt-oss-20b")
        self.assertEqual(gateway.route("review").model, "openai/gpt-oss-120b")

    def test_groq_uses_visible_same_provider_reserve_only_after_429(self) -> None:
        provider = gateway.load_config()["providers"]["groq"]
        response = {"choices": [{"message": {"content": "OK"}}]}
        with patch.object(
            gateway,
            "_post_json",
            side_effect=[gateway.GatewayError("Provider HTTP 429: limit"), response],
        ) as post:
            data, model, fallback_from = gateway._run_groq_with_reserve(
                provider, "test-key", "openai/gpt-oss-20b", "test", 64, 10
            )
        self.assertEqual(data, response)
        self.assertEqual(model, "qwen/qwen3.8-27b")
        self.assertEqual(fallback_from, "openai/gpt-oss-20b")
        self.assertEqual(post.call_count, 2)
        self.assertEqual(post.call_args_list[1].args[1]["reasoning_effort"], "none")

    def test_groq_skips_retired_reserve_and_keeps_rate_limit_error(self) -> None:
        provider = dict(gateway.load_config()["providers"]["groq"])
        provider["reserve_models"] = ["retired/model", "qwen/qwen3.8-27b"]
        response = {"choices": [{"message": {"content": "OK"}}]}
        with patch.object(
            gateway,
            "_post_json",
            side_effect=[
                gateway.GatewayError("Provider HTTP 429: limit"),
                gateway.GatewayError('Provider HTTP 404: {"error":{"code":"model_not_found"}}'),
                response,
            ],
        ):
            data, model, fallback_from = gateway._run_groq_with_reserve(
                provider, "test-key", "openai/gpt-oss-20b", "test", 64, 10
            )
        self.assertEqual(data, response)
        self.assertEqual(model, "qwen/qwen3.8-27b")
        self.assertEqual(fallback_from, "openai/gpt-oss-20b")

    def test_groq_reports_rate_limit_when_only_retired_reserves_remain(self) -> None:
        provider = dict(gateway.load_config()["providers"]["groq"])
        provider["reserve_models"] = ["retired/model"]
        with patch.object(
            gateway,
            "_post_json",
            side_effect=[
                gateway.GatewayError("Provider HTTP 429: limit"),
                gateway.GatewayError('Provider HTTP 404: {"error":{"code":"model_not_found"}}'),
            ],
        ):
            with self.assertRaisesRegex(gateway.GatewayError, "429"):
                gateway._run_groq_with_reserve(
                    provider, "test-key", "openai/gpt-oss-20b", "test", 64, 10
                )

    def test_groq_does_not_fallback_on_non_rate_error(self) -> None:
        provider = gateway.load_config()["providers"]["groq"]
        with patch.object(
            gateway, "_post_json", side_effect=gateway.GatewayError("Provider HTTP 401: auth")
        ) as post:
            with self.assertRaisesRegex(gateway.GatewayError, "401"):
                gateway._run_groq_with_reserve(
                    provider, "test-key", "openai/gpt-oss-20b", "test", 64, 10
                )
        post.assert_called_once()

    def test_routes_coding_to_gemini(self) -> None:
        selected = gateway.route("coding")
        self.assertEqual(selected.provider, "gemini_cli")
        self.assertEqual(selected.model, "auto")

    def test_global_task_profiles_are_data_driven(self) -> None:
        self.assertEqual(gateway.route("summarize").provider, "groq")
        self.assertEqual(gateway.route("presentation_outline").provider, "gemini_cli")
        self.assertEqual(gateway.route("market_synthesis").model, "openai/gpt-oss-120b")

    def test_deterministic_work_does_not_consume_ai_quota(self) -> None:
        with self.assertRaisesRegex(gateway.GatewayError, "no AI provider"):
            gateway.route("calculation")

    def test_personal_data_is_blocked_without_local_provider(self) -> None:
        config = gateway.load_config()
        config["providers"]["ollama"]["enabled"] = False
        with patch.object(gateway, "load_config", return_value=config):
            with self.assertRaises(gateway.GatewayError):
                gateway.route("routine", "personal")

    def test_personal_data_routes_only_to_local_provider_when_enabled(self) -> None:
        selected = gateway.route("routine", "personal")
        self.assertEqual(selected.provider, "ollama")
        self.assertEqual(selected.model, "qwen3:1.7b")

    def test_personal_deep_task_never_leaves_ollama(self) -> None:
        selected = gateway.route("architecture", "personal")
        self.assertEqual(selected.provider, "ollama")

    def test_secret_is_blocked_before_network(self) -> None:
        with patch.object(gateway, "_post_json") as post:
            with self.assertRaises(gateway.GatewayError):
                gateway.generate("api_key = gsk-this-is-a-secret-value")
            post.assert_not_called()
        with patch.object(gateway, "_run_gemini") as gemini:
            with self.assertRaises(gateway.GatewayError):
                gateway.generate("password = this-must-never-leave", task="coding")
            gemini.assert_not_called()

    def test_gemini_result_is_bounded_and_reports_actual_model(self) -> None:
        fake = {
            "response": "OK",
            "stats": {"models": {"gemini-test-model": {}}},
        }
        with patch.object(gateway, "_run_gemini", return_value=fake), patch.object(gateway, "_record_telemetry"):
            result = gateway.generate("public test", task="coding", sensitivity="public")
        self.assertEqual(result["provider"], "gemini_cli")
        self.assertEqual(result["model"], "gemini-test-model")
        self.assertEqual(result["text"], "OK")

    def test_gemini_child_environment_excludes_api_keys(self) -> None:
        fake_environment = {
            "PATH": "test-path",
            "SYSTEMROOT": "C:\\Windows",
            "GROQ_API_KEY": "must-not-leak",
            "GEMINI_API_KEY": "must-not-leak",
        }
        with patch.dict(os.environ, fake_environment, clear=True):
            environment = gateway._gemini_environment(ROOT / ".test-home")
        self.assertEqual(environment["PATH"], "test-path")
        self.assertNotIn("GROQ_API_KEY", environment)
        self.assertNotIn("GEMINI_API_KEY", environment)

    def test_gemini_api_key_selection_is_not_mistaken_for_verified_auth(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            settings = home / ".gemini" / "settings.json"
            settings.parent.mkdir(parents=True)
            settings.write_text(
                json.dumps({"security": {"auth": {"selectedType": "gemini-api-key"}}}),
                encoding="utf-8",
            )
            with patch.object(gateway, "_gemini_paths", return_value=("node", ROOT / "gemini.js", home)):
                self.assertTrue(gateway._gemini_auth_selected({}))
                self.assertFalse(gateway._gemini_authenticated({}))
                (home / ".gemini" / "gateway-authenticated").write_text("verified\n", encoding="utf-8")
                self.assertTrue(gateway._gemini_authenticated({}))

    def test_oversize_input_is_blocked(self) -> None:
        with self.assertRaises(gateway.GatewayError):
            gateway.generate("x" * 12001)

    def test_per_call_output_limit_is_enforced(self) -> None:
        with patch.object(gateway, "_run_gemini", return_value={"response": "x" * 500, "stats": {}}), patch.object(gateway, "_record_telemetry"):
            result = gateway.generate("public test", task="coding", max_output_chars=192)
        self.assertEqual(len(result["text"]), 192)
        self.assertTrue(result["truncated"])

    def test_profile_output_limits_protect_codex_context(self) -> None:
        cases = (
            ("summarize", "routine", 1800),
            ("coding", "worker", 3200),
            ("architecture", "deep", 3600),
        )
        for task, expected_profile, expected_limit in cases:
            with self.subTest(task=task), \
                 patch.object(gateway, "_run_gemini", return_value={"response": "x" * 7000, "stats": {}}), \
                 patch.object(gateway, "_post_json", return_value={"choices": [{"message": {"content": "x" * 7000}}]}), \
                 patch.object(gateway, "_read_env_key", return_value="test-key"), \
                 patch.object(gateway, "_record_telemetry"):
                result = gateway.generate("public test", task=task, sensitivity="public")
            self.assertEqual(result["profile"], expected_profile)
            self.assertEqual(result["output_limit_chars"], expected_limit)
            self.assertEqual(len(result["text"]), expected_limit)
            self.assertTrue(result["truncated"])

    def test_explicit_limit_cannot_bypass_profile_ceiling(self) -> None:
        with patch.object(gateway, "_post_json", return_value={"choices": [{"message": {"content": "x" * 7000}}]}), \
             patch.object(gateway, "_read_env_key", return_value="test-key"), \
             patch.object(gateway, "_record_telemetry"):
            result = gateway.generate(
                "public test",
                task="summarize",
                sensitivity="public",
                max_output_chars=6000,
            )
        self.assertEqual(result["output_limit_chars"], 1800)
        self.assertEqual(len(result["text"]), 1800)

    def test_invalid_per_call_output_limit_is_blocked(self) -> None:
        with self.assertRaises(gateway.GatewayError):
            gateway.generate("public test", max_output_chars=100)

    def test_telemetry_keeps_metadata_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "telemetry.jsonl"
            with patch.object(gateway, "TELEMETRY_PATH", path):
                gateway._record_telemetry({
                    "status": "ok",
                    "provider": "fixture",
                    "prompt": "must not be stored",
                    "text": "must not be stored",
                    "credential": "must not be stored",
                })
            event = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(event["provider"], "fixture")
        self.assertNotIn("prompt", event)
        self.assertNotIn("text", event)
        self.assertNotIn("credential", event)

    def test_usage_summary_groups_metadata_without_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "telemetry.jsonl"
            path.write_text(
                json.dumps({"provider": "local", "status": "ok", "input_chars": 10, "output_chars": 4}) + "\n" +
                json.dumps({"provider": "local", "status": "error", "input_chars": 5}) + "\n",
                encoding="utf-8",
            )
            with patch.object(gateway, "TELEMETRY_PATH", path):
                summary = gateway.usage_summary()
        self.assertEqual(summary["tracked_calls"], 2)
        self.assertEqual(summary["providers"]["local"]["errors"], 1)
        self.assertFalse(summary["contains_prompt_content"])

    def test_mcp_initialize_and_list(self) -> None:
        messages = "\n".join(
            json.dumps(item)
            for item in (
                {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
                {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
            )
        ) + "\n"
        result = subprocess.run(
            [sys.executable, str(ROOT / "mcp_server.py")],
            input=messages,
            text=True,
            capture_output=True,
            check=True,
            timeout=10,
        )
        responses = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(responses[0]["result"]["serverInfo"]["name"], "lionel-free-ai-gateway")
        self.assertEqual(len(responses[1]["result"]["tools"]), 5)
        tools = {item["name"]: item for item in responses[1]["result"]["tools"]}
        self.assertIn("max_output_chars", tools["free_ai_generate"]["inputSchema"]["properties"])
        self.assertNotIn("max_output_chars", tools["free_ai_route"]["inputSchema"]["properties"])

    def test_preflight_uses_no_model_calls_and_accepts_optional_claude(self) -> None:
        config = gateway.load_config()
        fake_state = {
            "groq": {"enabled": True, "configured": True},
            "gemini_cli": {"enabled": True, "installed": True, "authenticated": True},
            "claude_code": {"enabled": False},
        }
        fake_tags = {"models": [{"name": "qwen3:1.7b"}]}
        def fake_read_text(path: Path, *args: object, **kwargs: object) -> str:
            if path.name == "project-state.json":
                return '{"active_task_id":"LIONEL-008"}'
            if path.name == "next-task.json":
                return '{"task_id":"LIONEL-008","status":"in_progress"}'
            if path.name == "orchestration-validation.json":
                return '{"overall_exit_code":0,"source_set_sha256":"abc"}'
            return '{"goal":"test","next_step":"continue"}'

        with patch.object(gateway, "load_config", return_value=config), \
             patch.object(gateway, "status", return_value=fake_state), \
             patch.object(gateway, "_get_json", return_value=fake_tags), \
             patch.object(Path, "is_file", return_value=True), \
             patch.object(Path, "iterdir", return_value=iter(())), \
             patch.object(Path, "read_text", autospec=True, side_effect=fake_read_text), \
             patch.object(gateway, "_lionel_validation_is_current", return_value=True), \
             patch.object(gateway, "_post_json") as post, \
             patch.object(gateway, "_run_gemini") as gemini:
            result = gateway.preflight()
        self.assertEqual(result["overall"], "ready_with_warnings")
        self.assertEqual(result["quota_calls"], 0)
        post.assert_not_called()
        gemini.assert_not_called()

    def test_preflight_returns_compact_resume_instead_of_full_history(self) -> None:
        config = gateway.load_config()
        fake_state = {
            "groq": {"enabled": True, "configured": True},
            "gemini_cli": {"enabled": True, "installed": True, "authenticated": True},
            "claude_code": {"enabled": False},
        }
        def fake_read_text(path: Path, *args: object, **kwargs: object) -> str:
            if path.name == "project-state.json":
                return '{"active_task_id":"LIONEL-009"}'
            if path.name == "next-task.json":
                return '{"task_id":"LIONEL-009","status":"completed"}'
            if path.name == "orchestration-validation.json":
                return '{"overall_exit_code":0,"source_set_sha256":"abc"}'
            return json.dumps({
                "goal": "test", "phase": "ready", "status": "active",
                "active_task": "none", "next_step": "continue",
                "last_green_gates": ["historical evidence" * 500],
                "known_warnings": ["old warning" * 500],
            })

        with patch.object(gateway, "load_config", return_value=config), \
             patch.object(gateway, "status", return_value=fake_state), \
             patch.object(gateway, "_get_json", return_value={"models": []}), \
             patch.object(Path, "is_file", return_value=True), \
             patch.object(Path, "iterdir", return_value=iter(())), \
             patch.object(Path, "read_text", autospec=True, side_effect=fake_read_text):
            result = gateway.preflight()
        self.assertEqual(result["work_state"], {
            "phase": "ready", "status": "active", "active_task": "none", "next_step": "continue"
        })
        self.assertEqual(result["work_state_path"], str(gateway.WORKSPACE / "ARBEITSSTAND.json"))
        self.assertNotIn("historical evidence", json.dumps(result))

    def test_preflight_degrades_on_valid_json_with_wrong_shapes(self) -> None:
        config = gateway.load_config()
        fake_state = {
            "groq": {"enabled": True, "configured": True},
            "gemini_cli": {"enabled": True, "installed": True, "authenticated": True},
            "claude_code": {"enabled": False},
        }
        def malformed_json(path: Path, *args: object, **kwargs: object) -> str:
            return "[]" if path.name != "ARBEITSSTAND.json" else "null"

        with patch.object(gateway, "load_config", return_value=config), \
             patch.object(gateway, "status", return_value=fake_state), \
             patch.object(gateway, "_get_json", return_value={"models": []}), \
             patch.object(Path, "is_file", return_value=True), \
             patch.object(Path, "iterdir", return_value=iter(())), \
             patch.object(Path, "read_text", autospec=True, side_effect=malformed_json):
            result = gateway.preflight()
        states = {item["id"]: item["state"] for item in result["checks"]}
        self.assertEqual(states["lionel_truth"], "fail")
        self.assertEqual(states["lionel_validation"], "warn")
        self.assertEqual(states["resume_checkpoint"], "fail")
        self.assertEqual(result["overall"], "blocked")

    def test_preflight_degrades_on_malformed_local_ollama_response(self) -> None:
        config = gateway.load_config()
        fake_state = {
            "groq": {"enabled": True, "configured": True},
            "gemini_cli": {"enabled": True, "installed": True, "authenticated": True},
            "claude_code": {"enabled": False},
        }
        with patch.object(gateway, "load_config", return_value=config), \
             patch.object(gateway, "status", return_value=fake_state), \
             patch.object(gateway, "_get_json", return_value={"models": [42]}), \
             patch.object(Path, "is_file", return_value=True), \
             patch.object(Path, "iterdir", return_value=iter(())), \
             patch.object(Path, "read_text", return_value='{"goal":"test","next_step":"continue"}'), \
             patch.object(gateway, "_lionel_validation_is_current", return_value=False):
            result = gateway.preflight()
        checks = {item["id"]: item["state"] for item in result["checks"]}
        self.assertEqual(checks["ollama_runtime"], "warn")

    def test_lionel_gate_freshness_rejects_stale_source_inventory(self) -> None:
        validation = {"overall_exit_code": 0, "source_set_sha256": "old-digest", "source_files": []}
        self.assertFalse(gateway._lionel_validation_is_current(ROOT.parent / "lionel-os", validation))

    def test_lionel_gate_freshness_accepts_matching_source_inventory(self) -> None:
        lionel_root = ROOT.parent / "lionel-os"
        sys.path.insert(0, str(lionel_root / "src"))
        try:
            from lionel_core.orchestration import digest_value, verification_source_inventory

            files = verification_source_inventory(lionel_root)
            validation = {
                "overall_exit_code": 0,
                "source_set_sha256": digest_value(files),
                "source_files": files,
            }
            self.assertTrue(gateway._lionel_validation_is_current(lionel_root, validation))
            closed_files = [dict(item) for item in files]
            task_file = next(item for item in closed_files if item["path"] == "control/next-task.json")
            task_file["sha256"] = "0" * 64
            closed_validation = {
                "overall_exit_code": 0,
                "source_set_sha256": digest_value(closed_files),
                "source_files": closed_files,
            }
            self.assertFalse(gateway._lionel_validation_is_current(lionel_root, closed_validation))
            self.assertTrue(gateway._lionel_validation_is_current(
                lionel_root, closed_validation, completed_task=True
            ))
        finally:
            sys.path.remove(str(lionel_root / "src"))

    def test_completed_lionel_task_is_not_reported_as_active(self) -> None:
        state, detail = gateway._evaluate_lionel_truth(
            {"active_task_id": "LIONEL-009"},
            {"task_id": "LIONEL-009", "status": "completed"},
            0,
        )
        self.assertEqual(state, "pass")
        self.assertEqual(detail, "Letzte Lionel-Aufgabe LIONEL-009 ist abgeschlossen; kein aktiver Lauf.")

    def test_review_only_claude_is_ready_without_becoming_generation_provider(self) -> None:
        provider = {"enabled": False, "mode": "review_only"}
        with patch.object(gateway.shutil, "which", return_value="claude.cmd"), \
             patch.object(Path, "is_file", return_value=True):
            self.assertTrue(gateway._claude_review_configured(provider))
        with patch.object(gateway.shutil, "which", return_value=None):
            self.assertFalse(gateway._claude_review_configured(provider))

    def test_completed_lionel_task_rejects_leftover_active_run(self) -> None:
        state, _ = gateway._evaluate_lionel_truth(
            {"active_task_id": "LIONEL-009"},
            {"task_id": "LIONEL-009", "status": "completed"},
            1,
        )
        self.assertEqual(state, "fail")

    def test_blocked_lionel_truth_is_not_reported_ready(self) -> None:
        state, _ = gateway._evaluate_lionel_truth(
            {"active_task_id": "LIONEL-010", "overall_status": "blocked"},
            {"task_id": "LIONEL-010", "status": "blocked"},
            0,
        )
        self.assertEqual(state, "fail")

    def test_cli_can_emit_unicode_on_windows_console(self) -> None:
        result = subprocess.run(
            [sys.executable, str(ROOT / "cli.py"), "route", "--task", "deep"],
            text=True,
            capture_output=True,
            check=True,
            timeout=10,
            encoding="utf-8",
        )
        self.assertIn("openai/gpt-oss-120b", result.stdout)


if __name__ == "__main__":
    unittest.main()
