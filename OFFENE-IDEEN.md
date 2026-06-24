# Offene Ideen — Backlog (eine Quelle der Wahrheit)

Stand 2026-06-24. Reihenfolge = grobe Priorität. Status: ⬜ offen · 🔄 in Arbeit · ✅ erledigt.
Wir gehen **eins nach dem anderen** an; Claude schlägt das nächste vor, du gibst das Go.

## trading-system
- ⬜ **Tiefen-Modus für den 08:00-Bericht** — optionaler „Deep Dive" mit Institutions-Prompts
  (DCF / Screener / Earnings-Breakdown). Token-Budget abwägen (Groq ~100k/Tag). *Höchster Nutzen.*
- ⬜ **„Morning Note"-Format** (Anthropic financial-services-plugins) als Berichts-Vorlage.

## instagram-system / Content
- ⬜ **PewDiePie-Playbook** (5 Content-Prompts: Niche / Branding / Content-Machine /
  Retention / CTR) als wiederverwendbare Vorlage für Reels/Hooks einbauen.

- ⬜ **Krypto-Marktstruktur** (aus Video V2): Analyse um Funding Rate, Open Interest,
  Fair Value Gap & Value Area erweitern. Braucht Derivate-Datenquelle (Exchange-API) —
  Machbarkeit/Kosten prüfen. *Echter Mehrwert, mittlerer Aufwand.*

## lern-nrw
- ⬜ **Spaced-Repetition** (à la „Retain") als PWA-Feature für die Lernbox prüfen.

## Erledigt (Referenz)
- ✅ Boomer-Karussell item_16 gebaut, freigegeben, Auto-Post geprüft.
- ✅ Sicherheits-Leak (Groq-Key) behoben: rotiert, beide .env neu, aus Repo entfernt, .gitignore-Netz.
- ✅ Trading-Prompts integriert (Bear-Case, Peer-Comparison, 5-Brillen) in bull_bear_debate.py.
- ✅ Ideen-Ordner gesichtet & sortiert (ideen-auswertung.md).
- ✅ trump-scanner von Railway → Cloudflare Worker (Cron, kostenlos) migriert & live.
  **Offen (du):** Railway-Deployment abschalten/löschen, damit nichts mehr läuft/kostet.
- ✅ 11 Videos ausgewertet (ffmpeg-Frames + Groq-Whisper); 3 relevant (V1 Price-Action,
  V2 Krypto-Marktstruktur, V6 CMBlue-Batterie), Rest Entertainment, V5 defekt.
