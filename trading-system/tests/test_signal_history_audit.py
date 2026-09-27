import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "audit_signal_fusion_history.py"
SPEC = importlib.util.spec_from_file_location("signal_history_audit", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class SignalHistoryAuditTests(unittest.TestCase):
    def test_parses_tailwind_components(self):
        html = """<table><tr><th>Ticker</th><th>Thema</th><th>Score</th><th>Signal</th><th>Kurs</th><th>ATH-Abstand</th><th>News|Rev|Opt|Trend</th></tr>
        <tr><td><strong>ANET</strong></td><td>AI</td><td>65/100</td><td>STARK</td><td>$168.54</td><td>6.3% unter ATH</td><td>30 | 20 | 15 | 0</td></tr></table>"""
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "report_2026-06-18.html"
            path.write_text(html, encoding="utf-8")
            row = MODULE.parse_tailwind_report(path)[0]
        self.assertEqual(row["ticker"], "ANET")
        self.assertEqual(row["score"], 65)
        self.assertEqual(row["components"]["options"], 15)

    def test_parses_daily_report(self):
        text = """  [AKTIE] ANET  --  $164.93
  Technisch    : KAUFEN
  News         : NEUTRAL  (0 Artikel)
  Debatte      : BULL gewinnt
  EMPFEHLUNG   : KAUFEN
  Einstieg     : $164.93
  Ziel         : $200.00
  Stop-Loss    : $150.00
  Risiko       : MITTEL
"""
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bericht_2026-06-18_0857.txt"
            path.write_text(text, encoding="utf-8")
            row = MODULE.parse_daily_report(path)[0]
        self.assertEqual(row["ticker"], "ANET")
        self.assertEqual(row["technical"], "KAUFEN")
        self.assertEqual(row["entry"], 164.93)

    def test_tailwind_replay_marks_implausible_raw_move(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            reports = root / "tailwind-scanner" / "reports"
            reports.mkdir(parents=True)
            output = root / "trading-system" / "output"
            output.mkdir(parents=True)
            data = root / "trading-system" / "data"
            archive = data / "archive" / "cycle"
            archive.mkdir(parents=True)
            (data / "current-cycle.json").write_text(
                '{"previous_cycle_archive":"archive/cycle"}', encoding="utf-8"
            )
            dashboard = root / "lionel-os" / "test-artifacts" / "trading-dashboard"
            dashboard.mkdir(parents=True)
            (dashboard / "trading-gesamtanalyse.json").write_text(
                '{"sources":{}}', encoding="utf-8"
            )
            template = """<table><tr><th>Ticker</th><th>Thema</th><th>Score</th><th>Signal</th><th>Kurs</th><th>ATH-Abstand</th><th>News|Rev|Opt|Trend</th></tr>
            <tr><td><strong>XYZ</strong></td><td>AI</td><td>65/100</td><td>STARK</td><td>${price}</td><td>6.3% unter ATH</td><td>30 | 20 | 15 | 0</td></tr></table>"""
            (reports / "report_2026-06-01.html").write_text(
                template.format(price="100.00"), encoding="utf-8"
            )
            (reports / "report_2026-06-02.html").write_text(
                template.format(price="20.00"), encoding="utf-8"
            )

            with patch.object(MODULE, "load_archived_outcomes", return_value=[]), patch.object(
                MODULE, "load_paper_outcomes", return_value=[]
            ):
                result = MODULE.build_audit(root)

        self.assertEqual(
            result["tailwind_replay"][0]["quality_status"],
            "suspected_corporate_action_or_symbol_discontinuity",
        )


if __name__ == "__main__":
    unittest.main()
