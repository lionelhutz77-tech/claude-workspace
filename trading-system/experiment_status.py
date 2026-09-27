"""Erzeugt den aktuellen, lokalen Statusbericht der 10.000-EUR-Testserie."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from html import escape
from pathlib import Path

from agents.experiment_depot import DB_PATH, statistics


PROJECT = Path(__file__).resolve().parent
REPORT = PROJECT / "output" / "experiment_10000_aktuell.html"


def render_report(stats: list[dict]) -> str:
    rows = []
    for item in stats:
        equity = (f"{item['equity_eur']:,.2f} €" if item["equity_eur"] is not None
                  else "Kurs fehlt")
        ret = (f"{item['return_pct']:+.2f} %" if item["return_pct"] is not None
               else "nicht bewertbar")
        hit = (f"{item['hit_rate_pct']:.1f} %" if item["hit_rate_pct"] is not None
               else "noch offen")
        rows.append("<tr>" + "".join(f"<td>{escape(str(x))}</td>" for x in (
            item["strategy"], equity, ret, hit, item["closed_trades"],
            item["open_positions"], item["pending_orders"], item["max_drawdown_pct"],
            item["stale_positions"]
        )) + "</tr>")
    updated = datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M UTC")
    return f"""<!doctype html><html lang="de"><meta charset="utf-8">
<title>Trading-Testserie 10.000 €</title>
<style>body{{font:16px system-ui;max-width:1100px;margin:3rem auto;padding:0 1rem;
background:#101827;color:#edf3fa}}table{{border-collapse:collapse;width:100%}}
td,th{{padding:.8rem;border-bottom:1px solid #39475a;text-align:left}}
th{{color:#95c5ee}}.note{{background:#1b2a3c;padding:1rem;border-radius:.5rem}}</style>
<h1>Vier virtuelle 10.000-€-Depots</h1><p>Stand: {updated}</p>
<p class="note">Jede Strategie testet alternativ dasselbe Startbudget. Kein echtes Geld,
keine Brokerorders. Ein Signal wird erst bei einem später beobachteten Kurs virtuell
ausgeführt; ohne frischen Kurs oder sichere Währung bleibt es offen. Rendite und
Trefferquote sind erst nach ausreichend Trades aussagekräftig.</p>
<table><thead><tr><th>Strategie</th><th>Depotwert</th><th>Rendite</th>
<th>Trefferquote</th><th>Geschlossene Trades</th><th>Offene Positionen</th>
<th>Vorgemerkt</th><th>Max. Rückgang</th><th>Fehlende Kurse</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
<p>Regeln: maximal 2.000 € je Position, höchstens fünf Kandidaten je Strategie,
0,2 % Kosten/Slippage pro Seite, Exit nach +10 %, −7 % oder 20 Kalendertagen.
Aktien und Krypto nur mit finalem KAUFEN-Signal und belegtem Instrumenttyp.
Eine „beste“ Strategie wird frühestens nach vier Wochen und mindestens 20
geschlossenen Trades bewertet – anhand Rendite, Verlusten, Trefferquote und
fehlenden Daten, nicht allein an der Trefferquote.</p>
<p>Automatisierte Modell-Ausgabe, keine Anlageberatung. Keine Gewähr.</p></html>"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--output", type=Path, default=REPORT)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_report(statistics(args.db)), encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
