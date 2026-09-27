import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from portfolio_market_review import gate, rsi, run, summarize_chart, yahoo_symbol


class MarketReviewTests(unittest.TestCase):
    def test_private_symbols_never_leave_without_gate(self):
        with self.assertRaises(PermissionError):
            run()

    def test_symbols(self):
        self.assertEqual(yahoo_symbol("BTC", "crypto"), "BTC-USD")
        self.assertEqual(yahoo_symbol("WAF.DE", "stock"), "WAF.DE")
        self.assertIsNone(yahoo_symbol("copytrader", "copy"))

    def test_rsi_flat(self):
        self.assertEqual(rsi([100] * 20), 50)

    def test_bear_gate(self):
        m = {"age_hours": 1, "price": 80, "ma50": 90, "ma200": 100,
             "return_20d_pct": -8, "rsi14": 30}
        self.assertEqual(gate(m, "stock", 1)[0], "EXIT_PRUEFEN")

    def test_stale_blocks_even_when_bearish(self):
        m = {"age_hours": 150, "price": 80, "ma50": 90, "ma200": 100,
             "return_20d_pct": -8, "rsi14": 30}
        self.assertEqual(gate(m, "stock", 1)[0], "KEIN_URTEIL")

    def test_concentration_gate(self):
        m = {"age_hours": 1, "price": 110, "ma50": 100, "ma200": 90,
             "return_20d_pct": 5, "rsi14": 60}
        self.assertEqual(gate(m, "crypto", 12)[0], "KLUMPEN_PRUEFEN")

    def test_chart_summary(self):
        closes = [float(i) for i in range(100, 351)]
        payload = {"chart":{"result":[{"meta":{"regularMarketPrice":350,
            "regularMarketTime":1720000000,"currency":"USD"},
            "indicators":{"quote":[{"close":closes}]}}]}}
        m = summarize_chart(payload, "2024-07-03T12:00:00+00:00")
        self.assertEqual(m["points"], 251)
        self.assertGreater(m["ma50"], m["ma200"])


if __name__ == "__main__":
    unittest.main()
