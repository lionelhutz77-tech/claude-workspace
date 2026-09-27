# CLAUDE.md — Trading-System

Multi-Agent-System für tägliche Kauf-/Verkaufssignale (Aktien + Krypto). Voller Plan: `PROJEKT.md`.

## Ausführen
- **Produktiv läuft das System seit 27.09.2026 nur in der Cloud**: GitHub Actions
  `.github/workflows/daily_trading.yml`, täglich 05:23 UTC, committet `data/*.db` und
  `output/dashboard_aktuell.html` nach `master`, warnt per Telegram bei Fehlern und bei
  stillen Ausfällen (401, `model_not_found`, `$nan`, Traceback im Log).
- Der Windows-Task `TradingIntelligenceSystem` ist deaktiviert — **keine lokalen Läufe**,
  sonst entstehen wieder zwei getrennte Depotstände. Cloud-Stand auf den PC holen:
  `python cloud_daten_holen.py [--oeffnen]` (Logon-Task nutzt `--oeffnen`).
- Manueller Lauf: auf GitHub „Run workflow“ bzw. `gh workflow run daily_trading.yml`.
- Secrets nur als GitHub Secrets (GROQ_API_KEY, TELEGRAM_*, GMX_*, EMAIL_ABSENDER_FILTER).
- Dashboard: `start_dashboard.ps1` bzw. `python dashboard.py` (HTML mit TradingView-Charts, öffnet im Browser).
- Sofort-Lauf: `run_jetzt.bat`. Task-Setup: `setup_task_admin.ps1`/`.bat`.
- venv vorhanden (`venv/`), `requirements.txt`. Secrets in `.env` (gitignored).

## Aufbau
- `main.py` — Orchestrierung der Pipeline.
- `agents/` — alle Agenten: stock/crypto/news/social_analyst, aggregator, revision_agent, bull_bear_debate, portfolio_agent, multi_depot, backtesting_agent, learning_agent/memory_agent, universe_scanner, correlation_agent, valuation_agent, makro_agent, pattern_agent, volume_agent, sec_agent, strategy_agent, telegram_agent, email_agent, tailwind_connector.
- DBs in `data/` (learnings, market_memory, multi_depot, portfolio).

## Konventionen / Gotchas
- KI-Aufgaben laufen über `agents/free_ai_client.py` und das gemeinsame **Free-AI-Gateway**. Routine und Tiefenanalyse nutzen die dort festgelegten Groq-Routen; klar begrenzte Recherche nutzt Gemini CLI. Ausgabe- und Eingabelimits gelten zentral, und es gibt keinen stillen Providerwechsel. Nie Anthropic-API vorschlagen.
- Bekannte Schwächen ehrlich mittragen (für Berichte gilt Skill **trading-bericht**): Bull/Bear nutzt dasselbe Modell (keine echte Unabhängigkeit); News-Sentiment keyword-basiert; StockTwits oft 50/50; Krypto-Symbole CoinGecko↔Yahoo nicht immer kompatibel.
- **Keine persönliche Anlageberatung** — Ausgaben sind Modell-Output des Systems, mit Disclaimer.
- Telegram wird vor dem Dashboard gesendet; Dashboard-Fehler abfangen (siehe Git-Historie).

## Arbeitsweise
Skill **bau-qualitaet** anwenden (planen → Ursache statt Symptom → verifizieren vor „fertig"). Inkrementell, jeden Schritt erklären.
