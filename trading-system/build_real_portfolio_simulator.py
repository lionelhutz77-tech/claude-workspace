"""Erzeugt ein vollständig lokales, offline nutzbares Depot-Was-wäre-wenn-Dashboard."""

from __future__ import annotations

import json
import argparse
import math
import sqlite3
from datetime import datetime
from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PRIVATE = ROOT / "private" / "real_portfolio_2026-09-21.json"
OUTPUT = ROOT / "output" / "real_portfolio_simulator.html"
MEMORY = ROOT / "data" / "market_memory.db"


def local_review_rows(data: dict, memory: Path = MEMORY) -> str:
    latest: dict[str, tuple] = {}
    if memory.exists():
        with sqlite3.connect(f"file:{memory.as_posix()}?mode=ro", uri=True) as db:
            rows = db.execute("""SELECT asset,datum,empfehlung,tech_signal,news_sentiment
                                 FROM tages_signale ORDER BY datum DESC,id DESC""").fetchall()
            for row in rows:
                latest.setdefault(str(row[0]).upper(), row)
    today = datetime.now().date().isoformat()
    result = []
    for p in sorted(data["positions"], key=lambda x: x["value_eur"], reverse=True):
        symbol, kind = p["symbol"], p["kind"]
        record = latest.get(symbol.upper())
        if kind == "copy":
            status, reason = "Blackbox", "Enthaltene Einzelwerte und Risiken nicht aus Screenshot prüfbar"
        elif kind == "commodity":
            status, reason = "Produkt prüfen", "SILVER kann ein Broker-Derivat sein; Konditionen fehlen"
        elif record and record[1] == today:
            status = "Systemsignal: " + str(record[2])
            reason = "Lokaler Tageslauf; News=" + str(record[4]) + "; unabhängige Kursprüfung offen"
        elif record:
            status, reason = "Signal veraltet", "Letzter lokaler Lauf zu diesem Wert: " + str(record[1])
        else:
            status, reason = "Keine aktuelle Prüfung", "Weder frischer Kurs noch belastbares Signal lokal vorhanden"
        result.append("<tr><td>" + escape(symbol) + "</td><td>" + escape(kind) +
                      "</td><td>" + escape(status) + "</td><td>" + escape(reason) + "</td></tr>")
    return "\n".join(result)


def build(source: Path = PRIVATE, output: Path = OUTPUT) -> Path:
    data = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(data.get("positions"), list) or not data["positions"]:
        raise ValueError("Keine Positionen in der Depotdatei")
    seen: set[tuple[str, str]] = set()
    for row in data["positions"]:
        value = row.get("value_eur")
        key = (str(row.get("kind", "")), str(row.get("symbol", "")).upper())
        if not key[1] or key[0] not in {"stock", "crypto", "copy", "commodity"} or key in seen:
            raise ValueError(f"Ungültige oder doppelte Position: {key}")
        if not isinstance(value, (float, int)) or not math.isfinite(value) or value <= 0:
            raise ValueError(f"Ungültiger Wert für {key}")
        seen.add(key)
    template = (ROOT / "real_portfolio_simulator_template.html").read_text(encoding="utf-8")
    script = (ROOT / "real_portfolio_simulator_core.js").read_text(encoding="utf-8")
    payload = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e")
    html = (template.replace("__PORTFOLIO_DATA__", payload)
            .replace("__SIMULATOR_CORE__", script)
            .replace("__LOCAL_REVIEW_ROWS__", local_review_rows(data)))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=PRIVATE)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    print(build(args.source, args.output))
