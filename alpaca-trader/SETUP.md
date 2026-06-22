# Alpaca Trader — Setup

## Stand (2026-06-16)

- [x] Machbarkeit geprüft (siehe unten)
- [x] Strategie-Backtest gerechnet (`backtest/compare_strategies.py`)
- [x] Alpaca Paper-Account erstellt (Konto PA3XVG8ACUB6, 100.000 $)
- [x] API-Keys eingetragen (`.env`, per `.gitignore` geschützt) + Verbindung getestet
- [x] 5-Segmente-Experiment definiert (`segments.py`)
- [x] **Beobachtungs-Modus aktiv** (`track.py`) — Startpunkt 2026-06-16 eingefroren
- [ ] Scharf schalten (echte Paper-Orders via `bot.py --live`) — erst nach Beobachtung

## Workflow aktuell

**Phase 1 — Beobachten (jetzt):** Kein Handel. `python track.py` zeigt den Stand je
Segment + Rangliste + Treiber/Bremser und schreibt `history.csv` fort. Ziel: verstehen,
welche Segmente Erfolgs-/Misserfolgsfaktoren tragen, BEVOR virtuell gehandelt wird.

**Phase 2 — Scharf schalten (später):** Wenn klar ist, was funktioniert, setzt
`python bot.py --live` echte Paper-Orders (weiterhin Spielgeld).

## 5 Segmente (je 20.000 $)

| # | Segment | Werte |
|---|---|---|
| 1 | Eigene Risiko-Picks | AFL, LNT, CTAS |
| 2 | Republikaner | MAGA-ETF |
| 3 | Demokraten | DEMZ-ETF |
| 4 | Trump-nah | DJT, PLTR, COIN, XOM, LMT |
| 5 | Benchmark | SPY |

Startpunkt eingefroren in `baseline.json` (2026-06-16). Reset nur mit `python track.py --reset`.

## Machbarkeits-Ergebnis

| Frage | Antwort |
|---|---|
| Alpaca Paper Trading aus Deutschland? | **Ja**, weltweit, nur E-Mail nötig, kostenlos |
| Alpaca Live Trading aus Deutschland? | Unklar — vor Live-Gang bei support@alpaca.markets anfragen |
| Trade Republic automatisiert? | **Nein** — keine offizielle API. Inoffizielle APIs verstoßen gegen die AGB (Risiko: Kontosperrung). Nicht empfohlen. |

## Nächster Schritt (manuell, ~5 Minuten)

1. https://app.alpaca.markets/signup → mit E-Mail registrieren
2. Im Dashboard oben links auf **Paper Trading** umschalten
3. Rechts unter **API Keys** → **Generate New Keys**
4. `API Key ID` und `Secret Key` kopieren und hier im Projekt in eine Datei
   `alpaca-trader/.env` eintragen:

```
ALPACA_API_KEY=dein_key
ALPACA_SECRET_KEY=dein_secret
ALPACA_PAPER=true
```

Die `.env` kommt in `.gitignore` (Keys nie committen).

## Backtest-Ergebnis (2010–2026, SPY/QQQ/TLT, inkl. 0,05% Kosten pro Trade)

| Strategie | CAGR | Max. Drawdown | Sharpe | Schlechtestes Jahr | Trades/Jahr |
|---|---|---|---|---|---|
| Buy & Hold SPY | 14,07% | -33,72% | 0,86 | -18,18% | 0 |
| **SMA200-Trendfilter** | 9,89% | **-20,68%** | **0,88** | -15,52% | 2,4 |
| RSI-2 Mean Reversion | 2,82% | -14,94% | 0,45 | -6,43% | 7,8 |
| Dual Momentum (mtl.) | 10,80% | -27,10% | 0,68 | -12,92% | 2,3 |

**Empfehlung:** SMA200-Trendfilter als Kern (beste risikoadjustierte Rendite,
deutlich kleinerer Drawdown als Buy & Hold), optional kombiniert mit Dual
Momentum für die Asset-Auswahl. Reproduzierbar via:

```
python backtest/compare_strategies.py
```
