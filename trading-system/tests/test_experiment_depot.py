import sqlite3
from contextlib import closing
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "agents"))
from experiment_depot import Quote, STRATEGIES, choose, process_run, statistics  # noqa: E402
from experiment_runner import market_quotes, run_daily  # noqa: E402
from experiment_status import render_report  # noqa: E402


def signal(asset="ABC", **fields):
    return {"asset": asset, "finale": {"empfehlung": "KAUFEN"},
            "gesamt_punkte": 5, "rsi": 55, "momentum_5d": 3,
            "tailwind_signal": "STARK", "tailwind_score": 80, **fields}


class ExperimentDepotTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.db = Path(self.folder.name) / "paper.db"

    def tearDown(self):
        self.folder.cleanup()

    def test_four_equal_10000_eur_alternative_budgets(self):
        stats = statistics(self.db)
        self.assertEqual({s["strategy"] for s in stats}, set(STRATEGIES))
        self.assertTrue(all(s["cash_eur"] == 10000 for s in stats))
        self.assertTrue(all(s["hit_rate_pct"] is None for s in stats))

    def test_signal_queued_not_filled_on_same_run_and_idempotent(self):
        first = process_run("r1", "2026-09-21T08:00:00Z", [signal()],
                            {"ABC": Quote(100, "2026-09-21T08:00:00Z")}, self.db)
        self.assertEqual(first["filled"], 0)
        self.assertEqual(first["queued"], 3)  # VALUE braucht RSI < 40
        self.assertEqual(process_run("r1", "2026-09-21T08:00:00Z", [signal()], {}, self.db)["status"],
                         "already_processed")
        self.assertTrue(all(s["cash_eur"] == 10000 for s in statistics(self.db)))

    def test_next_observation_fills_and_costs_then_exit(self):
        process_run("r1", "2026-09-21T08:00:00Z", [signal()], {}, self.db)
        # Stale quote cannot fill a previous signal.
        stale = process_run("r2", "2026-09-22T08:00:00Z", [],
                            {"ABC": Quote(100, "2026-09-21T07:00:00Z")}, self.db)
        self.assertEqual(stale["filled"], 0)
        filled = process_run("r3", "2026-09-23T08:00:00Z", [],
                             {"ABC": Quote(100, "2026-09-22T20:00:00Z")}, self.db)
        self.assertEqual(filled["filled"], 3)
        self.assertEqual(statistics(self.db)[0]["cash_eur"], 8000)
        closed = process_run("r4", "2026-09-24T08:00:00Z", [],
                             {"ABC": Quote(112, "2026-09-23T20:00:00Z")}, self.db)
        self.assertEqual(closed["closed"], 3)
        consensus = next(s for s in statistics(self.db) if s["strategy"] == "KONSENS")
        self.assertEqual(consensus["closed_trades"], 1)
        self.assertEqual(consensus["hit_rate_pct"], 100)
        self.assertGreater(consensus["realized_pnl_eur"], 0)

    def test_no_future_quote_or_backdated_run(self):
        process_run("r1", "2026-09-21T08:00:00Z", [signal()], {}, self.db)
        result = process_run("r2", "2026-09-22T08:00:00Z", [],
                             {"ABC": Quote(100, "2026-09-23T00:00:00Z")}, self.db)
        self.assertEqual(result["filled"], 0)
        with self.assertRaises(ValueError):
            process_run("older", "2026-09-21T07:00:00Z", [], {}, self.db)

    def test_no_final_buy_means_no_order(self):
        rejected = signal()
        rejected["finale"]["empfehlung"] = "ABWARTEN"
        self.assertTrue(all(not choose(strategy, [rejected]) for strategy in STRATEGIES))
        process_run("r1", "2026-09-21T08:00:00Z", [rejected], {}, self.db)
        with closing(sqlite3.connect(self.db)) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM orders").fetchone()[0], 0)

    def test_pending_order_expires_instead_of_using_late_price(self):
        process_run("r1", "2026-09-21T08:00:00Z", [signal()], {}, self.db)
        result = process_run("r2", "2026-09-25T08:00:00Z", [],
                             {"ABC": Quote(110, "2026-09-24T20:00:00Z")}, self.db)
        self.assertEqual(result["filled"], 0)
        with closing(sqlite3.connect(self.db)) as db:
            self.assertEqual(db.execute(
                "SELECT COUNT(*) FROM orders WHERE reason='expired'").fetchone()[0], 3)

    def test_invalid_numbers_do_not_crash_strategy_filter(self):
        malformed = signal()
        malformed["rsi"] = "not-a-number"
        malformed["momentum_5d"] = float("nan")
        self.assertEqual(choose("MOMENTUM", [malformed]), [])

    def test_daily_adapter_and_report_without_live_market_access(self):
        with patch("experiment_runner.market_quotes", return_value={}) as mocked:
            outcome, stats = run_daily([signal()], "2026-09-21T08:00:00Z", self.db)
        mocked.assert_called_once()
        self.assertEqual(outcome["filled"], 0)
        self.assertEqual(outcome["queued"], 3)
        report = render_report(stats)
        self.assertIn("KONSENS", report)
        self.assertIn("10.000", report)
        self.assertIn("noch offen", report)

    def test_crypto_signal_uses_separate_usd_quote_symbol(self):
        crypto = signal("ETH")
        crypto["asset_typ"] = "krypto"
        process_run("r1", "2026-09-21T08:00:00Z", [crypto], {}, self.db)
        result = process_run("r2", "2026-09-22T08:00:00Z", [],
                             {"ETH-USD": Quote(2200, "2026-09-21T20:00:00Z")}, self.db)
        self.assertEqual(result["filled"], 3)
        with closing(sqlite3.connect(self.db)) as db:
            self.assertEqual(db.execute(
                "SELECT COUNT(*) FROM positions WHERE asset_type='krypto'").fetchone()[0], 3)

    def test_market_data_outage_does_not_invent_quotes(self):
        fake = ModuleType("yfinance")
        class BrokenTicker:
            def __init__(self, _symbol):
                pass
            def history(self, **_kwargs):
                raise ConnectionError("offline")
        fake.Ticker = BrokenTicker
        with patch.dict(sys.modules, {"yfinance": fake}):
            self.assertEqual(market_quotes({"ETH-USD"}, datetime.now(timezone.utc)), {})


if __name__ == "__main__":
    unittest.main()
