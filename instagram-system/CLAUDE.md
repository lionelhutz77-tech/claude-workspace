# CLAUDE.md — Instagram-System (@kiai1977)

Vollautomatische Karussell-/Reel-Pipeline für @kiai1977 („Früher & Heute"-Content). Zugriff via offizielle Instagram-API. Setup-Stand: `SETUP.md`.

## Inhaltsregeln — zuerst lesen
Für ALLE Inhalte (Themen, Texte, Bild-Prompts, Captions) gilt der Skill **kiai-content** sowie:
- `vorlagen/content_richtlinien.json` — Ton, Tabus, persönliche Themen
- `vorlagen/redaktions_checkliste.md` — Prüf-Sequenz VOR jeder Freigabe
Diese Dateien sind maßgeblich (bei Abweichung gewinnt die Datei).

## Ausführen
- Pipeline: `python daily_pipeline.py` — Modi: `--dry` (nur bauen), `--publish-approved` (nächstes freigegebenes posten), `--publish-queue`, `--publish-reel-today`.
- Auto-Post: Windows-Aufgabe „KIAI Auto-Post 18 Uhr" → `--publish-approved` (postet nur Ordner mit `APPROVED.txt`, ohne `PUBLISHED.txt`).
- Freigeben: `python -m tools.approve output/queue/item_NN` (setzt APPROVED.txt — sonst wird NIE gepostet!).
- Token-Refresh automatisch via „Instagram Token Guard" (`token_guard.py`, täglich 10:00).
- Secrets in `.env` (gitignored).

## Aufbau
- `daily_pipeline.py` — Orchestrierung. `tools/` — theme_generator, carousel_builder, build_queue, fix_queue_item (einzelne Bilder neu), preview_text (Text zuerst, kostet kein FLUX), carousel_to_reel, publish_carousel, video_host, reply_helper.
- `vorlagen/` — Regeln + Templates. `output/queue/item_NN/` — Vorrat.

## Konventionen / Gotchas
- **Prozess: Text zuerst** (preview_text) → User-Freigabe → Bilder → Checkliste C (Anatomie) auf JEDES Bild → fehlerhafte einzeln neu → erst dann zeigen.
- Bilder: **Cloudflare FLUX** (flux-1-schnell), 10.000 Neurons/Tag → reicht nicht für viele Re-Renderings; Fallback Stable Horde (schwächere Hände). Higgsfield (Basic, Credits sparsam) als Premium-Alternative.
- FLUX-Schwächen: Hände (5 Finger, keine Close-ups), ganze Figuren, europäischer Kontext. Themen mit Hand-/Geräte-Close-ups (z. B. „Smartwatch") meiden.
- Immer „du"-Form. LLM-Texte über Groq.
- Einmal-ScheduledTasks mit Uhrzeit in der Vergangenheit feuern NIE.

## Arbeitsweise
Skill **bau-qualitaet** + Redaktionspflicht: nichts ungeprüft als „fertig" zeigen.
