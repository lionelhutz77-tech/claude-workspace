# Gemini-CLI-Anbindung – Checkpoint

Stand: 04.09.2026

## Freigabe

Der Nutzer erlaubt dauerhaft, dass Codex und Claude Code über das Free-AI-Gateway
ausdrücklich ausgewählte, begrenzte und auf Geheimnisse geprüfte Projekttexte an Gemini
CLI übermitteln. `.env`, Schlüssel, Zugangsdaten, persönliche Dateien und Datenbanken sind
ausgeschlossen. Ganze Projekte dürfen nicht automatisch übertragen werden.

## Aktueller Stand

- `ai-gateway/` ist für Groq produktiv und über MCP mit Codex und Claude Code verbunden.
- Geheimnisprüfung sowie Ein-/Ausgabelimits sind vorhanden.
- Gemini CLI 0.58.0 ist global installiert.
- Der Gateway-Provider `gemini_cli` ist implementiert. Coding, Recherche, Prototyping,
  Tests und Dokumentation werden explizit dorthin geroutet.
- Gemini läuft pro Aufruf in einem leeren Temporärverzeichnis, mit bereinigter Umgebung,
  ohne geerbte API-Schlüssel und im Read-only-Planmodus.
- Zehn Gateway-Tests sind grün; das isolierte Loginprofil ist gitignoriert.
- Node.js 24.16.0 und npm 11.13.0 sind vorhanden.
- Der frühere persönliche Google-Login ist seit 18.06.2026 für Gemini CLI eingestellt.
  Der reale kostenlose Weg ist jetzt ein Gemini-API-Key aus Google AI Studio im Free Tier.
- Der Gemini-API-Key liegt ausschließlich in der gitignorierten `.env` des isolierten
  Gateway-Profils. Er wird weder angezeigt noch an Kindprozesse anderer Anbieter vererbt.
- Der neutrale Live-Test über das Gateway war erfolgreich. Tatsächlich genutzt wurden
  `gemini-3.1-pro-preview-customtools` und `gemini-3-flash-preview`.
- Der Authentifizierungsstatus wird erst nach einem erfolgreichen Live-Aufruf als verifiziert
  markiert; die bloße Auswahl einer Anmeldemethode reicht nicht mehr aus.

## Ergebnis

Die Gemini-CLI-Anbindung ist eingerichtet und verifiziert. Coding, Recherche, Prototyping,
Tests und Dokumentation können nun begrenzt und geheimnisgeprüft über das Free-AI-Gateway
ausgelagert werden. Bei ungültigem oder abgelaufenem Schlüssel schlägt der Aufruf sichtbar
fehl; es gibt keinen unbemerkten Providerwechsel.

## Nicht Teil dieses Blocks

- Keine OpenCode-/Kilo-Anbindung ohne eigene Datenfreigabe.
- Keine Anthropic- oder OpenAI-API.
- Kein automatischer Fallback, der bei Fehlern unbemerkt Daten an einen anderen Provider sendet.
