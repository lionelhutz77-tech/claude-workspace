import importlib.util
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd


SCANNER_DIR = Path(__file__).resolve().parents[2] / "tailwind-scanner"
sys.path.insert(0, str(SCANNER_DIR))
SPEC = importlib.util.spec_from_file_location("tailwind_scanner_logic", SCANNER_DIR / "scanner.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class TailwindScannerLogicTests(unittest.TestCase):
    def test_revisions_score_uses_positive_change_not_absolute_bull_count(self):
        recommendations = pd.DataFrame(
            [
                {"strongBuy": 6, "buy": 5},
                {"strongBuy": 5, "buy": 5},
            ]
        )
        fake = SimpleNamespace(recommendations=recommendations)

        with patch.object(MODULE.yf, "Ticker", return_value=fake):
            score, details = MODULE.berechne_revisions_score("TEST")

        self.assertEqual(score, 5)
        self.assertEqual(details["delta_bull_analysten"], 1)

    def test_empty_options_volume_is_not_scored_bullish(self):
        empty = pd.DataFrame({"volume": [0, None]})
        chain = SimpleNamespace(calls=empty, puts=empty)
        fake = SimpleNamespace(options=("2026-10-01",), option_chain=lambda _: chain)

        with patch.object(MODULE.yf, "Ticker", return_value=fake):
            score, details = MODULE.berechne_options_score("TEST")

        self.assertEqual(score, 0)
        self.assertEqual(details["quality"], "zu_wenig_volumen")
        self.assertIsNone(details["call_put_ratio"])

    def test_html_badge_uses_score_including_trends(self):
        result = {
            "ticker": "TEST",
            "thema": "AI",
            "gesamt_score": 40,
            "signal_stufe": "MODERAT",
            "kurs_info": {
                "kurs": 10,
                "ziel_kurs": 12,
                "upside_pct": 20,
                "abstand_ath_prozent": 10,
            },
            "scores": {"news": 20, "revisions": 10, "options": 10},
            "details": {"news_treffer": 4, "revisions": {}, "options": {}},
        }

        html = MODULE.erstelle_html([result], {"AI": {"score": 20}})

        self.assertIn("60/100", html)
        self.assertIn(">STARK</span>", html)


if __name__ == "__main__":
    unittest.main()
