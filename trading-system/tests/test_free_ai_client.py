import sys
import unittest
from pathlib import Path
from unittest.mock import patch


AGENTS = Path(__file__).resolve().parents[1] / "agents"
sys.path.insert(0, str(AGENTS))

import free_ai_client  # noqa: E402


class FreeAiClientTests(unittest.TestCase):
    def test_forwards_task_and_hard_output_budget(self):
        with patch.object(
            free_ai_client,
            "generate",
            return_value={"text": "  OK  "},
        ) as generate:
            result = free_ai_client.generate_text(
                "Systemregel", "Aufgabe", task="research", max_tokens=300
            )

        self.assertEqual(result, "OK")
        prompt = generate.call_args.args[0]
        self.assertIn("SYSTEM:\nSystemregel", prompt)
        self.assertIn("AUFGABE:\nAufgabe", prompt)
        self.assertEqual(generate.call_args.kwargs["task"], "research")
        self.assertEqual(generate.call_args.kwargs["max_output_chars"], 900)

    def test_does_not_switch_provider_after_non_rate_limit_error(self):
        with patch.object(
            free_ai_client,
            "generate",
            side_effect=free_ai_client.GatewayError("provider unavailable"),
        ) as generate:
            with self.assertRaises(free_ai_client.GatewayError):
                free_ai_client.generate_text("System", "Aufgabe")
        generate.assert_called_once()


if __name__ == "__main__":
    unittest.main()
