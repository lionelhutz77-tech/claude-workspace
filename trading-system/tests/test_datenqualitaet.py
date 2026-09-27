"""Regressionstests fuer Kursdaten-Qualitaet (NaN-Zeilen, Krypto-IDs, Ersatzquelle)."""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "agents"))

import crypto_analyst  # noqa: E402
import learning_agent  # noqa: E402
import stock_analyst  # noqa: E402


def _kurse(n: int, letzte_nan: bool = False) -> pd.DataFrame:
    close = np.linspace(100, 120, n)
    if letzte_nan:
        close[-1] = np.nan
    return pd.DataFrame({"Close": close, "Open": close, "High": close, "Low": close})


class StockDatenTests(unittest.TestCase):
    def test_leere_tageszeile_ergibt_keinen_nan_preis(self) -> None:
        ticker = MagicMock()
        ticker.history.return_value = _kurse(63, letzte_nan=True)
        with patch.object(stock_analyst.yf, "Ticker", return_value=ticker):
            ergebnis = stock_analyst.analysiere_aktie("TEST")
        self.assertFalse(np.isnan(ergebnis["preis"]))
        self.assertFalse(np.isnan(ergebnis["rsi"]))

    def test_zu_wenig_daten_ist_sichtbarer_fehler(self) -> None:
        ticker = MagicMock()
        ticker.history.return_value = _kurse(10)
        with patch.object(stock_analyst.yf, "Ticker", return_value=ticker):
            with self.assertRaises(ValueError):
                stock_analyst.lade_kursdaten("TEST")


class KryptoDatenTests(unittest.TestCase):
    def test_registrierte_id_wird_statt_kuerzel_genutzt(self) -> None:
        crypto_analyst.registriere_coingecko_id("ZZZ", "zzz-network")
        self.assertEqual(crypto_analyst.KRYPTO_IDS["ZZZ"], "zzz-network")

    def test_coingecko_ausfall_nutzt_yahoo_sichtbar(self) -> None:
        with patch.object(crypto_analyst, "_lade_kursdaten_coingecko", side_effect=Exception("429")), \
             patch.object(crypto_analyst, "_lade_kursdaten_yahoo", return_value=_kurse(90)) as yahoo:
            df = crypto_analyst.lade_kursdaten("ETH")
        yahoo.assert_called_once()
        self.assertEqual(len(df), 90)

    def test_livepreis_faellt_auf_letzten_schlusskurs_zurueck(self) -> None:
        with patch.object(crypto_analyst, "_lade_aktuellen_preis_coingecko", side_effect=Exception("429")):
            live = crypto_analyst.lade_aktuellen_preis("ETH", _kurse(90))
        self.assertAlmostEqual(live["preis"], 120.0)


class AuswertungTests(unittest.TestCase):
    def test_gespeicherter_typ_hat_vorrang(self) -> None:
        self.assertEqual(learning_agent._asset_typ("NEAR", "aktie"), "aktie")
        self.assertEqual(learning_agent._asset_typ("NEAR", None), "krypto")
        self.assertEqual(learning_agent._asset_typ("ABBV", None), "aktie")


if __name__ == "__main__":
    unittest.main()
