import sys
import unittest
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))

from morning_note import morning_note_html, morning_note_lines  # noqa: E402
from agents.telegram_agent import format_tagesbericht  # noqa: E402
from dashboard import erstelle_html  # noqa: E402
from main import erstelle_tagesbericht  # noqa: E402


class MorningNoteTests(unittest.TestCase):
    def test_empty_run_does_not_invent_a_call_or_news(self):
        note = " ".join(morning_note_lines([]))
        self.assertIn("Kein Kaufsignal", note)
        self.assertIn("nicht verifiziert", note)
        self.assertNotIn("Overnight gestiegen", note)

    def test_null_or_nonfinite_fields_are_not_shown_as_prices(self):
        results = [
            {"asset": "X", "finale": None},
            {"asset": "Y", "finale": {"empfehlung": "KAUFEN", "einstieg": float("nan")}},
        ]
        note = " ".join(morning_note_lines(results))
        self.assertIn("Einstieg —", note)
        self.assertNotIn("nan", note.lower())

    def test_existing_signal_uses_only_supplied_numbers(self):
        results = [{
            "asset": "TEST", "finale": {
                "empfehlung": "KAUFEN", "einstieg": 100.0,
                "ziel": None, "stop_loss": 95.0, "risiko": "MITTEL",
            },
        }]
        note = " ".join(morning_note_lines(results))
        self.assertIn("Einstieg $100.00", note)
        self.assertIn("Ziel —", note)
        self.assertIn("Stop $95.00", note)
        self.assertIn("keine Rangliste", note)

    def test_dashboard_escapes_untrusted_asset(self):
        results = [{"asset": "<script>alert(1)</script>", "finale": {"empfehlung": "KAUFEN"}}]
        html = morning_note_html(results)
        self.assertIn("&lt;script&gt;", html)
        self.assertNotIn("<script>", html)

    def test_telegram_formatter_is_not_modified(self):
        results = [{"asset": "TEST", "finale": {"empfehlung": "ABWARTEN"}}]
        before = format_tagesbericht(results)
        morning_note_lines(results)
        self.assertEqual(before, format_tagesbericht(results))

    def test_empty_pipeline_outputs_include_note_without_changing_telegram(self):
        text = "\n".join(erstelle_tagesbericht([]))
        html = erstelle_html([], "13.09.2026 08:00")
        self.assertIn("MORNING NOTE", text)
        self.assertIn("Kein Kaufsignal", text)
        self.assertIn("<h2>Morning Note</h2>", html)
        self.assertIn("Kein Kaufsignal", html)
        self.assertNotIn("Morning Note", format_tagesbericht([]))


if __name__ == "__main__":
    unittest.main()
