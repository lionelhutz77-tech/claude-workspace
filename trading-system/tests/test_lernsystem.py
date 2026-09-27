"""Tests fuer News-Digest und Sonntags-Review (reine Logik, ohne Netz)."""

import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "agents"))

import news_digest  # noqa: E402
import weekly_review  # noqa: E402


class ReviewLogikTests(unittest.TestCase):
    def test_wochenrendite_nutzt_letzten_wert_vor_wochenbeginn(self) -> None:
        verlauf = [("2026-09-18", 1000.0), ("2026-09-20", 1010.0), ("2026-09-25", 1030.2)]
        self.assertAlmostEqual(weekly_review._wochen_rendite(verlauf, "2026-09-20"), 2.0, places=3)

    def test_news_zuordnung_ignoriert_englisches_are(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "news_archive.db"
            conn = sqlite3.connect(db)
            conn.execute("CREATE TABLE artikel (id, quelle, titel, teaser, url, veroeffentlicht, gesammelt_am, assets)")
            conn.executemany("INSERT INTO artikel VALUES (?,?,?,?,?,?,?,?)", [
                ("1", "X", "Stocks are rising today", "", "", "2026-09-22", "", "[]"),
                ("2", "X", "ARE shares drop after guidance cut", "", "", "2026-09-23", "", "[]"),
                ("3", "X", "Bitcoin rallies", "", "", "2026-09-23", "", json.dumps(["BTC"])),
            ])
            conn.commit()
            conn.close()
            with patch.object(weekly_review, "DATA", Path(tmp)):
                are = weekly_review.news_zu("ARE", "2026-09-20")
                btc = weekly_review.news_zu("BTC", "2026-09-20")
        self.assertEqual(len(are), 1)
        self.assertIn("guidance cut", are[0])
        self.assertEqual(len(btc), 1)


class DigestLogikTests(unittest.TestCase):
    def test_zeitpunkt_rfc822_wird_utc(self) -> None:
        eintrag = {"published": "Sun, 27 Sep 2026 11:00:01 +0200"}
        self.assertEqual(news_digest._zeitpunkt(eintrag), "2026-09-27T09:00:01+00:00")

    def test_ausgefallener_fear_greed_wird_nicht_als_neutral_gemeldet(self) -> None:
        text = news_digest._kennzahlen_text({"Fear&Greed Aktien": {"score": 50, "label": "Neutral", "fehler": "x"}})
        self.assertIn("nicht verfuegbar", text)


if __name__ == "__main__":
    unittest.main()
