import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


AGENTS = Path(__file__).resolve().parents[1] / "agents"
sys.path.insert(0, str(AGENTS))

with patch.dict(
    sys.modules,
    {
        "requests": types.SimpleNamespace(),
        "dotenv": types.SimpleNamespace(load_dotenv=lambda *args, **kwargs: None),
    },
):
    from telegram_agent import (  # noqa: E402
        format_tagesbericht, format_position_geschlossen, format_warnung,
    )


class TelegramContractTests(unittest.TestCase):
    def test_untrusted_fields_cannot_inject_telegram_html(self):
        signal = {
            "asset": "<b>FAKE</b>", "strategie": "<i>bad</i>", "preis": 100.0,
            "finale": {
                "empfehlung": "KAUFEN", "einstieg": 100.0, "ziel": 110.0,
                "stop_loss": 95.0, "optionalitaet": "<a href='x'>click</a>",
            },
        }
        message = format_tagesbericht([signal], fg_aktien={"score": 50, "label": "<script>x</script>"})
        self.assertIn("&lt;b&gt;FAKE&lt;/b&gt;", message)
        self.assertIn("&lt;i&gt;bad&lt;/i&gt;", message)
        self.assertIn("&lt;script&gt;x&lt;/script&gt;", message)
        self.assertNotIn("<a href=", message)
        self.assertIn("<b>✅ KAUFEN", message)
        self.assertIn("&lt;b&gt;FAKE&lt;/b&gt;", format_position_geschlossen("<b>FAKE</b>", 1.0, 1.0, "<i>x</i>"))
        self.assertIn("&lt;script&gt;", format_warnung("A", "<script>x</script>"))

    def test_formats_deterministic_fallback_when_ai_is_unavailable(self):
        signal = {
            "asset": "TEST",
            "preis": 100.0,
            "finale": {
                "empfehlung": "ABWARTEN",
                "einstieg": 100.0,
                "ziel": 110.0,
                "stop_loss": 95.0,
                "risiko": "UNBEKANNT",
                "gewinner": "-",
                "begruendung": "KI-Analyse nicht verfuegbar.",
            },
        }

        message = format_tagesbericht([signal])

        self.assertIn("<b>⏸ Abwarten:</b> TEST", message)
        self.assertIn("Keine Anlageberatung", message)


if __name__ == "__main__":
    unittest.main()
