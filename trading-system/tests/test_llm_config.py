import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


AGENTS = Path(__file__).resolve().parents[1] / "agents"
sys.path.insert(0, str(AGENTS))

from llm_config import groq_model, groq_reasoning_effort  # noqa: E402


class LlmConfigTests(unittest.TestCase):
    def test_defaults_split_routine_and_deep_work(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(groq_model("routine"), "openai/gpt-oss-20b")
            self.assertEqual(groq_model("deep"), "openai/gpt-oss-120b")
            self.assertEqual(groq_reasoning_effort("routine"), "low")
            self.assertEqual(groq_reasoning_effort("deep"), "medium")

    def test_environment_can_override_models_centrally(self):
        values = {"GROQ_MODEL_ROUTINE": "routine-fixture", "GROQ_MODEL_DEEP": "deep-fixture"}
        with patch.dict(os.environ, values, clear=True):
            self.assertEqual(groq_model("routine"), "routine-fixture")
            self.assertEqual(groq_model("deep"), "deep-fixture")

    def test_unknown_tier_fails_closed(self):
        with self.assertRaises(ValueError):
            groq_model("unknown")
        with self.assertRaises(ValueError):
            groq_reasoning_effort("unknown")


if __name__ == "__main__":
    unittest.main()
