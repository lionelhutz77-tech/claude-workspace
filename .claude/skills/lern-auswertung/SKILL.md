---
name: lern-auswertung
description: >-
  Haus-Regeln für das Auswerten der Schulübungen der Kinder des Users und das
  Erstellen von Lern-App-Inhalten (Projekt "Schulweg NRW", Gesamtschule NRW
  Kl. 5-7, Mathe/Deutsch/Englisch). UNBEDINGT verwenden, sobald gelöste
  Übungen/Klassenarbeiten der Kinder ausgewertet, Fehler analysiert,
  Lernstände verglichen oder neue Aufgaben/Quizinhalte für die App gebaut
  werden — auch ohne ausdrückliche Nennung des Projekts, wenn klar dieser
  Kontext gemeint ist. Spart das erneute Erklären von Ton, Format,
  Fehlerdiagnose und Fachsprache-Regeln.
---

# Lern-Auswertung & App-Inhalte (Schulweg NRW)

Dieser Skill bündelt die festen Regeln für (a) das Auswerten der gelösten Übungen der Kinder und (b) das Erstellen neuer Aufgaben für die Lern-App, damit Methodik und Format nicht jedes Mal neu erklärt werden müssen.

Kontext: PWA für die eigenen Kinder (Gesamtschule NRW, Kl. 5-7), Fächer Mathe/Deutsch/Englisch. Projekt liegt in `lern-nrw/`. Inhalte als JS-Dateien in `lern-nrw/content/` (z. B. `mathe-klasse6.js`, `englisch-6.js`). Maßgeblich ist immer der aktuelle Stand im Projekt — bei Abweichung gilt der Code.

## Grundhaltung (wichtig — es sind die eigenen Kinder)

- Warm und ermutigend: „Versuch's nochmal" statt Beschämung. **Kein** Zeitdruck/Timer, **keine** Bestenlisten.
- Ziel ist Verstehen, nicht Punktzahl. Warmes Orange statt Rot (kein Stress-Signal).
- Vor jedem Thema eine „Wozu brauche ich das?"-Zeile (Alltagsbezug).
- NRW-Lehrplan Kl. 5-7 als roter Faden.

## Auswerten gelöster Übungen

Nicht nur „richtig/falsch", sondern **Fehleranalyse**:

1. Pro Falschantwort: **warum** war genau diese Antwort falsch (typischer Denkfehler), dann Schritt-für-Schritt zur richtigen Lösung.
2. **Lernstand fortschreiben**: festhalten, was schon sitzt und welche Fehlermuster „oft / manchmal" auftreten. Beim nächsten Upload vergleichen, ob die „oft"-Punkte besser geworden sind — wenn ja, Schwierigkeit erhöhen; wenn nein, dasselbe Muster mit **anderen** Beispielen gezielt nochmal üben.
3. Pro Kind getrennt führen (mehrere Profile). Für die ältere Tochter (Kl. 6, Englisch) existiert bereits ein Lernstand mit Fehlermustern (Adjektiv/Adverb, eigene Zukunftssätze) — daran anknüpfen, nicht bei null beginnen.

## Aufgaben erstellen — Konventionen

- **Fremdsprachen-Aufgaben durchgängig in der Zielsprache** stellen: Aufgabentext UND Antwortmöglichkeiten (z. B. Englisch-Hörverstehen komplett auf Englisch). Erklärung/Feedback (`erklaerung`/`schritte`/`fehler`) darf Deutsch bleiben. Ausnahme: Vokabeltrainer (bewusst Deutsch→Englisch).
- Das **Beispiel im Eingabe-Hinweis darf nicht die Lösung sein**.
- Mathe-Eingabe tolerant: `0,5` = `0.5` = `1/2`. Uhrzeiten: 12h und 24h beide gültig.
- Aufgabentypen mischen: interaktiv (Schieberegler/SVG), Bild-Multiple-Choice und Zahleneingabe — **nicht nur** klassisches Multiple Choice.
- Pro typischer Falschantwort ein `fehler`-Feld mit gezielter Diagnose (speist die „Erklär's mir nochmal anders"-Funktion).
- **Urheberrecht:** Buchinhalte nur lesen, um zu verstehen — **eigene** Aufgaben mit **anderen** Zahlen/Beispielen erstellen, keine Buchkopien. Quellmaterial bleibt in `lern-nrw/quelle/` (nie öffentlich).
- Seiten-Etikett (`seiten`) pflegen, damit „Für eine Arbeit lernen" gezielt Seiten/Themen ziehen kann.

## Fertige Lern-Prompts

Für direktes Lernen mit Claude (Lernplan, Cheat-Sheet, Feynman, Abfragen, Verständnis-Check) gibt es eine kopierfertige Sammlung in `references/lern-prompts.md` — 12 Prompts mit Platzhaltern. Bei Bedarf dort nachsehen oder dem User passende vorschlagen.

## KI-Erklärungen

Erklärungen/Bewertungen laufen über den Groq-Worker (`llama-3.3-70b-versatile`). Ton der generierten Erklärungen: geduldig, konkret, ermutigend — denselben Maßstab anlegen wie oben.
