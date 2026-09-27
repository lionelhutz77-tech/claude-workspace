import os
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch


AGENTS_DIR = Path(__file__).resolve().parents[1] / "agents"
sys.path.insert(0, str(AGENTS_DIR))

import multi_depot
from multi_depot import filtere_fuer_strategie
from tailwind_connector import wende_tailwind_bonus_an


class TailwindFusionTests(unittest.TestCase):
    def test_tailwind_is_annotated_without_changing_main_score(self):
        signal = {"asset": "ABC", "gesamt_punkte": 7, "begruendung": []}
        tailwind = {
            "ABC": {
                "signal_stufe": "STARK",
                "gesamt_score": 70,
                "thema": "Test",
                "kurs_info": {"abstand_ath_prozent": 20},
                "details": {"options": {}, "revisions": {}},
            }
        }

        with patch.dict(os.environ, {}, clear=True):
            result = wende_tailwind_bonus_an(signal, tailwind)

        self.assertEqual(result["gesamt_punkte"], 7)
        self.assertEqual(result["tailwind_signal"], "STARK")
        self.assertEqual(result["tailwind_bonus_applied"], 0)
        self.assertNotIn("tailwind_signal", signal)

    def test_tailwind_arm_only_selects_strong_signals_by_score(self):
        signals = [
            {"asset": "LOW", "tailwind_signal": "MODERAT", "tailwind_score": 99},
            {"asset": "A", "tailwind_signal": "STARK", "tailwind_score": 60},
            {"asset": "B", "tailwind_signal": "STARK", "tailwind_score": 80},
        ]

        result = filtere_fuer_strategie("TAILWIND", signals)

        self.assertEqual([item["asset"] for item in result], ["B", "A"])

    def test_new_strategy_gets_initial_valuation(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(
            multi_depot, "DB_PFAD", str(Path(folder) / "multi.db")
        ):
            multi_depot.initialisiere()
            with closing(sqlite3.connect(multi_depot.DB_PFAD)) as db:
                row = db.execute(
                    "SELECT depotwert, pnl_eur FROM verlauf WHERE strategie='TAILWIND'"
                ).fetchone()

        self.assertEqual(row, (1000.0, 0.0))


if __name__ == "__main__":
    unittest.main()
