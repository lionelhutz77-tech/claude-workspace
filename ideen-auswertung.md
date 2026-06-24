# Ideen-Auswertung — Ordner `Pictures/Ideen`

Auswertung der gesammelten Screenshots/Reels (Stand 2026-06-24). Sortiert nach Projekt,
mit konkretem „was nehmen wir mit". Quelle jeweils als `IMG_xxxx`.

> ⚠️ **Wichtigster Fund vorab — Sicherheit:** Eine Screenshot war eine GroqCloud-Warnmail
> (`IMG_8488`): der Groq-Key `…83C7` ist **öffentlich auf GitHub geleakt**. Ursache gefunden:
> `trend-scout/.env` war im **öffentlichen** Repo `claude-workspace` eingecheckt (kein
> `.gitignore` im Ordner). Derselbe Key wird auch in `trading-system/.env` genutzt.
> → Siehe Abschnitt **Sicherheit** unten. **Key muss rotiert werden (Groq-Dashboard).**

---

## 🟢 trading-system — größter Mehrwert

Mehrere Quellen liefern **strukturierte LLM-Analyse-Prompts** (Rollenspiel „Analyst bei
Institut X"). Direkt als Vorlage für die Agenten/den Bericht übernehmbar.

**`derekanddakota` — 5 Institutions-Prompts** (`IMG_8526`–`8530`):
1. *Goldman-Sachs-Stock-Screener* — Top-10-Screen mit P/E vs. Sektor, 5J-Umsatzwachstum,
   Debt/Equity, Dividenden-Score, Moat-Rating, Bull/Bear-Kursziele, Risk-Score 1–10,
   Entry-Zonen & Stop-Loss. Input: Risikoprofil/Betrag/Horizont/Sektoren.
2. *Morgan-Stanley-DCF* — vollständige DCF: 5J-Umsatz, Margen, FCF, WACC, Sensitivität,
   innerer Wert vs. Kurs, Verdikt über/unter/fair. Input: Ticker.
3. *Bridgewater-Risk-Framework* — Korrelations-/Sektor-/Geo-Risiko, Zins-Sensitivität,
   Rezessions-Stresstest, Liquidität, Position-Sizing, Hedging, Rebalancing. Input: Holdings.
4. *JPMorgan-Earnings-Breakdown* — Earnings-Historie vs. Schätzung, EPS-Forecast,
   Segment-Wachstum, Guidance-Review, Optionsmarkt-Erwartung, Bull/Bear-Szenarien.
5. *BlackRock-Portfolio-Construction* — Asset-Allocation %, ETF-Vorschläge, Core/Satellite,
   erwartete Rendite, Drawdown, Steuer-effizient, Rebalancing, DCA.

**`berttrading` — 5 Analyse-Prompts** (`IMG_8520`–`8525`): The Deep Dive · „How [X] makes
money" · The Peer Comparison · „Most growth per dollar" · The Bear Case. Gleiche Idee,
knapper. Gut als Slide-/Berichts-Bausteine.

**`sven_schnurr` — 5-Agenten-Framework „jeder denkt anders"** (`IMG_8392`): Risk Hunter ·
First Principles · Opportunity Scout · Pure Problem · Action Now. → passt 1:1 auf unser
Multi-Agent-Council UND die allgemeine Council-Review-Arbeitsweise.

**`valuebyramin` — Claude financial-services-plugins** (`IMG_8501`–`8512`): offizielle
Anthropic-Plugins via Claude-Marketplace (GitHub `financial-services-plugins`): Equity
Research, Market Researcher, **Morning Note** (Cowork `/morning-note`). → Idee: ein
„Morning-Note"-Ablauf für den 08:00-Trading-Bericht.

> **Übernehmen:** Die Institutions-Prompts als wiederverwendbare Bausteine in die Agenten
> einarbeiten (Groq). Das 5-Agenten-Schema als Review-Layer. Kostet nichts, klarer Gewinn.
> **NICHT übernehmen:** `miles_deutscher`/`joeparys`/`britt.trades`/`valie.trades` —
> „Kommentier TRADE, mein Bot printet im Schlaf $500"-Reels (`IMG_8489`–`8499`, `8536`).
> Das ist Promo/typische Trading-Bot-Masche, kein verlässliches Signal. Höchstens als
> Negativ-Beispiel (Risiko-Aufklärung im Bericht).

## 🟣 instagram-system / Content-Strategie

**`aiautomationchannels` — „PewDiePie-Playbook" (5 Claude-Prompts)** (`IMG_8514`–`8519`):
1. Find your niche · 2. Build a channel people remember · 3. Build your content machine
(90-Tage-Plan) · 4. Write videos people finish (Retention) · 5. Make people click
(Thumbnails/Titel/CTR). → übertragbar auf @kiai1977-Reels & ggf. YouTube.

**Eigene Referenz-Posts** (`IMG_8311`, `IMG_8312`): zwei @kiai1977-Posts als Muster für
Caption/Hashtag-Stil — deckt sich mit unseren Regeln (gut zur Konsistenzprüfung).

**Higgsfield-UGC „Morning Note"** (`IMG_8327` „Afternoon, steven" / stee.ugc): personalisierte
UGC-Automation. Interessant fürs Verständnis des Soul-Workflows, den wir schon nutzen.

## 🔵 lern-nrw (Lern-App der Kinder)

- **`Retain`** (`IMG_8484`, study.mit.sarina „Tipps für ein 0,7 Abi"): Spaced-Repetition-
  Karteikarten-App. → Methodik (Wiederholungsintervalle) ist genau das, was unsere Lernbox
  schon andeutet; als Feature-Inspiration für die PWA.
- **`hailolernen` „Fresh-Methoden-Kreisen"** (`IMG_8511`): Lernmethoden-Content.

## ⚪ Sonstiges / persönlich (kein Projekt)

- **Husatech-Angebot Batteriespeicher ~12 kWh, Oberhausen** (`IMG_8513`): privates
  PV-/Speicher-Angebot. Nur ablegen, kein Projektbezug.
- **„Die letzten Glühwürmchen" (1988, Krieg/Drama)** (`IMG_8512`): Film-Notiz. Evtl.
  thematischer Tonfall-Bezug, sonst privat.
- **Kathrin L. Deko/Sprüche** (`IMG_8375`, `IMG_8376`): privat.
- **`dawidprzybylski`/`michael_ehlers` — Claude Connectors/Skills, „Code Review Graph",
  „REPO"** (`IMG_8305`–`8308`, `8328`/`8329`): Claude-Code-Tipps (Custom Connectors/MCP).
  Bezug zum laufenden MCP-Setup — als Lernquelle vermerkt.
- **`herr_tech` / „1-Personen-Unternehmen kopieren"** (`IMG_8310`), **derekanddakota
  „Digital Real Estate"** (`IMG_8531`–`8535`): Side-Hustle-Pitches → Bezug `nebenerwerb`.
  Ehrlich: „Lead-Gen-Websites $50k/Monat im Schlaf" ist Hype-Framing; Kern (Lead-Gen für
  lokale Betriebe) ist legitim, aber nichts Neues ggü. unserer Nebenerwerb-Bewertung.

## 🎬 Videos (ausgewertet: ffmpeg-Frames + Groq-Whisper-Transkript, 2026-06-24)

**Projektrelevant (3):**
- **V1 (MCWB0416) — Price-Action/Kerzen-Lehre:** Body/Wicks als Käufer-vs-Verkäufer-Duell,
  Engulfing-Setup, 3 grüne Kerzen = Momentum, „Unentschlossenheit → Überzeugung". Sauberer
  Erklär-Baustein → ggf. für `pattern_agent`/Bericht-TA-Erklärung. *trading-system.*
- **V2 (MKXD1692) — Krypto-Marktstruktur (sehr gehaltvoll):** Open Interest, Funding Rate,
  Spot-Delta, Liquidationen, Fair Value Gap, Value Area Low/High, Range-Trading, bärischer
  Trend. → echte Erweiterungs-Idee für die Krypto-Analyse (siehe Backlog). Auch Discord/TG-
  Promo, also Framework nehmen, nicht den „folge mir". *trading-system.*
- **V6 (LPCR5976) — CMBlue Lignin-Batterie:** deutsche Nicht-Lithium-Langzeitspeicher
  (Holzabfall/Lignin, nicht brennbar, Mercedes/Samsung-Investor, ab ~10h Speicherung 6× günstiger
  als Lithium). → Investment-Thema (Energiespeicher) UND persönlich relevant (passt zum
  Husatech-Speicherangebot `IMG_8513`). *trading-system Universe + privat.*

**Nicht projektrelevant (7):** V3/V4/V7/V8/V9/V10/V11 = Entertainment/Memes (Doberman-Futter-
Challenge, Straßen-Prank, Tanz-Clips, Mariachi). Höchstens als Reel-Format/Hook-Referenz, kein
inhaltlicher Übernahme-Wert.

**Defekt (1):** V5 (IIHP6315.MP4) ist nur 14 Bytes („moov atom not found") — nicht lesbar.

---

## 🔐 Sicherheit — Sofortmaßnahmen (offen, von dir zu tun)

1. **Groq-Key rotieren:** im Groq-Dashboard den Key `…83C7` **widerrufen** und einen neuen
   erstellen (Groq deaktiviert ihn ohnehin).
2. **Neuen Key eintragen** in `trading-system/.env` **und** `trend-scout/.env`
   (beide nutzen denselben Key).
3. **Bereits erledigt (lokal, gestaged, noch nicht committet):** `trend-scout/.env` aus
   Git-Tracking entfernt + `trend-scout/.gitignore` angelegt. → committen + pushen, damit
   die Datei aus dem aktuellen Stand verschwindet.
4. **Hinweis:** Der alte Key bleibt in der Git-Historie (Repo ist **public**). Das Rotieren
   macht ihn wertlos — das ist die eigentliche Absicherung. History-Scrubbing (BFG) optional.
5. **Grundsatz fürs ganze Repo:** `claude-workspace` ist öffentlich → **nie** Secrets
   committen; jeder Unterordner braucht eine `.gitignore` mit `.env`.
