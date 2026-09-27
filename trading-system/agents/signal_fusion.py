"""Canonical, idempotent evidence records for every trading-system decision."""

from __future__ import annotations

import hashlib
import json
import math
import sqlite3
from datetime import datetime, timezone
from typing import Any


CRYPTO_SYMBOLS = {"BTC", "ETH", "SOL", "XRP", "BNB", "ADA", "AAVE", "DOGE", "NEAR", "OKB"}


def instrument_id(asset: object, asset_type: object = None) -> str:
    symbol = str(asset or "").strip().upper()
    if not symbol or not symbol.replace(".", "").replace("-", "").isalnum():
        raise ValueError("ungueltiges Instrument")
    declared = str(asset_type or "").strip().lower()
    kind = "crypto" if declared in {"crypto", "krypto"} or (not declared and symbol in CRYPTO_SYMBOLS) else "equity"
    return f"{kind}:{symbol}"


def _finite(value: object) -> float | None:
    if value in (None, ""):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _canonical_utc(value: str | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("observed_at braucht eine Zeitzone")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def build_evidence_snapshot(signal: dict[str, Any], observed_at: str | None = None) -> dict[str, Any]:
    final = signal.get("finale") if isinstance(signal.get("finale"), dict) else {}
    observed = _canonical_utc(observed_at)
    instrument = instrument_id(signal.get("asset"), signal.get("asset_typ"))
    factors = {
        "technical": signal.get("technisches_signal"),
        "rsi": _finite(signal.get("rsi")),
        "momentum_5d": _finite(signal.get("momentum_5d")),
        "news_sentiment": signal.get("news_sentiment"),
        "news_count": int(signal.get("news_anzahl") or 0),
        "social_sentiment": signal.get("social_sentiment"),
        "tailwind_level": signal.get("tailwind_signal"),
        "tailwind_score": _finite(signal.get("tailwind_score")),
        "tailwind_theme": signal.get("tailwind_thema"),
        "pattern": signal.get("pattern_empfehlung"),
        "volume": signal.get("volume_empfehlung"),
        "relative_volume": _finite(signal.get("rel_volumen")),
        "valuation": signal.get("bewertung") or signal.get("valuation_signal"),
        "sec_signal": signal.get("sec_signal"),
    }
    payload: dict[str, Any] = {
        "schema_version": 1,
        "observed_at": observed,
        "instrument_id": instrument,
        "recommendation": final.get("empfehlung") or signal.get("empfehlung"),
        "entry": _finite(final.get("einstieg", signal.get("preis"))),
        "target": _finite(final.get("ziel")),
        "stop": _finite(final.get("stop_loss")),
        "risk": final.get("risiko"),
        "aggregate_score": _finite(signal.get("gesamt_punkte")),
        "factors": factors,
        "quality": {
            "tailwind_available": factors["tailwind_score"] is not None,
            "news_timestamped": bool(signal.get("news_timestamped", False)),
            "social_calibrated": bool(signal.get("social_calibrated", False)),
            "legacy_learning_used": False,
        },
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    payload["evidence_id"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return payload


def ensure_schema(connection: sqlite3.Connection) -> None:
    connection.execute("""
        CREATE TABLE IF NOT EXISTS signal_evidence_v2 (
            evidence_id TEXT PRIMARY KEY,
            observed_at TEXT NOT NULL,
            instrument_id TEXT NOT NULL,
            recommendation TEXT,
            payload_json TEXT NOT NULL
        )
    """)
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_signal_evidence_v2_instrument_time "
        "ON signal_evidence_v2(instrument_id, observed_at)"
    )


def store_evidence(connection: sqlite3.Connection, snapshot: dict[str, Any]) -> bool:
    ensure_schema(connection)
    cursor = connection.execute(
        "INSERT OR IGNORE INTO signal_evidence_v2 "
        "(evidence_id, observed_at, instrument_id, recommendation, payload_json) VALUES (?,?,?,?,?)",
        (
            snapshot["evidence_id"], snapshot["observed_at"], snapshot["instrument_id"],
            snapshot.get("recommendation"), json.dumps(snapshot, ensure_ascii=False, sort_keys=True),
        ),
    )
    return cursor.rowcount == 1
