---
name: kiai-content
description: >-
  Verbindliche Haus-Regeln für Content des Instagram-Accounts @kiai1977 ("Früher
  & Heute"-Karussells/Reels, nachdenklicher Gesellschafts-Content). UNBEDINGT
  verwenden, sobald es um @kiai1977 geht — also beim Entwerfen, Texten oder
  Bewerten von Karussell-Slides, Reels, Captions, Hooks, Bild-Prompts oder
  Themen für diesen Account, auch wenn "@kiai1977" nicht ausdrücklich genannt
  wird, aber klar dieser Account gemeint ist. Spart das erneute Erklären von
  Ton, Jugendfreiheit, Vielfalt und Qualitätsregeln bei jeder Anfrage.
---

# @kiai1977 — Content-Haus-Regeln

Dieser Skill hält die festen Leitplanken für den Instagram-Account @kiai1977 fest, damit Ton, Stil und Qualität nicht bei jeder Anfrage neu erklärt werden müssen. Der Account macht nachdenklichen, warmen Gesellschafts-Content im Format **„Früher & Heute"** (Bild oben = früher / unten = heute), mit ehrlichem KI-Label.

Wenn der Workspace `instagram-system/` verfügbar ist, sind die maßgeblichen, jeweils aktuellsten Quellen:
- `instagram-system/vorlagen/content_richtlinien.json` — Ton, Tabus, persönliche Themen
- `instagram-system/vorlagen/redaktions_checkliste.md` — vollständige Prüf-Sequenz vor jeder Freigabe

Diese Dateien haben Vorrang, falls sie von dem hier Zusammengefassten abweichen. Lies sie, bevor du produzierst.

## Ton & Haltung

- Nett, freundlich, positiv, nachdenklich — **nicht** überspitzt, zynisch oder mit erhobenem Zeigefinger. Der Betrachter soll sich eingeladen fühlen, nicht beschuldigt.
- Nie „Kinder/Menschen heute sind schlecht" anklagen. Warm und wehmütig erzählen, mit **Einladung/Hoffnung** enden.
- Authentizität vor Floskel: Themen aus dem echten Erleben des Users bevorzugen (seine „früher war das schöner"-Erinnerungen), nicht beliebige KI-Massenware.
- Immer **„du"-Form**, nie „Sie" — auch in Captions. Hook-Eröffnungen variieren.

## Tabus (strikt FSK 0)

Keine Nacktheit/Sexualisierung, keine Gewalt, keine Politik/Religion/Reizthemen, keine Diskriminierung. Inhalte bleiben „oberhalb der Gürtellinie".

## Repräsentation

- Über eine Serie hinweg **ausgewogen**: männlich UND weiblich, jung UND alt, Kinder/Familien/Paare. Natürlich gemischt, nicht als Quote inszeniert — Bild-Prompts gezielt variieren.
- Deutscher/europäischer Kontext: dargestellte Personen im besten Fall **Europäer** (hellhäutig, mitteleuropäisch). In Bild-Prompts explizit „white European" / „fair-skinned European" angeben. Gilt für alle Slides.

## Qualität der Idee (wichtigster Hebel)

Die häufigste Schwäche war: 5 Vergleiche, die nur **dieselbe Aussage** umformulieren, und oben/unten **dasselbe Objekt**. Das vermeiden:

- **5 verschiedene Facetten** — jeder Vergleich ein anderer Aspekt/Situation/Objekt/Moment, niemals paraphrasiert.
  - Negativ (Thema Geschenke): 5× „war besonders".
  - Positiv: Vorfreude / ein Spielzeug lange bespielt / Dankesbrief / Auspack-Ritual / selbst gebastelt.
- **Echter Bild-Kontrast**: Früher-Szene und Heute-Szene zeigen **unterschiedliche** Objekte/Situationen, nicht zweimal dasselbe.
- **Konkret & sinnlich** statt Floskeln. Verboten: „war besonders", „verliert sich", „hat sich geändert".
- Szene muss zur Aussage passen (Verkehrsthema = zwei Autos; Zuhause-Themen daheim, nicht im Café).

## Bild-Prompt-Regeln (FLUX-Schwächen)

- **Hände**: freies FLUX patzt bei Händen. Vermeide offene Handflächen zur Kamera, extreme Hand-Nahaufnahmen, viele Hände dicht beieinander, gespreizte Finger. Stattdessen natürliche Framings: von hinten/seitlich, mit Abstand (ganze Figur), Hände ruhig an der Seite/in der Tasche/am Tisch. Genau **5 Finger**.
- **Ganze Figuren** — keine kopflosen/fragmentierten Körper. Gesichter natürlich sitzend.
- **Themen verwerfen**, bei denen jedes „Heute"-Bild ein extremes Hand-/Handgelenk-/Geräte-Close-up braucht (z. B. „Smartwatch als Fessel") — dort scheitert FLUX zuverlässig.
- Handy/Geräte: Display von der Kamera weg, von hinten gezeigt.
- Gesicht frei von Text halten; Umlaute korrekt.

## Prozess: erst Texte, dann Bilder

1. **Texte/Bauplan zuerst** generieren und dem User zur **Freigabe** zeigen (kostet kein Bildbudget).
2. Auf **5 distinkte Facetten + echten Kontrast** prüfen.
3. Erst nach Freigabe Bilder bauen.
4. **Redaktions-Checkliste C (Anatomie)** auf **jedes** Bild anwenden; durchfallende Bilder **einzeln** neu generieren.
5. Erst dann dem User das fertige Karussell zeigen.

Bei vorhandenem `instagram-system/`: vollständige Sequenz in `vorlagen/redaktions_checkliste.md` abarbeiten, bevor irgendetwas gezeigt wird.

## Caption-Standard

Fließtext + Ein-Wort-Frage → Leerzeile → „Folge @kiai1977 für mehr Reisen zwischen Früher & Heute." → „🤖 Bilder mit KI erstellt." → Hashtags.
