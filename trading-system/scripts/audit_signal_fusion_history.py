"""Join legacy Tailwind and daily reports to actually observed paper/simulation outcomes."""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import statistics
from contextlib import closing
from datetime import date, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tables: list[list[list[str]]] = []
        self._table: list[list[str]] | None = None
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "table":
            self._table = []
        elif tag == "tr" and self._table is not None:
            self._row = []
        elif tag in {"td", "th"} and self._row is not None:
            self._cell = []

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self._cell is not None and self._row is not None:
            self._row.append(" ".join("".join(self._cell).split()))
            self._cell = None
        elif tag == "tr" and self._row is not None and self._table is not None:
            self._table.append(self._row)
            self._row = None
        elif tag == "table" and self._table is not None:
            self.tables.append(self._table)
            self._table = None


def _number(value: str) -> float | None:
    match = re.search(r"[-+]?\d[\d,.]*", value.replace("/100", ""))
    if not match:
        return None
    token = match.group(0)
    if token.count(",") == 1 and "." not in token:
        token = token.replace(",", ".")
    else:
        token = token.replace(",", "")
    try:
        return float(token)
    except ValueError:
        return None


def parse_tailwind_report(path: Path) -> list[dict[str, Any]]:
    match = re.fullmatch(r"(?:report|test)_(\d{4}-\d{2}-\d{2})\.html", path.name)
    if not match:
        return []
    parser = _TableParser()
    parser.feed(path.read_text(encoding="utf-8", errors="replace"))
    records: list[dict[str, Any]] = []
    for table in parser.tables:
        if not table or "Ticker" not in table[0] or "Score" not in table[0]:
            continue
        headers = table[0]
        for cells in table[1:]:
            row = dict(zip(headers, cells))
            ticker = str(row.get("Ticker") or "").upper()
            if not ticker:
                continue
            component_text = str(row.get("News|Rev|Opt|Trend") or "")
            components = [_number(part) for part in component_text.split("|")]
            records.append({
                "signal_date": match.group(1),
                "ticker": ticker,
                "theme": row.get("Thema"),
                "score": _number(str(row.get("Score") or "")),
                "level": row.get("Signal"),
                "entry": _number(str(row.get("Einstieg") or row.get("Kurs") or "")),
                "ath_distance_pct": _number(str(row.get("ATH-Abstand") or "")),
                "components": {
                    name: components[index] if index < len(components) else None
                    for index, name in enumerate(("news", "revisions", "options", "trends"))
                },
                "source": path.name,
            })
    return records


def parse_daily_report(path: Path) -> list[dict[str, Any]]:
    match = re.fullmatch(r"bericht_(\d{4}-\d{2}-\d{2})_\d{4}\.txt", path.name)
    if not match:
        return []
    text = path.read_text(encoding="utf-8", errors="replace")
    blocks = re.split(r"(?=^\s*\[(?:AKTIE|KRYPTO)\])", text, flags=re.MULTILINE)
    rows: list[dict[str, Any]] = []
    for block in blocks:
        head = re.search(r"^\s*\[(AKTIE|KRYPTO)\]\s+([A-Z0-9.\-]+)\s+--\s+\$([\d,.]+)", block, re.MULTILINE)
        if not head:
            continue
        field = lambda label: (re.search(rf"^\s*{re.escape(label)}\s*:\s*(.+)$", block, re.MULTILINE) or [None, None])[1]
        rows.append({
            "signal_date": match.group(1),
            "asset_type": "equity" if head.group(1) == "AKTIE" else "crypto",
            "ticker": head.group(2),
            "observed_price": _number(head.group(3)),
            "technical": field("Technisch"),
            "news": field("News"),
            "debate": field("Debatte"),
            "recommendation": field("EMPFEHLUNG"),
            "entry": _number(field("Einstieg") or ""),
            "target": _number(field("Ziel") or ""),
            "stop": _number(field("Stop-Loss") or ""),
            "risk": field("Risiko"),
            "source": path.name,
        })
    return rows


def _iso_date(value: object) -> str | None:
    raw = str(value or "").strip()
    for pattern in ("%Y-%m-%d", "%d.%m.%Y %H:%M:%S", "%d.%m.%Y"):
        try:
            return datetime.strptime(raw[:19] if "%H" in pattern else raw[:10], pattern).date().isoformat()
        except ValueError:
            continue
    return None


def load_archived_outcomes(archive_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with closing(sqlite3.connect(f"file:{(archive_dir / 'portfolio.db').resolve().as_posix()}?mode=ro", uri=True)) as db:
        db.row_factory = sqlite3.Row
        for item in db.execute("SELECT * FROM positionen WHERE status != 'offen'"):
            rows.append({"platform": "simulation", "strategy": "PORTFOLIO", "asset": item["asset"],
                         "opened_at": _iso_date(item["eroeffnet_am"]), "pnl_pct": item["pnl_pct"]})
    with closing(sqlite3.connect(f"file:{(archive_dir / 'multi_depot.db').resolve().as_posix()}?mode=ro", uri=True)) as db:
        db.row_factory = sqlite3.Row
        for item in db.execute("SELECT * FROM positionen WHERE status != 'offen'"):
            rows.append({"platform": "simulation", "strategy": item["strategie"], "asset": item["asset"],
                         "opened_at": _iso_date(item["eroeffnet_am"]), "pnl_pct": item["pnl_pct"]})
    return rows


def load_paper_outcomes(snapshot_path: Path) -> list[dict[str, Any]]:
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    return [
        {"platform": "alpaca_paper", "strategy": item["strategy"], "asset": item["asset"],
         "opened_at": _iso_date(item["opened_at"]), "pnl_pct": item["pnl_pct"]}
        for item in snapshot.get("positions", []) if item.get("evidence_class") == "executed_paper"
    ]


def build_audit(root: Path) -> dict[str, Any]:
    tailwind = [row for path in sorted((root / "tailwind-scanner" / "reports").glob("*.html")) for row in parse_tailwind_report(path)]
    daily = [row for path in sorted((root / "trading-system" / "output").glob("bericht_*.txt")) for row in parse_daily_report(path)]
    cycle = json.loads((root / "trading-system" / "data" / "current-cycle.json").read_text(encoding="utf-8"))
    archive = root / "trading-system" / "data" / cycle["previous_cycle_archive"]
    outcomes = load_archived_outcomes(archive) + load_paper_outcomes(
        root / "lionel-os" / "test-artifacts" / "trading-dashboard" / "trading-gesamtanalyse.json"
    )
    daily_index = {(row["signal_date"], row["ticker"]): row for row in daily}
    tailwind_by_ticker: dict[str, list[dict[str, Any]]] = {}
    for row in tailwind:
        tailwind_by_ticker.setdefault(row["ticker"], []).append(row)
    tailwind_replay = []
    for ticker, ticker_rows in tailwind_by_ticker.items():
        ordered = sorted(ticker_rows, key=lambda row: row["signal_date"])
        first = next((row for row in ordered if row.get("entry")), None)
        last = next((row for row in reversed(ordered) if row.get("entry") and row["signal_date"] > (first or {}).get("signal_date", "")), None)
        if first is None or last is None or not first["entry"]:
            continue
        replay_return = round((float(last["entry"]) / float(first["entry"]) - 1) * 100, 2)
        tailwind_replay.append({
            "ticker": ticker,
            "theme": first["theme"],
            "first_date": first["signal_date"],
            "last_date": last["signal_date"],
            "first_score": first["score"],
            "first_level": first["level"],
            "return_pct": replay_return,
            "observations": len(ordered),
            "quality_status": (
                "suspected_corporate_action_or_symbol_discontinuity"
                if abs(replay_return) > 50
                else "raw_report_price_unadjusted"
            ),
        })
    matches = []
    for outcome in outcomes:
        opened = outcome["opened_at"]
        report = daily_index.get((opened, outcome["asset"])) if opened else None
        fresh_tailwind = None
        if opened:
            opened_date = date.fromisoformat(opened)
            candidates = [row for row in tailwind_by_ticker.get(outcome["asset"], [])
                          if 0 <= (opened_date - date.fromisoformat(row["signal_date"])).days <= 3]
            if candidates:
                fresh_tailwind = max(candidates, key=lambda row: row["signal_date"])
        matches.append({**outcome, "daily_report": report, "tailwind": fresh_tailwind})
    closed_simulation = [row for row in matches if row["platform"] == "simulation"]
    paper = [row for row in matches if row["platform"] == "alpaca_paper"]
    report_matched = [row for row in closed_simulation if row["daily_report"]]
    report_winners = [row for row in report_matched if float(row["pnl_pct"] or 0) > 0]

    def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
        returns = [float(row["pnl_pct"]) for row in rows]
        return {
            "count": len(returns),
            "positive": sum(value > 0 for value in returns),
            "positive_rate_pct": round(sum(value > 0 for value in returns) / len(returns) * 100, 1) if returns else None,
            "mean_return_pct": round(statistics.mean(returns), 2) if returns else None,
        }

    recommendation_performance = {}
    technical_performance = {}
    for row in report_matched:
        recommendation_performance.setdefault(row["daily_report"]["recommendation"], []).append(row)
        technical_performance.setdefault(row["daily_report"]["technical"], []).append(row)

    tailwind_level_replay = {}
    for level in ("STARK", "MODERAT", "SCHWACH"):
        rows = [
            {"pnl_pct": row["return_pct"]}
            for row in tailwind_replay
            if row["first_level"] == level
            and row["quality_status"] == "raw_report_price_unadjusted"
        ]
        tailwind_level_replay[level] = summarize(rows)
    return {
        "schema_version": 2,
        "method": "point_in_time_report_join_without_market_data_refetch",
        "limitations": [
            "Tailwind replay uses raw report prices and is not adjusted for splits or symbol changes.",
            "Matched observations are retrospective associations, not proof of causality.",
            "No fresh Tailwind match means its effect on executed trades cannot be inferred.",
        ],
        "sources": {"tailwind_reports": len({row["source"] for row in tailwind}),
                    "tailwind_rows": len(tailwind), "daily_reports": len({row["source"] for row in daily}),
                    "daily_rows": len(daily)},
        "summary": {
            "closed_simulation_outcomes": len(closed_simulation),
            "simulation_daily_report_matches": len(report_matched),
            "simulation_daily_report_positive": len(report_winners),
            "fresh_tailwind_matches_all_outcomes": sum(row["tailwind"] is not None for row in matches),
            "paper_outcomes": len(paper),
            "paper_daily_report_matches": sum(row["daily_report"] is not None for row in paper),
            "paper_tailwind_matches": sum(row["tailwind"] is not None for row in paper),
            "tailwind_replay_tickers": len(tailwind_replay),
        },
        "report_performance": {
            "final_recommendation": {
                key: summarize(rows) for key, rows in sorted(recommendation_performance.items())
            },
            "technical_signal": {
                key: summarize(rows) for key, rows in sorted(technical_performance.items())
            },
        },
        "tailwind_level_replay": tailwind_level_replay,
        "tailwind_replay": sorted(tailwind_replay, key=lambda row: row["return_pct"], reverse=True),
        "matches": matches,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "HISTORICAL_SIGNAL_FUSION_AUDIT.json")
    args = parser.parse_args()
    audit = build_audit(args.root.resolve())
    args.output.write_text(json.dumps(audit, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(audit["summary"], ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
