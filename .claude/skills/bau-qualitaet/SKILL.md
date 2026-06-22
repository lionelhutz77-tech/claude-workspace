---
name: bau-qualitaet
description: >-
  Arbeitsweise für sauberes, verlässliches Bauen und Debuggen in den Projekten
  des Users (Python-Automatik, Cloudflare Workers, PWA, Trading/Instagram/Lern-
  App). UNBEDINGT anwenden bei jeder nicht-trivialen Code-Aufgabe: neues Feature,
  Bugfix, Refactoring, „warum geht das nicht", oder wenn etwas „fertig" gemeldet
  werden soll. Erzwingt Planen-vor-Coden, systematisches Root-Cause-Debugging und
  Verifikation vor „erledigt" — statt Raten und vorschnellem Fertigmelden.
---

# Bau-Qualität — Arbeitsweise für verlässliches Bauen

Inspiriert von bewährten Agenten-Methodiken (u. a. „superpowers"), zugeschnitten auf die Projekte des Users. Ziel: weniger Fehlschläge, weniger Nacharbeit, ehrliche Ergebnisse. Der User schätzt reife Produkte und ehrliches Feedback ([[feedback_work_style]], [[feedback_council_review]]).

## 1. Vor dem Coden: kurz denken, dann bauen

Bei nicht-trivialen Aufgaben **erst** klären, dann tippen:
- Was ist das eigentliche Ziel? Was zählt als „fertig"?
- Welche Dateien/Teile sind betroffen? Gibt es bekannte Stolpersteine (FLUX-Hände, API-Limits, Symbol-Mismatches)?
- Bei Unklarheit: **eine** gezielte Rückfrage statt in die falsche Richtung loslaufen (Verständnis-Check).
- Größere Sachen in kleine, einzeln prüfbare Schritte zerlegen.

Nicht über-planen: Für Einzeiler/offensichtliche Änderungen direkt machen.

## 2. Beim Debuggen: Ursache finden, nicht Symptome pflastern

Reihenfolge bei „geht nicht":
1. **Reproduzieren** — den Fehler zuverlässig auslösen, echte Fehlermeldung/Logs lesen (nicht raten).
2. **Eingrenzen** — wo genau bricht es? Zwischenwerte ausgeben, Annahmen einzeln prüfen.
3. **Ursache benennen** — die *eine* Wurzel, nicht nur das Symptom. Erst wenn klar ist *warum*, fixen.
4. **Gezielt fixen** — minimaler Eingriff an der Wurzel, keine Schrotflinte.

Keine „probier mal das"-Schleifen ohne Diagnose. Wenn eine Hypothese falsch war: notieren, nächste prüfen — nicht im Kreis raten.

## 3. Vor „fertig": verifizieren

Nie „erledigt" melden, ohne es geprüft zu haben. Je nach Aufgabe:
- Code tatsächlich **ausführen** / Skript laufen lassen / Endpoint testen.
- Bei der Instagram-Pipeline: generierte Bilder gegen die Redaktions-Checkliste prüfen (Anatomie, 5 Finger, Kontrast) — [[feedback_carousel_qualitaet]].
- Bei Workern: nach Deploy einen echten Request gegen den Endpoint.
- Ehrlich berichten: Was getestet, was nicht, was noch offen. Fehlschläge mit echter Ausgabe zeigen, nicht beschönigen.

Faustregel: Wenn ich es nicht ausgeführt/geprüft habe, sage ich „ungetestet", nicht „funktioniert".

## 4. Tests, wo sie sich lohnen

Für Logik mit klaren Ein-/Ausgaben (Rechenwege, Parser, Signal-Berechnungen) lohnt ein kleiner Test zuerst — er fixiert das gewünschte Verhalten und fängt Regressionen. Für UI/Bild/Prompt-Arbeit ist visuelle/redaktionelle Prüfung sinnvoller als Unit-Tests. Pragmatisch entscheiden, nicht dogmatisch.

## 4b. Riskantes isolieren (Git-Worktree)

Bei größeren/experimentellen Umbauten, bei denen unklar ist, ob sie funktionieren, in einem **Git-Worktree** arbeiten statt direkt im Hauptstand. So bleibt das laufende Projekt (täglich postende/handelnde Automatik!) unberührt, bis die Änderung verifiziert ist. Klappt's nicht, wird der Worktree einfach verworfen. Für kleine, sichere Änderungen unnötig.

## 5. Sauber abschließen

- Token sparen: knapp berichten ([[feedback_antwortlaenge]]), keine Roman-Zusammenfassungen.
- Was wirklich neu/wichtig ist, ins passende Memory oder Projekt-Doc.
- Offene Punkte klar benennen, statt sie zu verstecken.

## Warum das wirkt

LLMs neigen dazu, plausibel klingende Antworten ohne echte Prüfung zu geben und Symptome statt Ursachen zu behandeln. Diese vier Reflexe — planen, Ursache suchen, verifizieren, ehrlich abschließen — sind genau die Stellen, an denen in den bisherigen Projekten Zeit verloren ging. Sie ersetzen kein Nachdenken, sie erzwingen es an den richtigen Momenten.
