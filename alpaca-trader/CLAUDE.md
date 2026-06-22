# CLAUDE.md — Alpaca Trader

Paper-Trading-Bot über die Alpaca-API (SMA200-Strategie, per Backtest gewählt). Setup: `SETUP.md`. Trade Republic ist NICHT automatisierbar (keine API) — bewusst Alpaca.

## Ausführen
- Täglicher Lauf: `run_daily.bat` (bzw. `python bot.py`). Log in `daily.log`.
- Verbindungstest: `python test_connection.py`. Tracking: `python track.py`.
- Secrets in `.env` (Vorlage `.env.example`). **Paper-Trading** — keine echten Trades.

## Aufbau
- `bot.py` — Hauptlogik (SMA200). `portfolio.py` — Depot/Positionen. `segments.py` — Segment-/Universe-Logik. `track.py` — Verlauf. `baseline.json`, `history.csv` — Zustände.

## Konventionen / Gotchas
- **Nie echte Order/Geldbewegung ausführen** — Paper only; tatsächliche Trades macht der User selbst. Keine persönliche Anlageberatung.
- Strategie SMA200 wurde per Backtest gewählt — Änderungen mit Backtest belegen, nicht aus dem Bauch.
- LLM-Anteile (falls) über Groq, nie Anthropic-API.

## Arbeitsweise
Skill **bau-qualitaet**: Änderungen an der Strategie verifizieren (Test/Backtest) vor „fertig".
