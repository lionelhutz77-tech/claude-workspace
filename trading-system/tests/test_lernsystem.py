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
import tailwind_kontext  # noqa: E402
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


class TailwindKontextTests(unittest.TestCase):
    def test_report_zeilen_beider_formate_werden_gelesen(self) -> None:
        alt = ('<tr> <td><strong>ANET</strong></td> <td>AI Networking</td> <td style="x">70/100</td> '
               '<td><span style="y">STARK</span></td> <td>$170.68</td> <td>5.1% unter ATH</td> </tr>')
        neu = ('<tr> <td><strong>KTOS</strong></td> <td>Defense Tech / Drohnen</td> <td style="x">42/100</td> '
               '<td><span style="y">MODERAT</span></td> <td>$1,047.02</td> <td>$102.76</td> </tr>')
        zeilen = tailwind_kontext.parse_report(alt + neu)
        self.assertEqual([z["ticker"] for z in zeilen], ["ANET", "KTOS"])
        self.assertEqual(zeilen[1]["stufe"], "MODERAT")
        self.assertAlmostEqual(zeilen[1]["kurs"], 1047.02)

    def test_statistik_zaehlt_je_aktie_und_woche_nur_erstes_signal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(tailwind_kontext, "DB_PFAD", Path(tmp) / "t.db"):
                conn = tailwind_kontext._db()
                for tag, r in (("2026-09-21", 5.0), ("2026-09-22", 50.0), ("2026-09-23", 50.0)):
                    conn.execute("INSERT INTO signale VALUES (?, 'X', 'T', 60, 'STARK', 1, ?, ?, 0, 0)",
                                 (tag, r, r))
                werte = tailwind_kontext.auswertung_je_stufe(conn)
                conn.close()
        self.assertEqual(werte[0]["anzahl"], 1)
        self.assertAlmostEqual(werte[0]["mehr_10t"], 5.0)


if __name__ == "__main__":
    unittest.main()
