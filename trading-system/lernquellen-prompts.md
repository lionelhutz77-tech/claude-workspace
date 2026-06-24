# Lernquellen: Institutions-Analyse-Prompts (aus Pictures/Ideen, 2026-06-24)

Wiederverwendbare LLM-Prompt-Bausteine zum Einarbeiten in die Agenten (Groq).
Noch NICHT in die Agenten integriert — Vorschlag, siehe unten. Quelle: gesammelte
Reels (`derekanddakota`, `berttrading`, `sven_schnurr`). Vollkontext: ../ideen-auswertung.md

## 5 Institutions-Prompts (derekanddakota)
1. **Stock-Screener (Goldman-Stil):** Top-10-Screen mit P/E vs. Sektor, 5J-Umsatzwachstum,
   Debt/Equity, Dividenden-Score, Moat-Rating, Bull/Bear-Kursziele, Risk-Score 1–10,
   Entry-Zonen + Stop-Loss. Input: Risikoprofil, Betrag, Horizont, Sektoren.
2. **DCF (Morgan-Stanley-Stil):** 5J-Umsatz, Margen, FCF, WACC, Sensitivität, innerer Wert
   vs. Kurs → Verdikt über-/unter-/fair bewertet. Input: Ticker.
3. **Risk-Framework (Bridgewater-Stil):** Korrelations-, Sektor-, Geo-Risiko, Zins-
   Sensitivität, Rezessions-Stresstest, Liquidität, Position-Sizing, Hedging, Rebalancing.
   Input: aktuelle Holdings.
4. **Earnings-Breakdown (JPMorgan-Stil):** Earnings vs. Schätzung, EPS-Forecast, Segment-
   Wachstum, Guidance-Review, Optionsmarkt-Erwartung, Bull/Bear-Szenarien. Input: Company.
5. **Portfolio-Construction (BlackRock-Stil):** Asset-Allocation %, ETF-Vorschläge,
   Core/Satellite, erwartete Rendite, Drawdown, Steuer-Effizienz, Rebalancing, DCA.

## Knappe Varianten (berttrading)
The Deep Dive · „How [X] makes money" · Peer Comparison · „Most growth per dollar" · Bear Case.

## 5-Agenten-Review (sven_schnurr) — passt auf unser Multi-Agent-Council
- **Risk Hunter** — was kann schiefgehen? Worst-Case, Blind Spots, falsche Annahmen.
- **First Principles** — Vorannahmen ignorieren, Problem von Grund auf neu denken.
- **Opportunity Scout** — Chancen, Hebel, Trends, ungenutzte Assets.
- **Pure Problem** — Kontext ausblenden, nacktes Problem ansehen.
- **Action Now** — nur: was ist heute/morgen konkret umsetzbar?

## Integration (Stand 2026-06-24)
**Erledigt in `bull_bear_debate.py`** (additive Prompt-Anreicherung, keine neuen Groq-Calls,
Ausgabeformat/Parsing unverändert):
- Bull-Prompt: „Growth per Dollar" + Peer-Comparison-Linse.
- Bear-Prompt: strukturierter Bear-Case (Bewertungs-Check teuer ggü. Historie/Peers +
  quantifiziertes Abwärts-Szenario).
- Portfolio-Manager: 5-Brillen-Denkweise (First Principles / Risk Hunter / Opportunity
  Scout / Pure Problem / Action Now) als gedanklicher Prüf-Layer vor dem Urteil.
- Verifiziert: `py_compile` ok, Parsing-Felder + Format-Block unverändert. Live-Debatte
  NICHT ausgeführt (spart Groq-Tagesbudget; greift automatisch beim 08:00-Lauf).

## Noch offen
- „Morning Note"-Format (Anthropic financial-services-plugins) als Vorlage für den 08:00-Bericht.
- Die expliziten Institutions-Prompts (DCF/Screener/Earnings) als optionalen Tiefen-Modus.
