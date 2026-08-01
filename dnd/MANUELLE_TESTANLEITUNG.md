# D&D Companion – Manuelle Testanleitung

Diese Anleitung führt Sie durch alle Hauptfunktionen der D&D Companion App.

## Vorbereitung

1. **App öffnen**:
   - Lokal: http://localhost:8000/schulweg-nrw/dnd/
   - Live: https://lionelhutz77-tech.github.io/schulweg-nrw/dnd/

2. **Browser-Konsole öffnen** (F12):
   - Prüfen Sie auf Fehler
   - Beobachten Sie die Logs

3. **localStorage prüfen**:
   - Öffnen Sie DevTools → Application → localStorage
   - Suchen Sie nach `dnd_character`, `dnd_history`, etc.

---

## Test 1: Erste Charaktereinrichtung

**Szenario**: App startet und erstellt einen Standardcharakter

**Schritte**:
1. App öffnen
2. Dashboard sollte sichtbar sein
3. Name sollte leer oder "Charakter ohne Namen" sein
4. HP sollte 10/10 anzeigen

**Erfolg**: Dashboard zeigt Standardwerte

---

## Test 2: Charakterdaten bearbeiten

**Szenario**: Charaktername und Klasse ändern

**Schritte**:
1. Klick auf Charaktername oben im Dashboard
2. Namen eingeben: "Aragorn"
3. Klasse setzen: "Kampfmeister"
4. Speichern
5. Seite laden (F5)
6. Name sollte noch "Aragorn" sein

**Erfolg**: Änderungen persistent nach Reload

---

## Test 3: Schaden eintragen

**Szenario**: Charakter nimmt 15 Schaden

**Schritte**:
1. Im Dashboard auf [⚔ Schaden] klicken
2. "15" eingeben
3. OK klicken
4. HP sollte von 10/10 zu 0/10 (Rot) ändern
5. "Schaden 15 eingetragen!" sollte angezeigt werden

**Erfolg**: HP sind 0, Farbe ist rot

**Zusatztest**: Schaden mit Temp-HP
1. [🛡 Temp HP] klicken → "10" eingeben
2. [⚔ Schaden] klicken → "15" eingeben
3. HP sollten um 5 reduziert werden (15-10 Temp)
4. Temp-HP sollte 0 sein

**Erfolg**: Temp-HP werden vor regulären HP abgezogen

---

## Test 4: Heilung eintragen

**Szenario**: Charakter wird geheilt

**Schritte**:
1. HP sind 0/10
2. [❤ Heilung] klicken
3. "8" eingeben
4. OK klicken
5. HP sollten zu 8/10 ändern

**Zusatztest**: Überheilung verhindern
1. HP sind 8/10
2. [❤ Heilung] klicken
3. "50" eingeben
4. HP sollten auf 10/10 begrenzt sein (nicht 58)

**Erfolg**: Heilung funktioniert, max. HP werden nicht überschritten

---

## Test 5: Vollständige Heilung

**Szenario**: Charakter sofort auf volle HP heilen

**Schritte**:
1. HP sind 3/10
2. [✨ Vollständig] klicken
3. Bestätigungsdialog: "Vollständig heilen?"
4. [Ja, fortfahren] klicken
5. HP sollten zu 10/10 ändern

**Erfolg**: Dialog wird angezeigt, HP sind vollständig

---

## Test 6: Temporäre Trefferpunkte

**Szenario**: Charakter erhält Temp-HP von Schutzschild

**Schritte**:
1. [🛡 Temp HP] klicken
2. "15" eingeben
3. OK klicken
4. "Temporäre HP: 15" sollte unter der HP-Bar angezeigt werden
5. [⚔ Schaden] klicken → "20" eingeben
6. Temp-HP sollten 0 sein, reguläre HP sollten um 5 reduziert sein

**Erfolg**: Temp-HP werden zuerst verbraucht

---

## Test 7: Ressourcen-Management

**Szenario**: Überlegenheitswürfel verwenden

**Schritte**:
1. Im Ressourcen-Bereich "Überlegenheitswürfel" suchen
2. Sollte "0/0" anzeigen (da nicht konfiguriert)
3. [+] Button mehrmals klicken
4. Sollten auf max. begrenzt sein
5. [-] Button klicken
6. Sollten um 1 reduzieren

**Erfolg**: Ressourcen-Buttons funktionieren

---

## Test 8: Rast - Kurze Rast

**Szenario**: Kurze Rast (1 Stunde)

**Schritte**:
1. [🏕 K. Rast] klicken (oder in Favoriten)
2. Dialog: "Kurze Rast - Trefferwürfel werden wiederhergestellt"
3. [Bestätigung Rast durchführen] klicken
4. Dialog sollte schließen
5. "Kurze Rast abgeschlossen!" sollte angezeigt werden
6. Ressourcen sollten regeneriert sein

**Erfolg**: Kurze Rast-Dialog funktioniert

---

## Test 9: Rast - Lange Rast

**Szenario**: Lange Rast (8 Stunden)

**Schritte**:
1. HP auf 3/10 setzen ([⚔ Schaden] → 7)
2. [🛌 L. Rast] klicken
3. Dialog mit Warnung: "Zustände werden nicht entfernt"
4. [Bestätigung Rast durchführen] klicken
5. HP sollten zu 10/10 werden
6. "Lange Rast abgeschlossen!" sollte angezeigt werden

**Erfolg**: HP sind vollständig, Dialog funktioniert

---

## Test 10: Zustände (Placeholder-Test)

**Szenario**: Zustände-System überprüfen

**Schritte**:
1. Dashboard sollte "Aktive Zustände" Bereich zeigen (wenn leer, ist das OK)
2. Zustände-Button im Favoriten-Bereich sollte klickbar sein
3. Sollte zu "Zustände" Placeholder-View wechseln

**Erfolg**: Navigation zu Zustände-Bereich funktioniert

---

## Test 11: Änderungsverlauf und Undo

**Szenario**: Letzte Aktion rückgängig machen

**Schritte**:
1. [⚔ Schaden] → 10 eingeben
2. HP sollten reduziert sein
3. Im "Zuletzt:" Bereich sollte "Schaden 10 eingetragen!" stehen
4. [↶ Rückgängig] Button sollte sichtbar sein
5. [↶ Rückgängig] klicken
6. HP sollten wiederhergestellt sein
7. "Aktion rückgängig gemacht!" sollte angezeigt werden

**Erfolg**: Undo funktioniert vollständig

**Zusatztest**: Verlaufs-Ansicht
1. [📜 Verlauf] klicken
2. Sollte die letzten Aktionen anzeigen
3. Jeder Eintrag sollte Zeitstempel haben

**Erfolg**: Verlauf zeigt Transaktionen

---

## Test 12: Favoriten

**Szenario**: Schnellzugriffe verwenden

**Schritte**:
1. Favoriten-Buttons im unteren Bereich prüfen
2. Mindestens diese sollten vorhanden sein:
   - ⚔ Schaden
   - ❤ Heilung
   - 🛡 Temp HP
   - ⚗ Heiltrank
   - 🗡 Manöver
   - 😵 Zustände
   - 🎒 Inventar
   - 🏕 K. Rast
   - 🛌 L. Rast
   - 📜 Verlauf
3. Jeder Button sollte klickbar sein

**Erfolg**: Alle Favoriten-Buttons existieren und sind funktionsfähig

---

## Test 13: Navigation

**Szenario**: Zwischen Views navigieren

**Schritte**:
1. Unten sollte eine Navigationsleiste sein mit:
   - 📊 Dashboard
   - ⚔ Kampf
   - ✨ Zauber
   - 🎒 Inventar
   - 📝 Notizen
   - ⚙ Mehr
2. Klick auf jeden Tab
3. Dashboard sollte aktiv sein (hervorgehoben)
4. Andere Tabs sollten Placeholder-Views zeigen
5. [Dashboard] sollte Dashboard-Sicht wiederherstellen

**Erfolg**: Navigation funktioniert

---

## Test 14: Export

**Szenario**: Charakter exportieren

**Schritte**:
1. Ein paar Aktionen durchführen (Schaden, Heilung)
2. [⚙ Mehr] → Einstellungen
3. [📥 Charakter exportieren] klicken
4. JSON-Datei sollte heruntergeladen werden
5. Dateiname sollte Pattern: `dnd_character_[Name]_[Datum].json` sein
6. Datei öffnen und prüfen:
   - `appVersion: "1.0.0"`
   - `schemaVersion: 1`
   - `character` Objekt vorhanden
   - `history` Array vorhanden

**Erfolg**: Export-Datei ist strukturiert und beinhaltet Daten

---

## Test 15: Import

**Szenario**: Zuvor exportierte Datei reimportieren

**Schritte**:
1. Name ändern in "TestChar Import"
2. HP auf 5 setzen
3. Schaden eintragen
4. [⚙ Mehr] → Einstellungen
5. [📤 Charakter importieren] klicken
6. Zuvor exportierte JSON-Datei auswählen
7. Dialog: "Charakter importieren? - Bestehenden Charakter überschreiben?"
8. [Ja, importieren] klicken
9. Name sollte auf exportierten Namen zurückgehen
10. HP sollten wie exportiert sein

**Erfolg**: Import funktioniert und überschreibt aktuellen Charakter

---

## Test 16: Offline-Betrieb

**Szenario**: App funktioniert auch ohne Netzwerk

**Schritte**:
1. App normal öffnen
2. Browser-Entwickler-Tools → Application → Service Workers
3. Service Worker sollte registriert sein
4. Internet ausschalten (DevTools → Network → Offline)
5. Seite neuladen (F5)
6. App sollte weiterhin laden
7. Alle Funktionen sollten funktionieren
8. Daten sollten noch vorhanden sein

**Erfolg**: App funktioniert offline

---

## Test 17: Responsive Design - iPad

**Szenario**: App auf iPad testen

**Schritte**:
1. DevTools → Device: iPad
2. Dashboard sollte vollständig ohne Scroll sichtbar sein (außer Navigation)
3. Alle Buttons sollten mind. 44×44px sein
4. Text sollte lesbar sein
5. Portrait und Landscape testen

**Erfolg**: Layout passt sich an, Touch-Targets sind groß genug

---

## Test 18: Deutsch-Überprüfung

**Szenario**: Alle Texte sind auf Deutsch

**Schritte**:
1. Alle sichtbaren Schaltflächen prüfen:
   - Dashboard: ✓
   - Schaden: ✓
   - Heilung: ✓
   - Vollständig: ✓
   - Rückgängig: ✓
   - etc.
2. Keine englischen Begriffe sollten sichtbar sein
3. Dialog-Titel sollten Deutsch sein
4. Meldungen sollten Deutsch sein

**Erfolg**: Vollständig deutschsprachige UI

---

## Test 19: localStorage-Isolation

**Szenario**: Lern-App und D&D-App nutzen getrennte Speicher

**Schritte**:
1. DevTools → Application → localStorage
2. Folgende Keys sollten existieren:
   - `dnd_character`
   - `dnd_history`
   - `dnd_favorites`
   - `dnd_settings`
3. Keys mit `schulweg_*` Präfix sollten NICHT existieren
4. Lern-App öffnen (http://localhost:8000)
5. localStorage sollte `schulweg_profile` etc. haben
6. Zurück zu D&D-App
7. `dnd_*` Keys sollten NICHT verändert sein

**Erfolg**: Namespace-Isolation funktioniert

---

## Test 20: Keine Konsolen-Fehler

**Szenario**: Keine JavaScript-Fehler in der Konsole

**Schritte**:
1. DevTools → Console
2. Alle Tests durchlaufen
3. Keine roten Fehler sollten angezeigt werden
4. Nur Info-Logs sind OK

**Erfolg**: Console ist fehlerfrei

---

## Zusammenfassung

Wenn alle 20 Tests bestanden haben:

✅ Dashboard funktioniert  
✅ HP-Management ist vollständig  
✅ Ressourcen-System funktioniert  
✅ Rast-Funktionalität  
✅ Undo-System  
✅ Export/Import  
✅ Offline-Betrieb  
✅ Responsive Design  
✅ Deutschsprachige UI  
✅ Isolation von Lern-App  
✅ Keine Fehler  

**Status: BEREIT FÜR RELEASE 1.0**

---

## Fehlerbehandlung

**Falls Tests fehlschlagen**:

1. **Browser-Konsole prüfen**: F12 → Console auf Fehler
2. **localStorage löschen**: DevTools → Application → Clear All
3. **Service Worker löschen**: DevTools → Application → Service Workers → Unregister
4. **Seite hart laden**: Ctrl+Shift+R oder Cmd+Shift+R
5. **Andere Browser testen**: Chrome, Firefox, Safari

---

**Erstellt**: 2026-07-31  
**Version**: 1.0 Release Candidate
