# CLAUDE.md

Leitfaden für Claude Code in diesem Workspace. Dies ist **kein Scratchpad mehr**, sondern eine Sammlung echter Projekte. Jedes Projekt hat eine eigene `CLAUDE.md` mit Details — diese hier gibt den Überblick und die projektübergreifenden Regeln.

## Projekte (jeweils eigene CLAUDE.md)

- `trading-system/` — Multi-Agent-Signale (Aktien/Krypto), täglich 08:00. Skill: **trading-bericht**.
- `instagram-system/` — @kiai1977 „Früher & Heute"-Pipeline, Auto-Post 18:00. Skill: **kiai-content**.
- `lern-nrw/` — PWA-Lernapp für die Kinder (NRW Kl. 5–7), GitHub Pages + Cloudflare Worker. Skill: **lern-auswertung**.
- `alpaca-trader/` — Paper-Trading-Bot (SMA200), Alpaca-API.
- `tailwind-scanner/` — unterbewertete Aktien via Makro-Signale, GitHub Actions.
- `immobilien-rechner/` — Excel-Vermietrechner. `angst-erfahrungsbericht/`, `trend-scout/`, `trump-scanner/` — kleinere/Content-Vorhaben.

## Projektübergreifende Regeln

- **LLM = Groq** (`llama-3.3-70b-versatile`), kostenlos. **Nie** die Anthropic-API vorschlagen.
- **Sprache:** Deutsch, „du"-Form. Antworten **knapp** halten (ausführlich nur auf Wunsch).
- **Keine persönliche Anlageberatung** und keine echten Trades/Geldbewegungen ausführen (Trading/Alpaca = nur Werkzeug-Output/Paper).
- **Plattform:** Windows, PowerShell. Kein Office am PC → Word/PDF/Excel über die docx/pdf/xlsx-Skills erzeugen.
- Secrets immer in `.env` (gitignored); in der Cloud GitHub Secrets.

## Arbeitsweise (Skills)

- **bau-qualitaet** — bei jeder Code-Aufgabe: planen → Ursache statt Symptom → verifizieren vor „fertig".
- Jede Anfrage durch internes **Council-Review** (Sinn/Realismus/Aufwand/beste Umsetzung/Gegenstimme), neutrales Urteil, nicht default-positiv.
- Machbarkeit vorab prüfen, bekannte Blocker früh nennen.
- Nützliche Tipps/Methoden proaktiv übernehmen (als Inspiration, nicht 1:1); dabei Token sparen.

## Weiteres

- `.claude/skills/` — eigene Skills. `KONTEXT.md` — portables Kontext-File für die Claude-App.
- `nvld-tipps-index.md` / `nvld-uebernahme-report.md` — Auswertung der NVLD-Claude-Tipps.
- `claude-ressourcen.md` — kuratierte Skill-/Prompt-Quellen. `KOSTEN.md` — Kostenliste (~70 €/Monat-Ziel).
