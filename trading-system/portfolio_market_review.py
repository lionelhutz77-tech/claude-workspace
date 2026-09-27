"""Lokaler technischer Erstcheck für das private Depot; nur öffentliche Ticker gehen an Yahoo.

Keine Broker- oder LLM-Verbindung. Diese Regeln sind explizite Paper-Exit/Watch-Gates,
keine Vorhersage und keine Order. Der private Positionswert bleibt lokal.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "private" / "real_portfolio_2026-09-21.json"
OUTPUT = ROOT / "private" / "real_portfolio_market_review.json"
CANDIDATES = ("ABBV", "A", "ARE", "CRWD", "FTNT", "KR", "MTCH", "MU", "PANW", "PFG")
USER_AGENT = "LionelOS-PaperResearch/1.0 (public-symbols-only)"


def yahoo_symbol(symbol: str, kind: str) -> str | None:
    if kind == "crypto":
        return symbol.upper() + "-USD"
    if kind == "stock":
        return symbol.upper()
    return None


def rsi(closes: list[float], periods: int = 14) -> float | None:
    if len(closes) <= periods:
        return None
    changes = [closes[i] - closes[i-1] for i in range(len(closes)-periods, len(closes))]
    gain = sum(max(0.0, c) for c in changes) / periods
    loss = sum(max(0.0, -c) for c in changes) / periods
    if loss == 0:
        return 100.0 if gain else 50.0
    return 100 - 100 / (1 + gain / loss)


def summarize_chart(payload: dict, queried_at: str) -> dict:
    result = payload["chart"]["result"][0]
    meta = result["meta"]
    raw = result["indicators"]["quote"][0]["close"]
    closes = [float(x) for x in raw if x is not None and math.isfinite(x) and x > 0]
    if len(closes) < 200:
        raise ValueError(f"Nur {len(closes)} verwertbare Tagesschlusskurse")
    price = float(meta["regularMarketPrice"])
    if not math.isfinite(price) or price <= 0:
        raise ValueError("Kein gültiger aktueller Kurs")
    market_at = datetime.fromtimestamp(int(meta["regularMarketTime"]), tz=timezone.utc)
    now = datetime.fromisoformat(queried_at)
    age_hours = (now - market_at).total_seconds() / 3600
    if age_hours < -1:
        raise ValueError("Kurszeitpunkt liegt in der Zukunft")
    ma20 = statistics.fmean(closes[-20:])
    ma50 = statistics.fmean(closes[-50:])
    ma200 = statistics.fmean(closes[-200:])
    ret20 = 100 * (price / closes[-21] - 1)
    ret60 = 100 * (price / closes[-61] - 1)
    return {
        "price": round(price, 4), "currency": meta.get("currency"),
        "market_at_utc": market_at.isoformat(), "age_hours": round(age_hours, 2),
        "points": len(closes), "ma20": round(ma20, 4), "ma50": round(ma50, 4),
        "ma200": round(ma200, 4), "rsi14": round(rsi(closes) or 0, 2),
        "return_20d_pct": round(ret20, 2), "return_60d_pct": round(ret60, 2),
        "high_1y": round(max(closes), 4), "low_1y": round(min(closes), 4),
    }


def gate(metrics: dict | None, kind: str, weight_pct: float, error: str | None = None) -> tuple[str, str]:
    if metrics is None:
        return "KEIN_URTEIL", error or "Kein überprüfbarer Marktpreis"
    if metrics["age_hours"] > (30 if kind == "crypto" else 96):
        return "KEIN_URTEIL", "Kurs zu alt; kein Paper-Signal"
    p, m50, m200 = metrics["price"], metrics["ma50"], metrics["ma200"]
    if p < 0.97 * m200 and m50 < m200 and metrics["return_20d_pct"] < 0:
        return "EXIT_PRUEFEN", "Unter 200-Tage-Linie, 50-Tage-Linie ebenfalls darunter, 20-Tage-Trend negativ"
    if weight_pct > 10:
        return "KLUMPEN_PRUEFEN", "Einzelwert über 10 % des Screenshot-Depots; Größenrisiko unabhängig vom Kurs"
    if metrics["rsi14"] > 75 and p > 1.15 * m50:
        return "GEWINNMITNAHME_PRUEFEN", "RSI > 75 und Kurs > 15 % über 50-Tage-Linie"
    if p < m50 and metrics["return_20d_pct"] < 0:
        return "BEOBACHTEN", "Unter 50-Tage-Linie und 20-Tage-Trend negativ"
    if p > m50 > m200 and 45 <= metrics["rsi14"] <= 70 and metrics["return_20d_pct"] > 0:
        return "TREND_INTAKT", "Über 50-/200-Tage-Linie, positives Momentum, RSI nicht überhitzt"
    return "BEOBACHTEN", "Gemischte technische Indikatoren; kein starkes Regelvotum"


def fetch_chart(symbol: str, timeout: int = 15) -> dict:
    query = urllib.parse.urlencode({"range": "1y", "interval": "1d"})
    url = "https://query1.finance.yahoo.com/v8/finance/chart/" + urllib.parse.quote(symbol, safe="") + "?" + query
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.load(response)


def run(source: Path = SOURCE, output: Path = OUTPUT, delay: float = 0.35,
        allow_symbol_upload: bool = False) -> dict:
    if not allow_symbol_upload:
        raise PermissionError("Ticker-Upload an Yahoo ist gesperrt; ausdrückliche Freigabe erforderlich")
    private = json.loads(source.read_text(encoding="utf-8"))
    denominator = round(sum(p["value_eur"] for p in private["positions"]) + private["cash_eur"], 2)
    seen = set()
    assets = []
    for p in private["positions"]:
        yahoo = yahoo_symbol(p["symbol"], p["kind"])
        if yahoo:
            assets.append((p["symbol"], p["kind"], p["value_eur"], yahoo, "bestand"))
            seen.add(p["symbol"].upper())
    for symbol in CANDIDATES:
        if symbol not in seen:
            assets.append((symbol, "stock", 0.0, symbol, "kandidat"))
    rows = []
    for symbol, kind, value, yahoo, role in assets:
        queried_at = datetime.now(timezone.utc).isoformat()
        metrics, error = None, None
        try:
            metrics = summarize_chart(fetch_chart(yahoo), queried_at)
        except (ValueError, KeyError, IndexError, TypeError, urllib.error.URLError, TimeoutError) as exc:
            error = str(exc)[:200]
        weight = 100 * value / denominator if denominator else 0
        status, reason = gate(metrics, kind, weight, error)
        rows.append({"symbol": symbol, "kind": kind, "role": role, "value_eur": value,
                     "weight_pct": round(weight, 2), "data_symbol": yahoo,
                     "source_url": "https://finance.yahoo.com/quote/" + urllib.parse.quote(yahoo, safe=""),
                     "metrics": metrics, "status": status, "reason": reason, "error": error})
        print(f"{symbol:10} {status:22} {('ok' if metrics else error)}")
        if delay:
            time.sleep(delay)
    result = {"generated_at_utc": datetime.now(timezone.utc).isoformat(),
              "source": "Yahoo Finance Chart API, 1y daily; public tickers only",
              "horizon": "taktischer Paper-Erstcheck, 2–12 Wochen",
              "limits": "Technische Regeln allein belegen weder Fair Value noch Gewinnwahrscheinlichkeit; keine Orders.",
              "rows": rows}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--allow-symbol-upload", action="store_true",
                        help="Nur nach ausdrücklicher Nutzerfreigabe: öffentliche Ticker an Yahoo senden")
    args = parser.parse_args()
    run(args.source, args.output, allow_symbol_upload=args.allow_symbol_upload)
