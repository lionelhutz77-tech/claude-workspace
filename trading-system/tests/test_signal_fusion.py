import json
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "agents"))

from signal_fusion import build_evidence_snapshot, ensure_schema, instrument_id, store_evidence  # noqa: E402


class SignalFusionTests(unittest.TestCase):
    def test_typed_instruments_prevent_near_collision(self):
        self.assertEqual(instrument_id("NEAR", "krypto"), "crypto:NEAR")
        self.assertEqual(instrument_id("NEAR", "aktie"), "equity:NEAR")
        self.assertNotEqual(instrument_id("NEAR", "krypto"), instrument_id("NEAR", "aktie"))

    def test_snapshot_binds_all_available_sources_without_claiming_quality(self):
        snapshot = build_evidence_snapshot({
            "asset": "ANET", "asset_typ": "aktie", "technisches_signal": "KAUFEN",
            "news_sentiment": "neutral", "news_anzahl": 0, "social_sentiment": "neutral",
            "tailwind_signal": "STARK", "tailwind_score": 65, "tailwind_thema": "AI Networking",
            "pattern_empfehlung": "KAUFEN", "volume_empfehlung": "NEUTRAL", "gesamt_punkte": 4,
            "finale": {"empfehlung": "KAUFEN", "einstieg": 100, "ziel": 110, "stop_loss": 95},
        }, "2026-09-20T10:00:00Z")
        self.assertEqual(snapshot["instrument_id"], "equity:ANET")
        self.assertEqual(snapshot["factors"]["tailwind_score"], 65)
        self.assertFalse(snapshot["quality"]["news_timestamped"])
        self.assertFalse(snapshot["quality"]["legacy_learning_used"])

    def test_storage_is_idempotent(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "memory.db"
            snapshot = build_evidence_snapshot(
                {"asset": "BTC", "asset_typ": "krypto", "finale": {"empfehlung": "ABWARTEN"}},
                "2026-09-20T10:00:00Z",
            )
            with closing(sqlite3.connect(path)) as connection:
                ensure_schema(connection)
                self.assertTrue(store_evidence(connection, snapshot))
                self.assertFalse(store_evidence(connection, snapshot))
                row = connection.execute("SELECT payload_json FROM signal_evidence_v2").fetchone()
            self.assertEqual(json.loads(row[0])["instrument_id"], "crypto:BTC")


if __name__ == "__main__":
    unittest.main()
