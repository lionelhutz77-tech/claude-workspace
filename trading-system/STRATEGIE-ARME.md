# Regel-Strategiearme (Lernsystem Stufe 4)

Vorregistriert am 27.09.2026, Code: `strategie_arme.py`, Tests: `tests/test_strategie_arme.py`.
Live-Start: erster abgeschlossener Handelstag nach dem 27.09.2026. Nur Paper, keine Brokerorders.
Die bestehenden Experiment-Arme (`EXPERIMENT-10000.md`) bleiben unverändert.

## Warum eigenständig

Die KI-Kette gibt fast immer „Abwarten“; BTC (+14,9 % nach dem 16.09.) wurde so verpasst.
Diese Arme rechnen direkt auf abgeschlossenen Tageskursen und handeln am Folgetag zum
Schlusskurs (keine Vorausschau, 0,2 % Kosten je Seite). Backtest und Live nutzen dieselbe
Schrittfunktion.

## Regeln (je 10.000 USD)

| Arm | Einstieg | Ausstieg | Größe |
|---|---|---|---|
| TREND | Schluss > 20-T-Hoch und > SMA50 > SMA200 | Stop Einstieg − 2 ATR, nachgezogen Hoch − 3 ATR; Schluss < SMA50 | 1 % Risiko, max. 20 %, max. 8 Pos. |
| TREND_SCHUTZ | wie TREND, ohne Aktien mit Verwässerungs-Schlagzeile (10 T) | wie TREND | wie TREND |
| SHORT | Schluss < 20-T-Tief und < SMA50 < SMA200 | Stop + 2 ATR, nachgezogen Tief + 3 ATR; Schluss > SMA50 | 0,5 % Risiko, max. 15 %, max. 4 Pos. |
| SHORT_REGIME* | wie SHORT, nur wenn SPY bzw. BTC < SMA200 | wie SHORT | wie SHORT |
| KERN | monatlich SPY 40 / QQQ 25 / BTC 15 / GLD 20 %, je nur über SMA200 | Monatsausgleich | – |
| MISCH | rechnerisch 50 % KERN + 30 % TREND + 20 % SHORT | – | – |

*nach dem Backtest ergänzt, zählt nur mit Live-Beleg.

Universum: 9 Kryptos, 40 große US-Aktien (inkl. Cybersecurity), SPY/QQQ/GLD.

## Backtest 01.06.2021 – 26.09.2026 (inkl. Bärenmarkt 2022)

| | p. a. | max. Rückgang | Wochen im Plus | Wochen ≥ 2,2 % | Trades | Treffer |
|---|---|---|---|---|---|---|
| TREND | +20,7 % | −24,6 % | 53 % | 23 % | 290 | 43 % |
| SHORT | −7,0 % | −33,8 % | 37 % | 1 % | 189 | 29 % |
| SHORT_REGIME | −3,4 % | −19,5 % | 22 % | 1 % | 108 | 29 % |
| KERN | +11,3 % | −23,0 % | 53 % | 8 % | 63 | 57 % |
| MISCH | +12,1 % | −18,0 % | 56 % | 11 % | – | – |
| S&P 500 halten | +13,7 % | −24,5 % | 56 % | 15 % | – | – |
| BTC halten | +17,0 % | −76,6 % | 50 % | 35 % | – | – |

Robustheit TREND (Survivorship-Bias: Universum wurde 2026 gewählt):
ohne die 8 größten Gewinner +15,7 % p. a. (MaxDD −28 %); nur Aktien +17,0 % (−19 %);
nur Krypto +20,0 % (−22 % statt −77 % bei BTC halten).

## Einordnung

- TREND hat im Backtest einen moderaten, robusten Vorsprung; am deutlichsten als
  Risikobegrenzung bei Krypto. Ein Backtest ist kein Beweis — maßgeblich ist der Live-Verlauf.
- Shorts nach Ausbrüchen verloren in jeder Variante, auch im Bärenmarkt. Der bessere Schutz
  war, in Abwärtstrends nicht investiert zu sein.
- „2 % pro Woche“ erreichte selbst der beste Arm nur in 23 % der Wochen.
- Kein Arm wird während der Live-Testphase nachträglich optimiert. Änderungen nur als neuer,
  eigens gekennzeichneter Arm.
