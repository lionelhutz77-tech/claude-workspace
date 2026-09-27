"""Marktdaten-Adapter fuer die strikt getrennte 10.000-EUR-Simulation."""

from __future__ import annotations

import re
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path

from agents.experiment_depot import DB_PATH, Quote, initialize, process_run, statistics


def _required_assets(db_path: Path) -> set[str]:
    initialize(db_path)
    with closing(sqlite3.connect(db_path)) as db:
        pending = {f"{row[0]}-USD" if row[1] == "krypto" else row[0]
                   for row in db.execute("SELECT asset,asset_type FROM orders WHERE status='pending'")}
        active = {f"{row[0]}-USD" if row[1] == "krypto" else row[0]
                  for row in db.execute("SELECT asset,asset_type FROM positions WHERE closed_at IS NULL")}
    return pending | active


def market_quotes(assets: set[str], now: datetime) -> dict[str, Quote]:
    """Nur tatsaechliche Kurse mit bekannter USD/EUR-Waehrung liefern.

    Unbekannte Waehrung, veralteter Kurs oder FX-Fehler sperren die Ausfuehrung.
    """
    if not assets:
        return {}
    import yfinance as yf

    try:
        fx = yf.Ticker("USDEUR=X").history(period="7d")
        if fx.empty:
            return {}
        fx_timestamp = fx.index[-1].to_pydatetime().astimezone(timezone.utc)
        usd_eur = float(fx["Close"].iloc[-1])
    except Exception:
        return {}
    if not (0 < usd_eur < 10) or fx_timestamp > now or fx_timestamp < now - timedelta(days=7):
        return {}
    result: dict[str, Quote] = {}
    for asset in sorted(assets):
        if not re.fullmatch(r"[A-Z0-9.^-]{1,20}", asset):
            continue
        try:
            ticker = yf.Ticker(asset)
            history = ticker.history(period="7d")
            if history.empty:
                continue
            stamp = history.index[-1].to_pydatetime().astimezone(timezone.utc)
            if stamp > now or stamp < now - timedelta(days=7):
                continue
            currency = str(ticker.fast_info.currency).upper()
            native = float(history["Close"].iloc[-1])
            if currency == "EUR":
                converted = native
            elif currency == "USD":
                converted = native * usd_eur
            else:
                continue
            if converted > 0:
                result[asset] = Quote(converted, stamp.isoformat())
        except Exception:
            # Einzelne fehlende Kurse duerfen keine Schaetzpreise erzeugen.
            continue
    return result


def run_daily(signals: list[dict], observed_at: str, db_path: Path = DB_PATH) -> tuple[dict, list[dict]]:
    now = datetime.fromisoformat(observed_at.replace("Z", "+00:00")).astimezone(timezone.utc)
    quotes = market_quotes(_required_assets(db_path), now)
    run_id = now.strftime("trading-%Y%m%dT%H%M%SZ")
    outcome = process_run(run_id, observed_at, signals, quotes, db_path)
    return outcome, statistics(db_path)
