# -*- coding: utf-8 -*-
"""
Musterdepot-Bot fuer Alpaca Paper Trading.
5 Segmente je 20.000 USD, innerhalb gleichgewichtet.

AUFRUF:
  python bot.py            -> TROCKENLAUF (zeigt nur an, KEINE Order)
  python bot.py --live     -> setzt echte Paper-Orders im Musterkonto

Auch im --live-Modus ist es Spielgeld (Paper). Kein echtes Risiko.
"""
import os
import sys
import requests
from dotenv import load_dotenv
from segments import SEGMENTS, SEGMENT_CAPITAL

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

KEY = os.getenv("ALPACA_API_KEY", "")
SECRET = os.getenv("ALPACA_SECRET_KEY", "")
PAPER = os.getenv("ALPACA_PAPER", "true").lower() == "true"
BASE = "https://paper-api.alpaca.markets" if PAPER else "https://api.alpaca.markets"
DATA = "https://data.alpaca.markets"
HEADERS = {"APCA-API-KEY-ID": KEY, "APCA-API-SECRET-KEY": SECRET}

LIVE = "--live" in sys.argv


def check_keys():
    if not KEY or "HIER_" in KEY or not SECRET or "HIER_" in SECRET:
        print("FEHLER: In der .env stehen noch Platzhalter statt echter Keys.")
        sys.exit(1)
    if not PAPER:
        print("STOPP: ALPACA_PAPER ist NICHT 'true'. Dieser Bot laeuft nur im Paper-Modus.")
        sys.exit(1)


def get_price(ticker):
    """Letzter Handelspreis ueber Alpaca Data API (IEX, kostenlos)."""
    r = requests.get(f"{DATA}/v2/stocks/{ticker}/trades/latest",
                     headers=HEADERS, params={"feed": "iex"}, timeout=15)
    if r.status_code == 200:
        return float(r.json()["trade"]["p"])
    return None


def submit_order(symbol, qty):
    body = {"symbol": symbol, "qty": qty, "side": "buy",
            "type": "market", "time_in_force": "day"}
    r = requests.post(f"{BASE}/v2/orders", json=body, headers=HEADERS, timeout=15)
    return r.status_code, r.text


def main():
    check_keys()
    modus = "LIVE (echte Paper-Orders)" if LIVE else "TROCKENLAUF (keine Order)"
    print("=" * 60)
    print(f"  MUSTERDEPOT-BOT  --  Modus: {modus}")
    print(f"  Kapital pro Segment: {SEGMENT_CAPITAL:,.0f} USD")
    print("=" * 60)

    gesamt = 0.0
    for seg_id, seg in SEGMENTS.items():
        tickers = seg["tickers"]
        pro_ticker = SEGMENT_CAPITAL / len(tickers)
        print(f"\n[{seg_id}] {seg['name']}")
        print(f"  {len(tickers)} Wert(e), je {pro_ticker:,.0f} USD")
        print("  " + "-" * 52)
        for t in tickers:
            preis = get_price(t)
            if preis is None:
                print(f"  {t:6s}  KEIN PREIS verfuegbar -> uebersprungen")
                continue
            qty = int(pro_ticker // preis)  # ganze Stueck, kein Bruchteil
            kosten = qty * preis
            gesamt += kosten
            zeile = f"  {t:6s}  Kurs {preis:9.2f}  ->  {qty:4d} Stueck = {kosten:10,.2f} USD"
            if LIVE and qty > 0:
                code, txt = submit_order(t, qty)
                zeile += "  [ORDER OK]" if code in (200, 201) else f"  [FEHLER {code}]"
            print(zeile)

    print("\n" + "=" * 60)
    print(f"  Geplantes Investment gesamt: {gesamt:,.2f} USD von 100.000 USD")
    if not LIVE:
        print("  -> Das war nur ein Trockenlauf. Mit  python bot.py --live  scharf schalten.")
    print("=" * 60)


if __name__ == "__main__":
    main()
