"""Kurzbericht der empfehlenswerten Objekte per Telegram (ersetzt den aufgegebenen GMX-Mailversand).

Zugangsdaten: TELEGRAM_TOKEN / TELEGRAM_CHAT_ID aus der Umgebung (GitHub Secrets) oder,
auf dem PC, aus trading-system/.env (derselbe Bot wie das Trading-System).
"""

from __future__ import annotations

import html
import os
from pathlib import Path
from typing import Dict, List

import requests


def _zugang() -> tuple[str, str]:
    if not os.getenv("TELEGRAM_TOKEN"):
        try:
            from dotenv import load_dotenv
            load_dotenv(Path(__file__).resolve().parents[1] / "trading-system" / ".env")
        except ImportError:
            pass
    return os.getenv("TELEGRAM_TOKEN", ""), os.getenv("TELEGRAM_CHAT_ID", "")


def _zahl(wert) -> str:
    return f"{float(wert or 0):,.0f}".replace(",", ".")


def formatiere(empfohlen: List[Dict], gesamt: int, max_objekte: int = 6) -> str:
    beste = sorted(empfohlen, key=lambda p: -(p.get("netto_cashflow") or 0))[:max_objekte]
    zeilen = [f"<b>🏠 Immobilien-Scan</b>: {len(empfohlen)} von {gesamt} Objekten erfüllen die Kriterien"]
    for p in beste:
        flaggen = f" ⚠️ {html.escape(p['rote_flaggen'][0])}" if p.get("rote_flaggen") else ""
        brutto = f"{float(p.get('brutto_rendite') or 0):.1f}".replace(".", ",")
        zeile = (f"\n• {_zahl(p.get('kaufpreis'))} € · {p.get('wohnungen', '?')} WE · "
                 f"Cashflow {_zahl(p.get('netto_cashflow'))} €/Monat · brutto {brutto} %"
                 f"\n  {html.escape(str(p.get('adresse', ''))[:60])} "
                 f"({html.escape(str(p.get('quelle', '')))}){flaggen}")
        if p.get("link"):
            zeile += f"\n  {p['link']}"
        zeilen.append(zeile)
    zeilen.append("\n<i>Annahmen (Miete je Einheit, Finanzierung) laut config.yaml · keine Anlageberatung</i>")
    return "\n".join(zeilen)


def sende(empfohlen: List[Dict], gesamt: int) -> bool:
    token, chat = _zugang()
    if not token or not chat:
        print("[WARNING] Telegram nicht konfiguriert — Kurzbericht uebersprungen")
        return False
    antwort = requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                            data={"chat_id": chat, "text": formatiere(empfohlen, gesamt), "parse_mode": "HTML",
                                  "disable_web_page_preview": "true"}, timeout=20)
    return antwort.ok
