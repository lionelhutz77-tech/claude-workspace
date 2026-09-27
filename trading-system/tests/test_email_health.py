import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import ModuleType
from unittest.mock import patch


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "agents"))

# Der Health-Test benoetigt keine .env-Datei oder Drittanbieter-Bibliothek.
if "dotenv" not in sys.modules:
    dotenv_stub = ModuleType("dotenv")
    dotenv_stub.load_dotenv = lambda *_args, **_kwargs: False
    sys.modules["dotenv"] = dotenv_stub

import email_agent  # noqa: E402


class FakeMailbox:
    def __init__(self, counts=None, fail_login=False):
        self.counts = counts or {}
        self.fail_login = fail_login
        self.searches = []
        self.store_called = False
        self.logged_out = False

    def login(self, *_args):
        if self.fail_login:
            raise RuntimeError("sensitive provider detail")

    def select(self, _mailbox):
        return "OK", [b""]

    def search(self, _charset, criterion):
        self.searches.append(criterion)
        return "OK", [b" ".join([b"x"] * self.counts.get(criterion, 0))]

    def store(self, *_args):
        self.store_called = True

    def logout(self):
        self.logged_out = True


class EmailHealthTests(unittest.TestCase):
    def test_missing_configuration_is_explicit(self):
        with patch.object(email_agent, "GMX_EMAIL", ""), patch.object(email_agent, "GMX_PASSWORT", ""):
            health = email_agent.pruefe_email_health()
        self.assertEqual(health.status, email_agent.EMAIL_HEALTH_CONFIG_FEHLT)
        self.assertIsNone(health.ungelesen_gesamt)

    def test_login_failure_is_masked_and_does_not_leak_error(self):
        mailbox = FakeMailbox(fail_login=True)
        with patch.object(email_agent, "GMX_EMAIL", "configured"), patch.object(email_agent, "GMX_PASSWORT", "secret"):
            health = email_agent.pruefe_email_health(mail_factory=lambda: mailbox)
        self.assertEqual(health.status, email_agent.EMAIL_HEALTH_VERBINDUNG_FEHLER)
        self.assertNotIn("sensitive", repr(health))

    def test_connected_empty_inbox_is_distinguished(self):
        mailbox = FakeMailbox({"UNSEEN": 0})
        with patch.object(email_agent, "GMX_EMAIL", "configured"), patch.object(email_agent, "GMX_PASSWORT", "secret"), patch.object(email_agent, "ABSENDER_LISTE", []):
            health = email_agent.pruefe_email_health(mail_factory=lambda: mailbox)
        self.assertEqual(health.status, email_agent.EMAIL_HEALTH_0_UNSEEN)
        self.assertFalse(mailbox.store_called)

    def test_connected_inbox_with_unseen_messages_is_distinguished(self):
        mailbox = FakeMailbox({"UNSEEN": 2})
        with patch.object(email_agent, "GMX_EMAIL", "configured"), patch.object(email_agent, "GMX_PASSWORT", "secret"), patch.object(email_agent, "ABSENDER_LISTE", []):
            health = email_agent.pruefe_email_health(mail_factory=lambda: mailbox)
        self.assertEqual(health.status, email_agent.EMAIL_HEALTH_NACHRICHTEN)
        self.assertEqual(health.ungelesen_gesamt, 2)

    def test_filter_exclusion_is_distinguished_without_exposing_filter(self):
        mailbox = FakeMailbox({"UNSEEN": 3, 'UNSEEN FROM "private@example.test"': 0})
        with patch.object(email_agent, "GMX_EMAIL", "configured"), patch.object(email_agent, "GMX_PASSWORT", "secret"), patch.object(email_agent, "ABSENDER_LISTE", ["private@example.test"]):
            health = email_agent.pruefe_email_health(mail_factory=lambda: mailbox)
        self.assertEqual(health.status, email_agent.EMAIL_HEALTH_FILTER_AUSSCHLUSS)
        self.assertNotIn("private@example.test", repr(health))

    def test_stale_run_preserves_the_current_underlying_status(self):
        now = datetime(2026, 9, 21, 12, tzinfo=timezone.utc)
        health = email_agent.klassifiziere_email_health(
            konfiguriert=True,
            verbindung_ok=True,
            filter_aktiv=False,
            ungelesen_gesamt=0,
            letzter_erfolgreicher_lauf=now - timedelta(hours=31),
            jetzt=now,
        )
        self.assertEqual(health.status, email_agent.EMAIL_HEALTH_LAUF_VERALTET)
        self.assertEqual(health.basis_status, email_agent.EMAIL_HEALTH_0_UNSEEN)


if __name__ == "__main__":
    unittest.main()
