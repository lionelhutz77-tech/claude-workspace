"""
Earnings Calendar Agent
Prüft ob für eine Aktie innerhalb der nächsten WARNTAGE Quartalsergebnisse anstehen.

Warum: Kauf kurz vor Earnings ist Roulette — 50/50 Chance auf ±10% Kursbewegung,
unabhängig von Fundamentals. Selbst eine gute Aktie kann nach Earnings einbrechen.

Gibt Warnung aus und reduziert Trading-Punkte wenn Earnings nahe sind.
"""

import sys
import yfinance as yf
from datetime import datetime, timezone, timedelta

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

WARNTAGE = 5   # Warnung wenn Earnings innerhalb dieser Tage


def prüfe_earnings(ticker: str) -> dict:
    """
    Prüft ob Earnings in den nächsten WARNTAGE Tagen anstehen.
    Gibt dict zurück: earnings_nah, tage, datum, warnung
    """
    try:
        t   = yf.Ticker(ticker)
        cal = t.calendar

        # Format variiert je nach yfinance-Version
        earnings_ts = None

        if isinstance(cal, dict) and cal:
            dates = cal.get("Earnings Date", [])
            if dates:
                d = dates[0] if isinstance(dates, list) else dates
                earnings_ts = d if hasattr(d, "date") else None

        elif cal is not None and hasattr(cal, "index"):
            # DataFrame-Format
            if "Earnings Date" in cal.index:
                val = cal.loc["Earnings Date"]
                earnings_ts = val.iloc[0] if hasattr(val, "iloc") else val

        if earnings_ts is None:
            return {"earnings_nah": False}

        # Zeitzonenfrei vergleichen
        jetzt = datetime.now(tz=timezone.utc)
        if hasattr(earnings_ts, "tzinfo") and earnings_ts.tzinfo:
            diff = (earnings_ts - jetzt).days
        else:
            try:
                diff = (earnings_ts.replace(tzinfo=timezone.utc) - jetzt).days
            except Exception:
                return {"earnings_nah": False}

        if 0 <= diff <= WARNTAGE:
            datum_str = earnings_ts.strftime("%d.%m.%Y") if hasattr(earnings_ts, "strftime") else str(earnings_ts)[:10]
            return {
                "earnings_nah": True,
                "tage": diff,
                "datum": datum_str,
                "warnung": f"Earnings in {diff} Tag(en) ({datum_str}) — Einstieg riskant (Roulette-Effekt)",
            }

        return {"earnings_nah": False}

    except Exception:
        return {"earnings_nah": False}


def prüfe_earnings_alle(tickers: list[str]) -> dict[str, dict]:
    """Batch-Check für mehrere Tickers. Gibt dict {ticker: earnings_info} zurück."""
    ergebnisse = {}
    for ticker in tickers:
        ergebnisse[ticker] = prüfe_earnings(ticker)
    return ergebnisse
