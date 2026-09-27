"""Vier voneinander getrennte 10.000-EUR-Paper-Strategien.

Signale werden erst bei einem *spaeteren* Lauf zum beobachteten Kurs ausgefuehrt.
Ohne frischen, waehrungsgesicherten Kurs bleibt die Order offen. Kein Brokerzugriff.
"""

from __future__ import annotations

import hashlib
import json
import math
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping


DB_PATH = Path(__file__).resolve().parents[1] / "data" / "multi_depot.db"
START_EUR = 10_000.0
MAX_POSITION_EUR = 2_000.0
COST_RATE = 0.002  # konservativer kombinierter Kosten-/Slippage-Abschlag je Seite
STRATEGIES = ("KONSENS", "MOMENTUM", "VALUE", "TAILWIND")


@dataclass(frozen=True)
class Quote:
    price_eur: float
    observed_at: str  # UTC ISO-8601; niemals ein nachtraeglich geratener Kurs


def _dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Zeitstempel braucht Zeitzone")
    return parsed.astimezone(timezone.utc)


def _valid_quote(quote: Quote | None, after: str | None = None) -> bool:
    if quote is None or not math.isfinite(quote.price_eur) or quote.price_eur <= 0:
        return False
    try:
        return after is None or _dt(quote.observed_at) > _dt(after)
    except ValueError:
        return False


def _is_buy(signal: dict) -> bool:
    return signal.get("finale", {}).get("empfehlung") == "KAUFEN"


def _kind(signal: dict) -> str:
    return "krypto" if str(signal.get("asset_typ", "aktie")).lower() in {"krypto", "crypto"} else "aktie"


def _quote_symbol(asset: str, kind: str) -> str:
    return f"{asset}-USD" if kind == "krypto" else asset


def _number(value: object, fallback: float = 0.0) -> float:
    try:
        number = float(value)
        return number if math.isfinite(number) else fallback
    except (TypeError, ValueError):
        return fallback


def choose(strategy: str, signals: list[dict]) -> list[dict]:
    """Vorregistrierte Filter; keine Position ohne finales KAUFEN-Votum."""
    if strategy not in STRATEGIES:
        raise ValueError("Unbekannte Strategie")
    buys = [s for s in signals if _is_buy(s) and s.get("asset")]
    if strategy == "KONSENS":
        ranked = sorted(buys, key=lambda s: _number(s.get("gesamt_punkte")), reverse=True)
    elif strategy == "MOMENTUM":
        ranked = sorted(
            [s for s in buys if _number(s.get("momentum_5d")) > 2
             and 50 <= _number(s.get("rsi")) < 70],
            key=lambda s: _number(s.get("momentum_5d")), reverse=True,
        )
    elif strategy == "VALUE":
        ranked = sorted(
            [s for s in buys if 0 < _number(s.get("rsi")) < 40],
            key=lambda s: _number(s.get("rsi"), 100),
        )
    else:
        ranked = sorted(
            [s for s in buys if s.get("tailwind_signal") == "STARK"],
            key=lambda s: _number(s.get("tailwind_score")), reverse=True,
        )
    seen: set[str] = set()
    selected = []
    for signal in ranked:
        asset = str(signal["asset"]).upper()
        instrument = f"{_kind(signal)}:{asset}"
        if instrument not in seen:
            selected.append(signal)
            seen.add(instrument)
        if len(selected) == 5:
            break
    return selected


def initialize(db_path: Path = DB_PATH) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(db_path)) as db:
      with db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS portfolios (
            strategy TEXT PRIMARY KEY, cash_eur REAL NOT NULL,
            started_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY, strategy TEXT NOT NULL, asset TEXT NOT NULL,
            asset_type TEXT NOT NULL DEFAULT 'aktie',
            created_at TEXT NOT NULL, signal_hash TEXT NOT NULL,
            signal_evidence TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending', reason TEXT,
            UNIQUE(strategy, asset, created_at));
        CREATE TABLE IF NOT EXISTS positions (
            id INTEGER PRIMARY KEY, strategy TEXT NOT NULL, asset TEXT NOT NULL,
            asset_type TEXT NOT NULL DEFAULT 'aktie',
            quantity REAL NOT NULL, cost_eur REAL NOT NULL, entry_eur REAL NOT NULL,
            opened_at TEXT NOT NULL, closed_at TEXT, exit_eur REAL, pnl_eur REAL);
        CREATE TABLE IF NOT EXISTS snapshots (
            run_id TEXT NOT NULL, strategy TEXT NOT NULL, observed_at TEXT NOT NULL,
            equity_eur REAL, cash_eur REAL NOT NULL, stale_positions INTEGER NOT NULL,
            PRIMARY KEY(run_id, strategy));
        CREATE TABLE IF NOT EXISTS runs (
            run_id TEXT PRIMARY KEY, observed_at TEXT NOT NULL);
        """)
        # Vorwaertskompatibel mit dem heute bereits angelegten leeren Schema.
        for table in ("orders", "positions"):
            columns = {row[1] for row in db.execute(f"PRAGMA table_info({table})")}
            if "asset_type" not in columns:
                db.execute(f"ALTER TABLE {table} ADD COLUMN asset_type TEXT NOT NULL DEFAULT 'aktie'")
        started = datetime.now(timezone.utc).isoformat()
        for strategy in STRATEGIES:
            db.execute("INSERT OR IGNORE INTO portfolios VALUES (?,?,?)",
                       (strategy, START_EUR, started))


def _hash_signal(signal: dict) -> str:
    return hashlib.sha256(_signal_evidence(signal).encode()).hexdigest()


def _signal_evidence(signal: dict) -> str:
    evidence = {key: signal.get(key) for key in
                ("asset", "gesamt_punkte", "rsi", "momentum_5d",
                 "tailwind_signal", "tailwind_score")}
    evidence["asset_typ"] = _kind(signal)
    evidence["finale"] = signal.get("finale", {}).get("empfehlung")
    return json.dumps(evidence, sort_keys=True, default=str)


def process_run(run_id: str, observed_at: str, signals: list[dict],
                quotes: Mapping[str, Quote], db_path: Path = DB_PATH) -> dict:
    """Idempotenter Tageslauf: alte Orders ausfuehren, Positionen bewerten, neue vormerken."""
    _dt(observed_at)
    if not run_id:
        raise ValueError("run_id fehlt")
    initialize(db_path)
    with closing(sqlite3.connect(db_path)) as db:
        db.row_factory = sqlite3.Row
        with db:
            if db.execute("SELECT 1 FROM runs WHERE run_id=?", (run_id,)).fetchone():
                return {"status": "already_processed", "run_id": run_id}
            previous = db.execute("SELECT MAX(observed_at) FROM runs").fetchone()[0]
            if previous and _dt(observed_at) <= _dt(previous):
                raise ValueError("Rueckdatierter oder doppelter Lauf")
            db.execute("INSERT INTO runs VALUES (?,?)", (run_id, observed_at))
            filled = closed = queued = 0
            for strategy in STRATEGIES:
                cash = float(db.execute("SELECT cash_eur FROM portfolios WHERE strategy=?",
                                        (strategy,)).fetchone()[0])
                open_assets = {f"{row[1]}:{row[0]}" for row in db.execute(
                    "SELECT asset,asset_type FROM positions WHERE strategy=? AND closed_at IS NULL", (strategy,))}
                for order in db.execute(
                    "SELECT * FROM orders WHERE strategy=? AND status='pending' ORDER BY id",
                    (strategy,)).fetchall():
                    asset = order["asset"]
                    kind = order["asset_type"]
                    instrument = f"{kind}:{asset}"
                    quote = quotes.get(_quote_symbol(asset, kind))
                    if (_dt(observed_at) - _dt(order["created_at"])).days >= 3:
                        db.execute("UPDATE orders SET status='cancelled', reason='expired' WHERE id=?",
                                   (order["id"],))
                        continue
                    if instrument in open_assets:
                        db.execute("UPDATE orders SET status='cancelled', reason='already_open' WHERE id=?",
                                   (order["id"],))
                        continue
                    if (not _valid_quote(quote, order["created_at"])
                            or _dt(quote.observed_at) > _dt(observed_at)):
                        continue
                    budget = min(MAX_POSITION_EUR, cash)
                    if budget < 100:
                        continue
                    entry = quote.price_eur * (1 + COST_RATE)
                    quantity = budget / entry
                    db.execute("INSERT INTO positions(strategy,asset,asset_type,quantity,cost_eur,entry_eur,opened_at) "
                               "VALUES (?,?,?,?,?,?,?)",
                               (strategy, asset, kind, quantity, budget, entry, quote.observed_at))
                    db.execute("UPDATE orders SET status='filled' WHERE id=?", (order["id"],))
                    cash -= budget
                    open_assets.add(instrument)
                    filled += 1
                for pos in db.execute(
                    "SELECT * FROM positions WHERE strategy=? AND closed_at IS NULL",
                    (strategy,)).fetchall():
                    quote = quotes.get(_quote_symbol(pos["asset"], pos["asset_type"]))
                    if (not _valid_quote(quote, pos["opened_at"])
                            or _dt(quote.observed_at) > _dt(observed_at)):
                        continue
                    change = quote.price_eur / pos["entry_eur"] - 1
                    age_days = (_dt(quote.observed_at) - _dt(pos["opened_at"])).days
                    if change >= 0.10 or change <= -0.07 or age_days >= 20:
                        proceeds = pos["quantity"] * quote.price_eur * (1 - COST_RATE)
                        db.execute("UPDATE positions SET closed_at=?,exit_eur=?,pnl_eur=? WHERE id=?",
                                   (quote.observed_at, quote.price_eur, proceeds - pos["cost_eur"], pos["id"]))
                        cash += proceeds
                        open_assets.discard(f"{pos['asset_type']}:{pos['asset']}")
                        closed += 1
                db.execute("UPDATE portfolios SET cash_eur=? WHERE strategy=?", (cash, strategy))
                pending = {f"{row[1]}:{row[0]}" for row in db.execute(
                    "SELECT asset,asset_type FROM orders WHERE strategy=? AND status='pending'", (strategy,))}
                for signal in choose(strategy, signals):
                    asset = str(signal["asset"]).upper()
                    kind = _kind(signal)
                    instrument = f"{kind}:{asset}"
                    if instrument in open_assets or instrument in pending:
                        continue
                    db.execute("INSERT INTO orders(strategy,asset,asset_type,created_at,signal_hash,signal_evidence) "
                               "VALUES (?,?,?,?,?,?)",
                               (strategy, asset, kind, observed_at, _hash_signal(signal),
                                _signal_evidence(signal)))
                    pending.add(instrument)
                    queued += 1
                equity = cash
                stale = 0
                for pos in db.execute(
                    "SELECT * FROM positions WHERE strategy=? AND closed_at IS NULL", (strategy,)):
                    quote = quotes.get(_quote_symbol(pos["asset"], pos["asset_type"]))
                    if not _valid_quote(quote) or _dt(quote.observed_at) > _dt(observed_at):
                        stale += 1
                    else:
                        equity += pos["quantity"] * quote.price_eur
                db.execute("INSERT INTO snapshots VALUES (?,?,?,?,?,?)",
                           (run_id, strategy, observed_at, equity if not stale else None, cash, stale))
            return {"status": "processed", "run_id": run_id,
                    "filled": filled, "closed": closed, "queued": queued}


def statistics(db_path: Path = DB_PATH) -> list[dict]:
    initialize(db_path)
    with closing(sqlite3.connect(db_path)) as db:
        db.row_factory = sqlite3.Row
        result = []
        for strategy in STRATEGIES:
            cash = float(db.execute("SELECT cash_eur FROM portfolios WHERE strategy=?",
                                    (strategy,)).fetchone()[0])
            closed = [float(row[0]) for row in db.execute(
                "SELECT pnl_eur FROM positions WHERE strategy=? AND closed_at IS NOT NULL", (strategy,))]
            open_count = int(db.execute("SELECT COUNT(*) FROM positions WHERE strategy=? AND closed_at IS NULL",
                                        (strategy,)).fetchone()[0])
            pending = int(db.execute("SELECT COUNT(*) FROM orders WHERE strategy=? AND status='pending'",
                                     (strategy,)).fetchone()[0])
            snap = db.execute("SELECT equity_eur,stale_positions,observed_at FROM snapshots "
                              "WHERE strategy=? ORDER BY observed_at DESC LIMIT 1", (strategy,)).fetchone()
            equity = snap["equity_eur"] if snap else START_EUR
            peak = START_EUR
            max_drawdown = 0.0
            for history in db.execute("SELECT equity_eur FROM snapshots WHERE strategy=? "
                                      "AND equity_eur IS NOT NULL ORDER BY observed_at", (strategy,)):
                current = float(history[0])
                peak = max(peak, current)
                max_drawdown = max(max_drawdown, (peak - current) / peak * 100)
            result.append({"strategy": strategy, "start_eur": START_EUR, "cash_eur": round(cash, 2),
                           "equity_eur": round(equity, 2) if equity is not None else None,
                           "return_pct": round((equity / START_EUR - 1) * 100, 2) if equity is not None else None,
                           "closed_trades": len(closed), "hit_rate_pct": round(sum(p > 0 for p in closed) / len(closed) * 100, 1) if closed else None,
                           "realized_pnl_eur": round(sum(closed), 2), "open_positions": open_count,
                           "max_drawdown_pct": round(max_drawdown, 2),
                           "pending_orders": pending, "stale_positions": snap["stale_positions"] if snap else 0,
                           "observed_at": snap["observed_at"] if snap else None})
        return result
