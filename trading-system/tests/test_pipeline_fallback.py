import sys
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
sys.path.insert(0, str(PROJECT / "agents"))

import main  # noqa: E402
from telegram_agent import format_tagesbericht  # noqa: E402


class PipelineFallbackTests(unittest.TestCase):
    def test_gateway_failure_still_produces_telegram_compatible_signal(self):
        signal = {
            "asset": "TEST",
            "asset_typ": "aktie",
            "preis": 100.0,
            "empfehlung": "ABWARTEN",
        }
        with patch.object(main, "analysiere_mit_ki", side_effect=RuntimeError("gateway offline")):
            with patch.object(main.time, "sleep"):
                result = main.ki_phase([signal])

        self.assertEqual(result[0]["finale"]["empfehlung"], "ABWARTEN")
        self.assertEqual(result[0]["finale"]["risiko"], "UNBEKANNT")
        message = format_tagesbericht(result)
        self.assertIn("<b>⏸ Abwarten:</b> TEST", message)


if __name__ == "__main__":
    unittest.main()
