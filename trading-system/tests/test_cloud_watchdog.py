import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "scripts"))

from cloud_watchdog import WorkflowCheck, bewerte_laeufe  # noqa: E402


class CloudWatchdogTests(unittest.TestCase):
    def setUp(self):
        self.jetzt = datetime(2026, 10, 9, 19, 17, tzinfo=timezone.utc)
        self.check = WorkflowCheck("Tagesanalyse", "daily_trading.yml", 30.0, 3.0)

    def lauf(self, *, alter=2.0, status="completed", conclusion="success", event="schedule"):
        return {
            "created_at": (self.jetzt - timedelta(hours=alter)).isoformat(),
            "status": status,
            "conclusion": conclusion,
            "event": event,
            "html_url": "https://example.test/run/1",
        }

    def test_frischer_erfolgreicher_lauf_ist_gesund(self):
        gesund, meldung = bewerte_laeufe([self.lauf()], self.check, self.jetzt)
        self.assertTrue(gesund)
        self.assertIn("OK", meldung)

    def test_neuester_fehler_wird_nicht_von_altem_erfolg_maskiert(self):
        laeufe = [self.lauf(alter=2), self.lauf(alter=1, conclusion="failure")]
        gesund, meldung = bewerte_laeufe(laeufe, self.check, self.jetzt)
        self.assertFalse(gesund)
        self.assertIn("failure", meldung)

    def test_veralteter_lauf_loest_alarm_aus(self):
        gesund, meldung = bewerte_laeufe([self.lauf(alter=31)], self.check, self.jetzt)
        self.assertFalse(gesund)
        self.assertIn("31.0 h alt", meldung)

    def test_junger_lauf_darf_noch_laufen(self):
        gesund, meldung = bewerte_laeufe(
            [self.lauf(alter=1, status="in_progress", conclusion="")],
            self.check,
            self.jetzt,
        )
        self.assertTrue(gesund)
        self.assertIn("laeuft", meldung)

    def test_haengender_lauf_loest_alarm_aus(self):
        gesund, meldung = bewerte_laeufe(
            [self.lauf(alter=4, status="in_progress", conclusion="")],
            self.check,
            self.jetzt,
        )
        self.assertFalse(gesund)
        self.assertIn("haengt", meldung)

    def test_push_lauf_zaehlt_nicht_als_betriebslauf(self):
        gesund, meldung = bewerte_laeufe([self.lauf(event="push")], self.check, self.jetzt)
        self.assertFalse(gesund)
        self.assertIn("kein Cloud-Lauf", meldung)


class WorkflowContractTests(unittest.TestCase):
    def test_tagesworkflow_hat_nur_einen_zeitplan(self):
        workflow = (PROJECT.parent / ".github" / "workflows" / "daily_trading.yml").read_text(
            encoding="utf-8"
        )
        self.assertEqual(workflow.count("- cron:"), 1)
        self.assertIn('date -u +%u', workflow)

    def test_watchdog_prueft_alle_kernlaeufe_und_warnt(self):
        workflow = (PROJECT.parent / ".github" / "workflows" / "trading_watchdog.yml").read_text(
            encoding="utf-8"
        )
        script = (PROJECT / "scripts" / "cloud_watchdog.py").read_text(encoding="utf-8")
        for name in ("news_digest.yml", "daily_trading.yml", "weekly_review.yml", "alpaca_weekly.yml"):
            self.assertIn(name, script)
        self.assertIn("TELEGRAM_TOKEN", workflow)
        self.assertIn("steps.health.outcome == 'failure'", workflow)


if __name__ == "__main__":
    unittest.main()
