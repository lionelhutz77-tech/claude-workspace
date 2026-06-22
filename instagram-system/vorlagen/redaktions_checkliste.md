# 🔍 REDAKTIONS-CHECKLISTE @kiai1977
Claude arbeitet diese Sequenz bei JEDEM Karussell ab — erst Prompts, dann jedes Bild —
BEVOR dem User etwas gezeigt wird. Quelle: gesammelte User-Kritik (Stand 2026-06-17).

## A) PROMPT-REGELN (vor dem Generieren — Fehler von vornherein vermeiden)
- [ ] KEINE extremen Hand-/Handgelenk-/Geräte-Close-ups (FLUX-Schwäche)
- [ ] Handy-Szenen: von HINTEN über die Schulter, Display zeigt von der Kamera WEG
      (die Person schaut aufs Display — wir sehen es nicht frontal)
- [ ] GANZE Figuren / weiter gefasst — keine angeschnittenen oder kopflosen Körper
- [ ] Hände natürlich: an der Seite, in der Tasche, ruhend — KEINE offenen Handflächen
      zur Kamera, keine weit gespreizten Finger
- [ ] Szene MUSS zur Aussage passen: Verkehr = zwei Autos; europäisch = Linkslenker;
      "Zuhause"-Momente daheim (nicht Café); Thema und Bild stimmen überein
- [ ] Realistische Details: Wasser/Kaffee statt Bier; passende Gegenstände
- [ ] Anatomie-Vorgabe steht im Prompt (5 Finger, natürliche Haltung) — automatisch

## B) INHALT & TEXT (Logik prüfen)
- [ ] 5 VERSCHIEDENE Facetten — niemals 5x dieselbe Aussage umformuliert
- [ ] Echter Kontrast: Früher-Bild und Heute-Bild zeigen UNTERSCHIEDLICHE Objekte/Szenen
- [ ] Konkret & sinnlich, keine Floskeln ("war besonders", "verliert sich")
- [ ] Durchgängig "du", nie "Sie"
- [ ] Korrekte Umlaute (ä ö ü ß), keine Tippfehler
- [ ] Hook-Eröffnung variiert; Caption + CTA in einheitlicher Struktur

## C) BILD-PRÜFUNG (nach dem Generieren — JEDES Bild einzeln durchgehen)
- [ ] HÄNDE: genau 5 Finger, natürlich gehalten? (häufigster Fehler!)
- [ ] KÖRPER vollständig: kein dritter Arm, kein fehlender Kopf, keine Fragmente,
      keine zwei Körper mit nur einem Kopf?
- [ ] HALTUNG/Geste natürlich — nichts verdreht/verrenkt (kein Unfall-Look)?
- [ ] Keine DOPPELTEN Objekte (zwei Zifferblätter, zwei Stifte)?
- [ ] HANDY-Display logisch (zeigt von der Kamera weg)?
- [ ] GESICHT nicht vom Text verdeckt? Text im Rahmen? Fußzeile frei?
- [ ] Keine zufälligen/störenden HINTERGRUND-Objekte (z.B. Wolf-Bild im Café)?
- [ ] Nase/Gesicht korrekt, nicht verzerrt?

REGEL: Jedes Bild, das in C durchfällt, wird EINZELN neu generiert (mit angepasstem,
komposition-bewusstem Prompt aus A) — erst danach dem User vorlegen.
Themen, bei denen jedes Heute-Bild ein Hand-/Geräte-Close-up erzwingt, gar nicht erst
wählen (siehe content_richtlinien.json "themen_vermeiden").
