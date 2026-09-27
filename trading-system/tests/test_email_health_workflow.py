import sys
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))

import main  # noqa: E402
from email_agent import (  # noqa: E402
    EMAIL_HEALTH_CONFIG_FEHLT,
    EMAIL_HEALTH_FILTER_AUSSCHLUSS,
    EMAIL_HEALTH_VERBINDUNG_FEHLER,
    EMAIL_HEALTH_LAUF_VERALTET,
    EmailHealth,
)


class EmailHealthWorkflowTests(unittest.TestCase):
    def health(self, status, basis_status=None):
        return EmailHealth(
            status=status,
            basis_status=basis_status or status,
            filter_aktiv=False,
        )

    def test_configuration_warning_is_safe_and_non_blocking(self):
        health = self.health(EMAIL_HEALTH_CONFIG_FEHLT)
        with patch.object(main, "pruefe_email_health", return_value=health), \
             patch.object(main, "sende_nachricht", return_value=False) as send, \
             patch("builtins.print") as output:
            result = main.protokolliere_email_health_und_warne()

        self.assertIs(result, health)
        self.assertEqual(send.call_count, 1)
        message = send.call_args.args[0]
        self.assertIn("nicht konfiguriert", message)
        self.assertNotIn("GMX", message)
        self.assertNotIn("@", message)
        self.assertIn(EMAIL_HEALTH_CONFIG_FEHLT, output.call_args.args[0])

    def test_connection_warning_uses_underlying_status_when_run_is_stale(self):
        health = self.health(EMAIL_HEALTH_LAUF_VERALTET, EMAIL_HEALTH_VERBINDUNG_FEHLER)
        with patch.object(main, "pruefe_email_health", return_value=health), \
             patch.object(main, "sende_nachricht", return_value=True) as send:
            main.protokolliere_email_health_und_warne()

        self.assertEqual(send.call_count, 1)
        self.assertNotIn("GMX", send.call_args.args[0])

    def test_filter_exclusion_is_logged_but_not_alerted(self):
        health = self.health(EMAIL_HEALTH_FILTER_AUSSCHLUSS)
        with patch.object(main, "pruefe_email_health", return_value=health), \
             patch.object(main, "sende_nachricht") as send, \
             patch("builtins.print") as output:
            main.protokolliere_email_health_und_warne()

        send.assert_not_called()
        self.assertIn(EMAIL_HEALTH_FILTER_AUSSCHLUSS, output.call_args.args[0])

    def test_health_and_telegram_failures_do_not_interrupt_the_pipeline(self):
        with patch.object(main, "pruefe_email_health", side_effect=RuntimeError("private detail")):
            self.assertIsNone(main.protokolliere_email_health_und_warne())

        health = self.health(EMAIL_HEALTH_VERBINDUNG_FEHLER)
        with patch.object(main, "pruefe_email_health", return_value=health), \
             patch.object(main, "sende_nachricht", side_effect=RuntimeError("provider detail")):
            self.assertIs(main.protokolliere_email_health_und_warne(), health)


if __name__ == "__main__":
    unittest.main()
