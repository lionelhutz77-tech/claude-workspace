"""Sicherer Neustart der virtuellen Trading-Depots.

Vor dem Reset wird ein konsistentes, hashgebundenes Archiv aller lokalen
Trading-Datenbanken erzeugt. Learnings und Marktsignale bleiben im aktiven System
erhalten; zurückgesetzt werden ausschließlich die beiden virtuellen Depotbücher.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
STARTKAPITAL = 1_000.0
MULTI_STARTKAPITAL = 1_000.0
ARCHIVE_DATABASES = ("portfolio.db", "multi_depot.db", "learnings.db", "market_memory.db")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def archive_current_cycle(data_dir: Path, archive_dir: Path, captured_at: str) -> dict[str, object]:
    """Create transactionally consistent SQLite backups and a digest manifest."""
    archive_dir.mkdir(parents=True, exist_ok=False)
    files: list[dict[str, object]] = []
    for name in ARCHIVE_DATABASES:
        source_path = data_dir / name
        if not source_path.is_file():
            continue
        target_path = archive_dir / name
        with closing(sqlite3.connect(f"file:{source_path.resolve().as_posix()}?mode=ro", uri=True)) as source:
            with closing(sqlite3.connect(target_path)) as target:
                source.backup(target)
        files.append({
            "name": name,
            "bytes": target_path.stat().st_size,
            "sha256": _sha256(target_path),
        })
    required = {"portfolio.db", "multi_depot.db"}
    present = {str(item["name"]) for item in files}
    if not required.issubset(present):
        raise FileNotFoundError(f"Pflichtdatenbanken fehlen: {sorted(required - present)}")
    manifest: dict[str, object] = {
        "schema_version": 1,
        "captured_at": captured_at,
        "purpose": "pre_reset_virtual_trading_cycle",
        "files": files,
    }
    _atomic_json(archive_dir / "manifest.json", manifest)
    return manifest


def reset_portfolio(db_path: Path, started_at: datetime) -> None:
    with closing(sqlite3.connect(db_path)) as connection:
        with connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("DELETE FROM positionen")
            connection.execute("DELETE FROM depot_verlauf")
            connection.execute("DELETE FROM sqlite_sequence WHERE name='positionen'")
            values = {
                "cash": str(STARTKAPITAL),
                "startkapital": str(STARTKAPITAL),
                "erstellt_am": started_at.strftime("%Y-%m-%d"),
            }
            for key, value in values.items():
                connection.execute(
                    "UPDATE depot_config SET wert=? WHERE schluessel=?",
                    (value, key),
                )
            connection.execute(
                "INSERT INTO depot_verlauf (datum, depotwert, cash, positionen, tagesrendite) "
                "VALUES (?,?,?,?,?)",
                (started_at.strftime("%Y-%m-%d"), STARTKAPITAL, STARTKAPITAL, 0, 0.0),
            )


def reset_multi_depot(db_path: Path, started_at: datetime) -> int:
    with closing(sqlite3.connect(db_path)) as connection:
        with connection:
            connection.execute("BEGIN IMMEDIATE")
            strategies = [row[0] for row in connection.execute("SELECT strategie FROM depots ORDER BY strategie")]
            connection.execute("DELETE FROM positionen")
            connection.execute("DELETE FROM verlauf")
            connection.execute("DELETE FROM sqlite_sequence WHERE name='positionen'")
            for strategy in strategies:
                connection.execute(
                    "UPDATE depots SET cash=?, erstellt_am=? WHERE strategie=?",
                    (MULTI_STARTKAPITAL, started_at.strftime("%Y-%m-%d %H:%M:%S"), strategy),
                )
                connection.execute(
                    "INSERT INTO verlauf (datum, strategie, depotwert, pnl_eur, pnl_pct) VALUES (?,?,?,?,?)",
                    (started_at.strftime("%Y-%m-%d"), strategy, MULTI_STARTKAPITAL, 0.0, 0.0),
                )
    return len(strategies)


def count_learnings(db_path: Path) -> int:
    total = 0
    with closing(sqlite3.connect(f"file:{db_path.resolve().as_posix()}?mode=ro", uri=True)) as connection:
        tables = [
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
        ]
        for table in tables:
            if not table.replace("_", "").isalnum():
                raise ValueError("Unerwarteter Tabellenname in learnings.db")
            total += int(connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
    return total


def perform_reset(data_dir: Path, archive_root: Path, now: datetime) -> dict[str, object]:
    timestamp = now.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    captured_at = now.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    archive_dir = archive_root / f"cycle-before-{timestamp}"
    manifest = archive_current_cycle(data_dir, archive_dir, captured_at)
    reset_portfolio(data_dir / "portfolio.db", now)
    strategy_count = reset_multi_depot(data_dir / "multi_depot.db", now)
    cycle = {
        "schema_version": 1,
        "cycle_id": f"virtual-cycle-{timestamp}",
        "started_at": captured_at,
        "mode": "simulation_only",
        "orders_enabled": False,
        "legacy_portfolio_start_eur": STARTKAPITAL,
        "multi_depot_start_eur_per_strategy": MULTI_STARTKAPITAL,
        "multi_depot_strategy_count": strategy_count,
        "previous_cycle_archive": archive_dir.relative_to(data_dir).as_posix(),
        "preserved_learning_records": count_learnings(data_dir / "learnings.db"),
    }
    _atomic_json(data_dir / "current-cycle.json", cycle)
    return {"archive": str(archive_dir), "manifest": manifest, "cycle": cycle}


def main() -> int:
    parser = argparse.ArgumentParser(description="Virtuelle Depots archivieren und auf null setzen")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Reset wirklich ausführen; ohne diesen Schalter bleibt der Aufruf read-only.",
    )
    args = parser.parse_args()
    if not args.execute:
        print("VORSCHAU: portfolio.db und multi_depot.db würden archiviert und zurückgesetzt.")
        print("Learnings, Marktsignale und Alpaca Paper bleiben unverändert.")
        return 0

    result = perform_reset(DATA_DIR, DATA_DIR / "archive", datetime.now(timezone.utc))
    cycle = result["cycle"]
    print("Reset abgeschlossen.")
    print(f"Archiv: {result['archive']}")
    print(f"Neuer Zyklus: {cycle['cycle_id']}")
    print(f"Startkapital: {STARTKAPITAL:.2f} EUR je virtuellem Depot")
    print(f"Erhaltene Learning-Datensätze: {cycle['preserved_learning_records']}")
    print("Alpaca Paper wurde nicht verändert.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
