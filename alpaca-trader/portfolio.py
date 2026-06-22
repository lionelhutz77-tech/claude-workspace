# -*- coding: utf-8 -*-
"""
Portfolio-Uebersicht fuer das Alpaca-Musterdepot.
Liest die ECHTEN Positionen + offenen Orders aus Alpaca, gruppiert sie nach
unseren 5 Segmenten, berechnet Gewinn/Verlust und schickt optional Telegram.

AUFRUF:
  python portfolio.py             -> Uebersicht im Terminal
  python portfolio.py --telegram  -> zusaetzlich an Telegram senden
"""
import os
import sys
import requests
from dotenv import load_dotenv
from segments import SEGMENTS

HERE = os.path.dirname(__file__)
load_dotenv(os.path.join(HERE, ".env"))
# Telegram-Zugang aus dem bestehenden Trading-System wiederverwenden
load_dotenv(r"C:\Users\HP\Documents\Claude\trading-system\.env")

KEY = os.getenv("ALPACA_API_KEY", "")
SECRET = os.getenv("ALPACA_SECRET_KEY", "")
BASE = "https://paper-api.alpaca.markets"
HEADERS = {"APCA-API-KEY-ID": KEY, "APCA-API-SECRET-KEY": SECRET}

TG_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TG_CHAT = os.getenv("TELEGRAM_CHAT_ID", "")

# Ticker -> Segmentname (zum Gruppieren der echten Positionen)
TICKER_SEG = {t: seg["name"] for seg in SEGMENTS.values() for t in seg["tickers"]}


def api(path, params=None):
    r = requests.get(f"{BASE}{path}", headers=HEADERS, params=params, timeout=15)
    r.raise_for_status()
    return r.json()


def send_telegram(text):
    if not TG_TOKEN or not TG_CHAT:
        print("  (Telegram: kein Token/Chat-ID gefunden, uebersprungen)")
        return
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    r = requests.post(url, data={"chat_id": TG_CHAT, "text": text,
                                 "parse_mode": "Markdown"}, timeout=15)
    print("  (Telegram gesendet)" if r.status_code == 200 else f"  (Telegram-Fehler {r.status_code})")


def build_report():
    acct = api("/v2/account")
    positions = api("/v2/positions")
    open_orders = api("/v2/orders", {"status": "open", "limit": 100})

    lines = ["*PAPER-TRADING — Musterdepot*", ""]
    equity = float(acct["equity"])
    cash = float(acct["cash"])
    lines.append(f"Gesamtwert: *{equity:,.0f} USD*  |  Cash: {cash:,.0f}")

    # Positionen nach Segment gruppieren
    seg_data = {}
    for p in positions:
        seg = TICKER_SEG.get(p["symbol"], "Sonstige")
        seg_data.setdefault(seg, []).append(p)

    if positions:
        lines.append("")
        for seg_name in [s["name"] for s in SEGMENTS.values()]:
            ps = seg_data.get(seg_name, [])
            if not ps:
                continue
            mv = sum(float(p["market_value"]) for p in ps)
            pl = sum(float(p["unrealized_pl"]) for p in ps)
            cost = mv - pl
            pct = (pl / cost * 100) if cost else 0
            lines.append(f"*{seg_name}*: {mv:,.0f} USD  ({pct:+.2f}%)")
            for p in sorted(ps, key=lambda x: float(x["unrealized_plpc"]), reverse=True):
                ppct = float(p["unrealized_plpc"]) * 100
                lines.append(f"  {p['symbol']}: {ppct:+.2f}%  ({float(p['market_value']):,.0f})")
    else:
        lines.append("")
        lines.append("Noch keine Positionen gefuellt.")

    if open_orders:
        lines.append("")
        lines.append(f"_Offene Orders: {len(open_orders)} (warten auf Boersenoeffnung)_")
        for o in open_orders[:15]:
            lines.append(f"  {o['side']} {o['qty']} {o['symbol']} — {o['status']}")

    return "\n".join(lines)


def main():
    text = build_report()
    print(text.replace("*", "").replace("_", ""))
    if "--telegram" in sys.argv:
        print()
        send_telegram(text)


if __name__ == "__main__":
    main()
