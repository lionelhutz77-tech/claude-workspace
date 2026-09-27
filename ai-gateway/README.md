# Lionel OS Free-AI-Gateway

Eine gemeinsame, limitschonende KI-Schnittstelle für alle Lionel-OS-Projekte, Codex und Claude Code.

## Aktiver Weg

- Mechanische Arbeit (Suche, Berechnung, Diff, Validierung): lokal ohne KI-Verbrauch
- Private Kurzaufgaben: lokales Ollama `qwen3:1.7b`
- Routine: Groq `openai/gpt-oss-20b`
- Tiefenanalyse/Review: Groq `openai/gpt-oss-120b`
- Reserve nach modellbezogenem HTTP 429: Groq `qwen/qwen3.8-27b`, danach
  `qwen/qwen3.6-27b`; kein Wechsel bei Auth-, Netzwerk- oder sonstigen Fehlern
- Coding, Recherche, Prototyping und Dokumentation: Gemini CLI mit eigenem
  isolierten, gitignorierten Loginprofil und leerem Arbeitsverzeichnis
- Lokal/Ollama: `qwen3:1.7b` für private Kurzaufgaben und Offline-Notbetrieb aktiv;
  ein größeres Modell wird erst nach einem Qualitätsbenchmark ergänzt
- Claude Code: separate Read-only-Prüfstrecke, nicht als allgemeiner Provider
- OpenAI API: aus (nicht als kostenlos vorausgesetzt)
- Codex CLI aus Codex heraus: aus (würde dasselbe Nutzungslimit belasten)

Die verbindliche Aufgabenmatrix steht in `../ORCHESTRATION.md`. Die Auswahl wird aus
`config.json` gelesen und von `free_ai_route` begründet zurückgegeben. Ein Wechsel zu
einem anderen externen Provider nach Fehlern erfolgt nicht automatisch. Groq und Gemini
stellen hier keinen verlässlich abfragbaren Restzähler bereit; das Gateway erkennt reale
Fehler, erfindet aber keine Kontingentstände. Ollama bleibt auf `127.0.0.1` beschränkt.

## Datenschutzgrenzen

Nur der Text im Parameter `prompt` wird verarbeitet. Das Gateway liest keine Projektdateien
für Prompts ein. Maximal 12.000 Eingabezeichen; Ausgaben sind zusätzlich zum absoluten
6.000-Zeichen-Limit profilbezogen auf 1.800 (Routine), 3.200 (Worker) oder 3.600
(Tiefenanalyse) begrenzt. Ein Aufrufer kann diese Spargrenze nicht erhöhen. Verdächtige Schlüssel,
Tokens, Passwörter und Private Keys werden vor externen Aufrufen blockiert. `personal` darf
nur über den lokalen Ollama-Provider laufen. Die Groq-Zugangsdaten werden lokal aus
der Prozessumgebung oder ausschließlich als einzelner Wert aus den bekannten Projekt-`.env`
gelesen und niemals ausgegeben oder übertragen.

Die Groq-Reserve bleibt beim bereits freigegebenen Provider, verwendet nur aktuell
dokumentierte Free-Plan-Modelle und weist das tatsächliche Modell sowie das wegen 429
verlassene Ausgangsmodell im Ergebnis aus. `service_tier=auto` wird nicht verwendet.

Gemini erhält ebenfalls nur den expliziten `prompt`. Der Prozess läuft in einem jedes Mal
neu erzeugten leeren Temporärverzeichnis, im Read-only-Planmodus und mit einer bereinigten
Umgebung ohne Projekt- oder API-Schlüssel. Weder `--all-files` noch Projektpfade werden verwendet.

## OmniRoute-Prüfung

Der Videovorschlag zu OmniRoute wurde geprüft. OmniRoute ist MIT-lizenziert, schafft aber
selbst kein Gratis-Kontingent; es bündelt providerabhängige Free-Tiers und eigene Logins.
Die aktuelle npm-Distribution ist rund 452 MB entpackt, verwaltet OAuth-/API-Zugangsdaten
und enthält auch privilegierte MITM-/Fingerprint-Funktionen. Sie ersetzt das kleine,
fail-closed Gateway daher nicht und ist in `config.json` ausdrücklich deaktiviert.
Eine spätere Anbindung setzt einen geprüften Minimal-Build, verschlüsselte lokale Speicherung,
Loopback-Bindung und eine explizite Free-Provider-Allowlist voraus. Die sofort nutzbare
Verbesserung aus dem Vorschlag sind die profilbezogenen Ausgabegrenzen, die den knappen
Codex-Kontext direkt schützen.

## Benutzung

Nach einem Neustart von Codex bzw. Claude Code stehen die MCP-Werkzeuge
`free_ai_status`, `free_ai_usage`, `free_ai_preflight`, `free_ai_route` und `free_ai_generate` bereit. Die lokale Diagnose läuft mit:

```powershell
& 'C:\Users\HP\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' .\ai-gateway\cli.py status
& 'C:\Users\HP\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' .\ai-gateway\cli.py usage
& 'C:\Users\HP\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' .\ai-gateway\cli.py preflight
```

Der Preflight ruft kein Modell auf und verbraucht kein KI-Kontingent. Er prüft zusätzlich
den konsistenten Lionel-Auftrag und die letzte gebundene Vollvalidierung. Seine Antwort
enthält nur den kurzen Resume-Stand; die vollständige Historie bleibt lokal in
`ARBEITSSTAND.json`, damit wiederholte Prüfungen keinen unnötigen Codex-Kontext belegen.
Der Lionel-Gate-Check vergleicht den gespeicherten Quellbestand mit dem aktuellen
Inventar. Nach einem archivierten Auftrag ist nur der erwartete Abschlusswechsel
von `control/next-task.json` ausgenommen; geänderte Quellen oder Tests erzeugen
eine sichtbare Warnung statt eines scheinbar aktuellen PASS.

Ein Gemini-API-Key aus Google AI Studio wird sicher und ausschließlich im isolierten,
gitignorierten Gateway-Profil hinterlegt mit:

```powershell
& .\ai-gateway\gemini_key_setup.ps1
```

Der Schlüssel wird bei der Eingabe nicht angezeigt. `gemini_login.ps1` bleibt nur als
manuelles Diagnosewerkzeug erhalten; der frühere persönliche Google-Login wird von der
aktuellen Gemini CLI nicht mehr unterstützt.
