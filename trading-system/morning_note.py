"""Kurzer, rein deterministischer Einstieg in den bestehenden Tagesbericht.

Keine zusätzlichen Datenquellen, Modellaufrufe oder Handelsentscheidungen.
"""

from html import escape
from math import isfinite


def _preis(value) -> str:
    if isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value):
        return f"${value:,.2f}"
    return "—"


def morning_note_lines(ergebnisse: list[dict]) -> list[str]:
    """Zeige ausschließlich vorhandene Signale, ohne News/Frische zu erfinden."""
    signale = [e for e in (ergebnisse or []) if isinstance(e, dict)]
    def urteil(e):
        finale = e.get("finale")
        return finale.get("empfehlung") if isinstance(finale, dict) else None

    kaufen = [e for e in signale if urteil(e) == "KAUFEN"]
    verkaufen = [e for e in signale if urteil(e) == "VERKAUFEN"]
    zeilen = [
        f"Systemlage: {len(kaufen)} Kaufen, {len(verkaufen)} Verkaufen, "
        f"{len(signale) - len(kaufen) - len(verkaufen)} Abwarten/ohne Urteil.",
    ]

    if kaufen:
        zeilen.append("Systemfokus (Reihenfolge der Pipeline, keine Rangliste):")
        for e in kaufen[:2]:
            finale = e["finale"]
            asset = str(e.get("asset") or "Unbekannt")[:24]
            zeilen.append(
                f"{asset}: Einstieg {_preis(finale.get('einstieg'))}, "
                f"Ziel {_preis(finale.get('ziel'))}, "
                f"Stop {_preis(finale.get('stop_loss'))}; "
                f"Risiko {str(finale.get('risiko') or 'unbekannt')[:24]}."
            )
    else:
        zeilen.append("Kein Kaufsignal aus diesem Lauf; kein Top-Call erzwungen.")

    zeilen.extend([
        "Datenfrische, Overnight-News, Earnings-Konsens und heutige Termine "
        "sind hier nicht verifiziert; daraus wird kein kurzfristiger Trigger abgeleitet.",
        "Konfidenz nicht kalibriert; Bull/Bear-Rollen sind kein unabhängiger "
        "Modellkonsens. Details und Quellenlage im Hauptbericht prüfen.",
        "Automatisierte Modell-Ausgabe, keine Anlageberatung. Keine Gewähr.",
    ])
    return zeilen


def morning_note_html(ergebnisse: list[dict]) -> str:
    """Für das bestehende Dashboard sicher escapte Darstellung erzeugen."""
    items = "".join(f"<li>{escape(line)}</li>" for line in morning_note_lines(ergebnisse))
    return f'<section class="morning-note"><h2>Morning Note</h2><ul>{items}</ul></section>'
