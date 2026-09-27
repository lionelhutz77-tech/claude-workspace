# Trading Intelligence System — Projektplan

**Aktueller Zusatz (21.09.2026):** Vier getrennte virtuelle 10.000-€-Depots
testen KONSENS, MOMENTUM, VALUE und TAILWIND nach vorregistrierten Regeln.
Die bisherigen fünf 1.000-€-Depots bleiben als eigener Verlauf erhalten.
Methodik und Berichtspfad: [EXPERIMENT-10000.md](EXPERIMENT-10000.md).
Diese Testserie sendet keine Brokerorders.

## Vision

Tägliche, automatisierte Kauf-/Verkaufsempfehlungen für Aktien und Kryptowährungen,
generiert durch ein Multi-Agenten-System das technische Analyse, Nachrichten und
Social-Media-Sentiment kombiniert. Ausgabe: Einstiegspreis, Zielpreis, Stop-Loss,
optimale Handelszeit.

---

## Agenten-Architektur

```
┌─────────────────────────────────────────────────────────────┐
│                     DATEN-SCHICHT                           │
├──────────────┬──────────────┬──────────────┬───────────────┤
│  Aktien-     │  Krypto-     │  News-       │  Social-      │
│  Analyst     │  Analyst     │  Agent       │  Media-Agent  │
│  (Charts,    │  (Charts,    │  (Artikel,   │  (TikTok,     │
│  Kerzen,     │  On-Chain,   │  Portale,    │  Instagram,   │
│  Indikatoren)│  Sentiment)  │  RSS)        │  X/Twitter)   │
└──────┬───────┴──────┬───────┴──────┬───────┴───────┬───────┘
       │              │              │               │
       └──────────────┴──────────────┴───────────────┘
                              │
                    ┌─────────▼─────────┐
                    │  Aggregator-Agent  │
                    │  (sammelt + ordnet)│
                    └─────────┬─────────┘
                              │
                    ┌─────────▼─────────┐
                    │  Revisions-Agent   │
                    │  (erste Synthese)  │
                    └─────────┬─────────┘
                              │
              ┌───────────────┴───────────────┐
              │                               │
    ┌─────────▼─────────┐         ┌──────────▼────────┐
    │   Bull-Gruppe      │◄───────►│   Bear-Gruppe      │
    │   (3 Agenten,      │ Debatte │   (3 Agenten,      │
    │   pro Kauf)        │         │   contra Kauf)     │
    └─────────┬─────────┘         └──────────┬────────┘
              └───────────────┬───────────────┘
                              │
                    ┌─────────▼─────────┐
                    │  Portfolio-Manager │
                    │  (finale Entsch.)  │
                    └─────────┬─────────┘
                              │
                    ┌─────────▼─────────┐
                    │  OUTPUT            │
                    │  Ticker | Richtung │
                    │  Entry | Target    │
                    │  Stop-Loss | Zeit  │
                    └───────────────────┘
```

---

## Erweiterungen (Phase 2)

- **Backtesting-Agent** — prüft Empfehlung gegen Historien-Daten
- **Korrelations-Agent** — BTC ↔ Coinbase, Öl ↔ Energieaktien etc.
- **Risiko-Agent** — dynamischer Stop-Loss basierend auf ATR/Volatilität
- **Marktzeiten-Orchestrator** — koordiniert wann welcher Agent läuft

---

## Marktzeiten-Logik

| Zeit (DE) | Ereignis | Aktion |
|---|---|---|
| 08:00 | Pre-Market USA | News + Sentiment sammeln |
| 09:00 | Xetra öffnet | DE-Aktien analysieren |
| 15:30 | NYSE/NASDAQ öffnet | US-Aktien analysieren |
| 22:00 | US-Markt schließt | Tagesempfehlung finalisieren |
| 00:00–24:00 | Krypto durchgehend | Stündliche Krypto-Checks |

---

## Umsetzungs-Phasen (Schritt für Schritt)

### Phase 1 — Fundament (jetzt)
- [ ] Projektstruktur anlegen
- [ ] Python-Umgebung einrichten
- [ ] Erste Datenquelle anbinden (yfinance für Aktien)
- [ ] Einfachen Technischen-Analyse-Agenten bauen

### Phase 2 — Krypto-Daten
- [ ] CoinGecko API anbinden
- [ ] Krypto-Analyst-Agent bauen

### Phase 3 — News & Sentiment
- [ ] NewsAPI / RSS anbinden
- [ ] News-Agent bauen

### Phase 4 — Social Media
- [ ] X/Twitter API oder Scraping
- [ ] TikTok Trending Topics
- [ ] Social-Media-Agent bauen

### Phase 5 — Multi-Agenten-Orchestrierung
- [ ] Aggregator + Revisions-Agent
- [ ] Bull/Bear-Debatte implementieren
- [ ] Portfolio-Manager + Output-Format

### Phase 6 — Automatisierung & Output
- [x] Tagesroutine als Scheduled Task (taeglich 08:00 Uhr)
- [x] Log-Dateien unter trading-system/logs/
- [x] HTML-Dashboard (oeffnet sich automatisch im Browser)
- [x] Textbericht als .txt gespeichert
- [x] Groq Rate-Limit Retry-Logik

---

## APIs & Tools (geplant)

| Zweck | Tool | Kosten |
|---|---|---|
| Aktien-Daten | yfinance | kostenlos |
| Aktien (Echtzeit) | Alpha Vantage | kostenlos (limit) |
| Krypto-Daten | CoinGecko API | kostenlos |
| Nachrichten | NewsAPI | kostenlos (limit) |
| Social Sentiment | X API Basic | ~$100/Mo |
| KI-Modell | Claude API (Sonnet) | pay-per-use |
| Basis-Framework | TradingAgents (OSS) | kostenlos |

---

## Referenzen

- [TradingAgents GitHub](https://github.com/TauricResearch/TradingAgents)
- [TradingAgents Paper](https://arxiv.org/abs/2412.20138)
- [MindStudio: 24/7 Trading Agent](https://www.mindstudio.ai/blog/how-to-build-ai-trading-agent-claude-code-routines)
