"""Tests fuer die regelbasierten Strategiearme (Stufe 4) mit synthetischen Kursen."""

import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import strategie_arme as sa  # noqa: E402


def _reihe(preise: list[float], start: str = "2025-01-01") -> pd.DataFrame:
    idx = pd.date_range(start, periods=len(preise), freq="D")
    close = pd.Series(preise, index=idx, dtype=float)
    return sa.kennzahlen(pd.DataFrame({"High": close * 1.01, "Low": close * 0.99, "Close": close}))


class StrategieArmeTests(unittest.TestCase):
    def setUp(self) -> None:
        self._handelbar = sa.HANDELBAR
        sa.HANDELBAR = ["AAA"]

    def tearDown(self) -> None:
        sa.HANDELBAR = self._handelbar

    def test_ausbruch_wird_erst_am_folgetag_mit_kosten_ausgefuehrt(self) -> None:
        preise = list(np.linspace(50, 100, 230)) + [110.0, 112.0]
        daten = {"AAA": _reihe(preise)}
        arm = sa.Arm("TREND")
        tage = daten["AAA"].index
        sa.schritt(arm, tage[-2], daten)           # Signal am Ausbruchstag
        self.assertEqual(arm.positionen, {})
        self.assertEqual(arm.auftraege[0]["symbol"], "AAA")
        sa.schritt(arm, tage[-1], daten)           # Ausfuehrung zum Folgeschluss
        pos = arm.positionen["AAA"]
        self.assertEqual(pos.einstieg, 112.0)
        self.assertAlmostEqual(arm.cash, sa.START_USD - pos.menge * 112.0 * (1 + sa.KOSTEN), places=6)
        # Groesse wird am Signaltag (Schluss 110) festgelegt, ohne Vorausschau auf den Fuellkurs.
        self.assertLessEqual(pos.menge * 110.0, sa.START_USD * 0.20 + 1e-6)

    def test_stop_schliesst_long_position_mit_verlust(self) -> None:
        preise = list(np.linspace(50, 100, 230)) + [110.0, 112.0, 90.0, 89.0]
        daten = {"AAA": _reihe(preise)}
        arm = sa.Arm("TREND")
        for tag in daten["AAA"].index[-4:]:
            sa.schritt(arm, tag, daten)
        self.assertEqual(arm.positionen, {})
        self.assertEqual(len(arm.trades), 1)
        self.assertLess(arm.trades[0]["pnl"], 0)

    def test_short_gewinnt_bei_fallendem_kurs(self) -> None:
        arm = sa.Arm("SHORT")
        pos = sa.Position("AAA", -10.0, 100.0, 110.0, 100.0, "2025-01-01")
        arm.positionen["AAA"] = pos
        arm.cash += 10 * 100.0 * (1 - sa.KOSTEN)
        sa._schliessen(arm, pos, 80.0, "2025-01-10", "Test")
        self.assertGreater(arm.trades[0]["pnl"], 190)
        self.assertAlmostEqual(arm.cash, sa.START_USD + 1000 * (1 - sa.KOSTEN) - 800 * (1 + sa.KOSTEN))

    def test_regime_short_handelt_nicht_im_bullenmarkt(self) -> None:
        fallend = list(np.linspace(200, 100, 230)) + [90.0]
        steigend = list(np.linspace(100, 200, 231))
        daten = {"AAA": _reihe(fallend), "SPY": _reihe(steigend)}
        arm_regime, arm_frei = sa.Arm("SHORT_REGIME"), sa.Arm("SHORT")
        tag = daten["AAA"].index[-1]
        sa.schritt(arm_regime, tag, daten)
        sa.schritt(arm_frei, tag, daten)
        self.assertEqual(arm_regime.auftraege, [])
        self.assertEqual(arm_frei.auftraege[0]["symbol"], "AAA")


if __name__ == "__main__":
    unittest.main()
