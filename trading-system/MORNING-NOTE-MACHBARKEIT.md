# Morning Note: Machbarkeit und Datenvertrag

Stand: 2026-09-13. Die Vorprüfung ist umgesetzt: Die Morning Note erscheint
im Textbericht und Dashboard, **nicht** als zusätzlicher Telegram-Versand.
Keine Anlageempfehlung.

## Entscheidung

Das Format aus Anthropic's öffentlicher `morning-note`-Vorlage ist als **kurzer
Lese-Einstieg** für den bestehenden 08:00-Bericht nützlich. Den fremden Plugin-
Stack oder dessen kostenpflichtige Daten-Connectoren installieren wir dafür
nicht. Die bereits laufende Pipeline und Telegram-Ausgabe bleiben unverändert.

Quelle: https://github.com/anthropics/financial-services/blob/main/plugins/vertical-plugins/equity-research/skills/morning-note/SKILL.md

## Was lokal schon vorliegt

- `main.py::erstelle_tagesbericht` erstellt Signale, Preise, Ziel, Stop-Loss,
  Risiko, News-Zahl, technische Sicht und Bull/Bear-Ergebnis.
- `agents/telegram_agent.py::format_tagesbericht` zeigt Marktsentiment,
  Musterdepot und kompakte Kauf-/Abwarten-Signale; `main.py` versendet Telegram
  vor dem optionalen Dashboard.
- `dashboard.py::erstelle_html` stellt Signale, Backtest-Kontext und
  Detailberichte dar.

Das veraltete `PROJEKT.md` ist **kein Nachweis** für aktuelle Live-Daten: die
Phase-1-Checkboxen und die dort genannte Claude-API widersprechen dem aktuellen
Gateway-Stand. Maßgeblich sind ausführbare Pfade, Tests und die Projektwahrheit.

## Datenvertrag für eine spätere reine Darstellungsschicht

| Feld | Quelle | Fehlregel |
|---|---|---|
| Stichtag mit Zeitzone und Datenfrische | Laufzeit + Zeitstempel jeder Quelle | „Stand unbekannt“, keine Behauptung zu Overnight/Pre-Market |
| Top-Signal und Gegenargument | `finale`, technische Signale, Bull/Bear | Nur vorhandene Signale; bei Unsicherheit „kein belastbares Top-Signal“ |
| Kurs/Entry/Target/Stop und Horizont | vorhandene Signalwerte | Fehlende Werte als `—`, nicht schätzen |
| Ereignis/Katalysator | belegter Quellverweis, Veröffentlichungs- und Erfassungszeit | Ohne Quelle als unbestätigt markieren, kein kurzfristiger Trigger |
| Earnings: Ist, Konsens, Guidance | primäre Filing-/IR-Quelle plus Konsensdaten | Ohne verifizierten Konsens keine Beat/Miss-Tabelle |
| Termine heute | verifizierte Kalenderquelle + Zeitzone | Abschnitt auslassen, nicht Termine erfinden |
| Musterdepot und Segment | bestehende Depot-/Segmentdaten | Basis und Stichprobe nennen; keine 80%-Trefferquote ableiten |
| Backtest-/Trefferquote | historischer Signaltyp, Stichprobe, Zeitraum | Bei dünner/überlappender Stichprobe „nicht belastbar“ |

## Umgesetzter Minimalumfang

`morning_note.py` erzeugt eine **deterministische** Kopfsektion aus den bereits
vorliegenden Signalwerten. `main.py` und `dashboard.py` zeigen sie an. Telegram
bleibt unangetastet, damit weder Länge noch Zustellung beeinträchtigt werden.
Ohne verifizierte Quelle/Frische werden Overnight-, Earnings- und Terminmeldungen
ausdrücklich **nicht** behauptet. Fehlende Preise bleiben `—`, leere Signale
erzeugen keinen erzwungenen Top-Call, und HTML escaped externe Assetnamen.
13 Tests der Trading-Suite einschließlich Null-/Leerfall, Ausgabeintegration
und Telegram-Unverändertheit bestanden; Python-Syntax ebenfalls bestanden.

Ein späterer Ereignis-/Earnings-Ausbau braucht je Meldung Quelle,
Veröffentlichungs- und Erfassungszeit sowie bei Beat/Miss einen belegten
Konsenswert. Ohne diese Daten bleibt der Abschnitt bewusst aus.
