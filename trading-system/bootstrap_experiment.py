"""Einmaliger Start aus den heute bereits protokollierten Signalen.

Nur Vormerkung; keine Kurse, Brokerorders oder Rueckdatierung von Ausfuehrungen.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from agents.experiment_depot import DB_PATH, initialize, process_run
from experiment_status import REPORT, render_report
from agents.experiment_depot import statistics


SOURCE = Path(__file__).resolve().parent / "data" / "market_memory.db"


def bootstrap(now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    initialize(DB_PATH)
    with closing(sqlite3.connect(DB_PATH)) as db:
        if db.execute("SELECT 1 FROM runs LIMIT 1").fetchone():
            return {"status": "already_started"}
    with closing(sqlite3.connect(f"file:{SOURCE.resolve().as_posix()}?mode=ro", uri=True)) as db:
        rows = db.execute(
            "SELECT payload_json FROM signal_evidence_v2 WHERE observed_at>=? "
            "AND observed_at<=? ORDER BY observed_at DESC",
            ((now.replace(hour=0, minute=0, second=0, microsecond=0)).isoformat(),
             now.isoformat()),
        ).fetchall()
    latest: dict[str, dict] = {}
    for (raw,) in rows:
        evidence = json.loads(raw)
        latest.setdefault(evidence["instrument_id"], evidence)
    signals = []
    for evidence in latest.values():
        factors = evidence.get("factors") or {}
        kind, asset = evidence["instrument_id"].split(":", 1)
        signals.append({
            "asset": asset, "asset_typ": "krypto" if kind == "crypto" else "aktie",
            "finale": {"empfehlung": evidence.get("recommendation")},
            "gesamt_punkte": evidence.get("aggregate_score"),
            "rsi": factors.get("rsi"), "momentum_5d": factors.get("momentum_5d"),
            "tailwind_signal": factors.get("tailwind_level"),
            "tailwind_score": factors.get("tailwind_score"),
        })
    observed_at = now.astimezone(timezone.utc).isoformat()
    result = process_run("bootstrap-" + now.strftime("%Y%m%dT%H%M%SZ"),
                         observed_at, signals, {})
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(render_report(statistics()), encoding="utf-8")
    return {**result, "signals_seen": len(signals)}


if __name__ == "__main__":
    print(bootstrap())
