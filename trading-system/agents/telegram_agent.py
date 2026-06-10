"""
Telegram-Agent
Sendet den taeglichen Handelsbericht als formatierte Nachricht an Telegram.

Nachrichten-Typen:
  1. Tages-Zusammenfassung (Kaufempfehlungen + Depot-Stand)
  2. Position geschlossen (Gewinn oder Verlust)
  3. Kritische Warnung (z.B. Stop-Loss nahe)

Einrichtung:
  1. @BotFather in Telegram -> /newbot -> Token erhalten
  2. Bot anschreiben -> getUpdates -> Chat-ID ermitteln
  3. Token + Chat-ID in .env eintragen
"""

import sys
import os
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
BASE_URL         = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"


# ---------------------------------------------------------------------------
# Kern-Funktion: Nachricht senden
# ---------------------------------------------------------------------------

def sende_nachricht(text: str, parse_mode: str = "HTML") -> bool:
    """
    Sendet eine Nachricht an den konfigurierten Telegram-Chat.
    Gibt True zurueck wenn erfolgreich.
    """
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("  [Telegram] Nicht konfiguriert — Token oder Chat-ID fehlt.")
        return False

    url  = f"{BASE_URL}/sendMessage"
    data = {
        "chat_id":    TELEGRAM_CHAT_ID,
        "text":       text,
        "parse_mode": parse_mode,
    }

    try:
        resp = requests.post(url, data=data, timeout=15)
        if resp.status_code == 200:
            return True
        else:
            print(f"  [Telegram] Fehler: {resp.status_code} — {resp.text[:200]}")
            return False
    except Exception as e:
        print(f"  [Telegram] Verbindungsfehler: {e}")
        return False


def teste_verbindung() -> bool:
    """Prueft ob Token und Chat-ID korrekt sind."""
    return sende_nachricht("Trading Intelligence System verbunden.")


# ---------------------------------------------------------------------------
# Nachrichten-Templates
# ---------------------------------------------------------------------------

def format_tagesbericht(ergebnisse: list[dict], depot_stats: dict = None) -> str:
    """Formatiert den Tagesbericht als Telegram-Nachricht (HTML)."""
    datum = datetime.now().strftime("%d.%m.%Y %H:%M")

    kaufen   = [e for e in ergebnisse if e["finale"]["empfehlung"] == "KAUFEN"]
    abwarten = [e for e in ergebnisse if e["finale"]["empfehlung"] == "ABWARTEN"]

    lines = [
        f"<b>Trading Intelligence System</b>",
        f"<i>{datum} Uhr</i>",
        "",
    ]

    # Depot-Stand
    if depot_stats and depot_stats.get("trades_gesamt", 0) > 0:
        pnl     = depot_stats.get("gesamt_pnl_eur", 0)
        pnl_pct = depot_stats.get("gesamt_pnl_pct", 0)
        pnl_emoji = "📈" if pnl >= 0 else "📉"
        lines += [
            f"<b>Musterdepot:</b> {pnl_emoji} {pnl:+.2f} EUR ({pnl_pct:+.2f}%)",
            f"Trefferquote: {depot_stats.get('trefferquote', 0):.1f}%  |  "
            f"Depotwert: {depot_stats.get('depotwert', 0):,.2f} EUR",
            "",
        ]

    # KAUFEN-Empfehlungen
    if kaufen:
        lines.append(f"<b>✅ KAUFEN ({len(kaufen)} Assets):</b>")
        for e in kaufen:
            f       = e["finale"]
            strat   = e.get("strategie", "")
            strat_str = f" [{strat}]" if strat else ""
            risiko  = f.get("risiko", "MITTEL")
            r_emoji = {"NIEDRIG": "🟢", "MITTEL": "🟡", "HOCH": "🔴"}.get(risiko, "⚪")
            lines.append(
                f"{r_emoji} <b>{e['asset']}</b>{strat_str}  "
                f"Einstieg: ${f.get('einstieg', e.get('preis', 0)):,.2f}  "
                f"Ziel: ${f.get('ziel', 0):,.2f}  "
                f"SL: ${f.get('stop_loss', 0):,.2f}"
            )
        lines.append("")

    # ABWARTEN
    if abwarten:
        names = ", ".join(e["asset"] for e in abwarten)
        lines.append(f"<b>⏸ Abwarten:</b> {names}")
        lines.append("")

    lines.append("<i>Keine Anlageberatung. Eigene Recherche erforderlich.</i>")
    return "\n".join(lines)


def format_position_geschlossen(asset: str, pnl_eur: float, pnl_pct: float, status: str) -> str:
    """Benachrichtigung wenn eine Position geschlossen wird."""
    if pnl_eur > 0:
        emoji = "✅"
        label = "GEWINN"
    else:
        emoji = "❌"
        label = "VERLUST"

    datum = datetime.now().strftime("%d.%m.%Y")
    return (
        f"{emoji} <b>Position geschlossen: {asset}</b>\n"
        f"Ergebnis: <b>{label}</b>\n"
        f"P&L: <b>{pnl_eur:+.2f} EUR ({pnl_pct:+.1f}%)</b>\n"
        f"Status: {status} | {datum}"
    )


def format_warnung(asset: str, nachricht: str) -> str:
    """Kritische Warnung (Stop-Loss nahe, ungewoehnliche Bewegung)."""
    return (
        f"⚠️ <b>WARNUNG: {asset}</b>\n"
        f"{nachricht}\n"
        f"<i>{datetime.now().strftime('%d.%m.%Y %H:%M')} Uhr</i>"
    )


# ---------------------------------------------------------------------------
# Haupt-Sendefunktion fuer den Tagesbericht
# ---------------------------------------------------------------------------

def sende_tagesbericht(ergebnisse: list[dict], depot_stats: dict = None) -> bool:
    """Sendet den vollstaendigen Tagesbericht an Telegram."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return False

    nachricht = format_tagesbericht(ergebnisse, depot_stats)
    erfolg    = sende_nachricht(nachricht)

    if erfolg:
        print("  [Telegram] Tagesbericht gesendet.")
    return erfolg


def sende_positions_update(geschlossene: list[dict]) -> None:
    """Sendet Updates fuer alle heute geschlossenen Positionen."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    for pos in geschlossene:
        msg = format_position_geschlossen(
            pos["asset"], pos["pnl_eur"], pos["pnl_pct"], pos.get("status", "")
        )
        sende_nachricht(msg)


# ---------------------------------------------------------------------------
# Einstiegspunkt (Verbindungstest)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Telegram-Agent — Verbindungstest\n")

    if not TELEGRAM_TOKEN:
        print("TELEGRAM_TOKEN fehlt in .env")
        print("Bitte eintragen: TELEGRAM_TOKEN=dein_token")
    elif not TELEGRAM_CHAT_ID:
        print("TELEGRAM_CHAT_ID fehlt in .env")
        print("Bitte eintragen: TELEGRAM_CHAT_ID=deine_chat_id")
    else:
        print(f"Token: ...{TELEGRAM_TOKEN[-10:]}")
        print(f"Chat-ID: {TELEGRAM_CHAT_ID}")
        print("\nSende Testnachricht...")
        ok = teste_verbindung()
        print("Erfolgreich!" if ok else "Fehlgeschlagen — Token oder Chat-ID pruefen.")
