# Free-AI-Gateway-Migration des Trading-Systems

Stand: 04.09.2026

## Ziel

Alle generativen Trading-Agenten verwenden eine gemeinsame, begrenzte KI-Schicht. Telegram,
Dashboard, Datenbanken und deterministische Signalberechnung bleiben davon getrennt.

## Umgesetzt

- Revisions-, Bull/Bear-, Deep-Dive-, Vorläufer- und Lern-Agent rufen
  `agents/free_ai_client.py` statt des Groq-SDK direkt auf.
- Routine und Tiefe bleiben auf den live geprüften Groq-Routen; Recherche nutzt Gemini CLI.
- Jeder Aufruf besitzt ein eigenes Ausgabelimit; das Gateway begrenzt zusätzlich global.
- Kein stiller Providerwechsel. Rate-Limit-Wiederholung bleibt innerhalb derselben Route.
- Lokale Metadaten-Telemetrie ohne Prompt, Antwort, Schlüssel oder persönliche Inhalte.
- Telegram lädt seine `.env` jetzt unabhängig vom aktuellen Arbeitsverzeichnis.
- Bei KI-Ausfall baut `main.ki_phase()` weiterhin das bestehende deterministische Fallback-Signal,
  das vom Telegram-Formatter verarbeitet wird.
- Ollama 0.33.3 installiert. Qwen3 1.7B ist ausschließlich für private einfache Kurzaufgaben
  aktiv; 0.6B war unzuverlässig, 4B auf der CPU zu langsam.

## Verifikation

- 15 Gateway-Tests: PASS.
- 7 Trading-Tests: PASS.
- Python-Syntaxprüfung der betroffenen Pipeline: PASS.
- Live-Routen `routine`, `deep`, `research`: PASS.
- Ollama 1.7B: alphabetische Sortierung und regelbasierte JSON-Klassifikation korrekt;
  rund 12–26 Sekunden.
- Telegram-Konfiguration: Token und Chat-ID geladen.
- Telegram `getMe` und `getChat`: PASS, ohne Nachricht zu versenden.
- KI-Ausfall bis Telegram-kompatibles Fallback-Signal: PASS.
- `git diff --check`: PASS.

## Noch offen

- Unabhängiger Claude-Code-Read-only-Abschlussreview. Der Aufruf ist vorbereitet, aber die
  lokale Claude-OAuth-Sitzung ist abgelaufen. Nach Nutzer-Login denselben bereinigten Diff
  prüfen lassen; bei PASS Checkpoint schließen.
- Gamma/Canva erst nach ausdrücklicher Plugin-Auswahl verbinden. OpenCode/Kilo erst nach
  eigener Datenfreigabe und harter Free-/Kostensperre.
