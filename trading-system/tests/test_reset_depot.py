import json
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))

from reset_depot import perform_reset  # noqa: E402


class ResetDepotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.data = Path(self.temp.name) / "data"
        self.data.mkdir()
        self._portfolio_db()
        self._multi_db()
        self._simple_db("learnings.db", "lehren", 3)
        self._simple_db("market_memory.db", "signale", 2)

    def tearDown(self):
        self.temp.cleanup()

    def _portfolio_db(self):
        with closing(sqlite3.connect(self.data / "portfolio.db")) as connection:
            with connection:
                connection.executescript("""
                CREATE TABLE positionen (id INTEGER PRIMARY KEY AUTOINCREMENT, asset TEXT);
                INSERT INTO positionen(asset) VALUES ('ALT');
                CREATE TABLE depot_verlauf (datum TEXT, depotwert REAL, cash REAL, positionen INTEGER, tagesrendite REAL);
                INSERT INTO depot_verlauf VALUES ('2026-01-01', 1100, 100, 1, 10);
                CREATE TABLE depot_config (schluessel TEXT PRIMARY KEY, wert TEXT);
                INSERT INTO depot_config VALUES ('cash','100'),('startkapital','1000'),('erstellt_am','2026-01-01');
                """)

    def _multi_db(self):
        with closing(sqlite3.connect(self.data / "multi_depot.db")) as connection:
            with connection:
                connection.executescript("""
                CREATE TABLE depots (strategie TEXT PRIMARY KEY, cash REAL, erstellt_am TEXT);
                INSERT INTO depots VALUES ('A',900,'2026-01-01'),('B',800,'2026-01-01');
                CREATE TABLE positionen (id INTEGER PRIMARY KEY AUTOINCREMENT, strategie TEXT, asset TEXT);
                INSERT INTO positionen(strategie,asset) VALUES ('A','ALT');
                CREATE TABLE verlauf (datum TEXT, strategie TEXT, depotwert REAL, pnl_eur REAL, pnl_pct REAL, PRIMARY KEY(datum,strategie));
                INSERT INTO verlauf VALUES ('2026-01-01','A',900,-100,-10);
                """)

    def _simple_db(self, name, table, rows):
        with closing(sqlite3.connect(self.data / name)) as connection:
            with connection:
                connection.execute(f"CREATE TABLE {table} (id INTEGER)")
                connection.executemany(f"INSERT INTO {table} VALUES (?)", [(n,) for n in range(rows)])

    def test_reset_archives_old_state_and_starts_clean_cycle(self):
        result = perform_reset(
            self.data,
            self.data / "archive",
            datetime(2026, 9, 20, 8, 0, tzinfo=timezone.utc),
        )
        archive = Path(result["archive"])
        manifest = json.loads((archive / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual({row["name"] for row in manifest["files"]}, {
            "portfolio.db", "multi_depot.db", "learnings.db", "market_memory.db"
        })
        with closing(sqlite3.connect(archive / "portfolio.db")) as connection:
            self.assertEqual(connection.execute("SELECT asset FROM positionen").fetchone()[0], "ALT")
        with closing(sqlite3.connect(self.data / "portfolio.db")) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM positionen").fetchone()[0], 0)
            self.assertEqual(connection.execute("SELECT depotwert FROM depot_verlauf").fetchone()[0], 1000)
        with closing(sqlite3.connect(self.data / "multi_depot.db")) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM positionen").fetchone()[0], 0)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM verlauf").fetchone()[0], 2)
            self.assertEqual(connection.execute("SELECT MIN(cash) FROM depots").fetchone()[0], 1000)
        self.assertEqual(result["cycle"]["preserved_learning_records"], 3)
        self.assertFalse(result["cycle"]["orders_enabled"])


if __name__ == "__main__":
    unittest.main()
