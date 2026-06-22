# CLAUDE.md — Trading-System

Multi-Agent-System für tägliche Kauf-/Verkaufssignale (Aktien + Krypto). Voller Plan: `PROJEKT.md`.

## Ausführen
- Kompletter Lauf: `run_daily.bat` (bzw. `python main.py`). Läuft automatisch täglich 08:00 (Windows Task Scheduler, StartWhenAvailable).
- Dashboard: `start_dashboard.ps1` bzw. `python dashboard.py` (HTML mit TradingView-Charts, öffnet im Browser).
- Sofort-Lauf: `run_jetzt.bat`. Task-Setup: `setup_task_admin.ps1`/`.bat`.
- venv vorhanden (`venv/`), `requirements.txt`. Secrets in `.env` (gitignored).

## Aufbau
- `main.py` — Orchestrierung der Pipeline.
- `agents/` — alle Agenten: stock/crypto/news/social_analyst, aggregator, revision_agent, bull_bear_debate, portfolio_agent, multi_depot, backtesting_agent, learning_agent/memory_agent, universe_scanner, correlation_agent, valuation_agent, makro_agent, pattern_agent, volume_agent, sec_agent, strategy_agent, telegram_agent, email_agent, tailwind_connector.
- DBs in `data/` (learnings, market_memory, multi_depot, portfolio).

## Konventionen / Gotchas
- KI-Revision über **Groq `llama-3.3-70b-versatile`** (kostenlos) — nie Anthropic-API vorschlagen. Groq-Tageslimit ~100k Token: bei Erschöpfung sauber abfangen, nicht still scheitern.
- Bekannte Schwächen ehrlich mittragen (für Berichte gilt Skill **trading-bericht**): Bull/Bear nutzt dasselbe Modell (keine echte Unabhängigkeit); News-Sentiment keyword-basiert; StockTwits oft 50/50; Krypto-Symbole CoinGecko↔Yahoo nicht immer kompatibel.
- **Keine persönliche Anlageberatung** — Ausgaben sind Modell-Output des Systems, mit Disclaimer.
- Telegram wird vor dem Dashboard gesendet; Dashboard-Fehler abfangen (siehe Git-Historie).

## Arbeitsweise
Skill **bau-qualitaet** anwenden (planen → Ursache statt Symptom → verifizieren vor „fertig"). Inkrementell, jeden Schritt erklären.
