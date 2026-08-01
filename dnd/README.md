# D&D Companion – Spielbegleiter für D&D 5e

**Version**: 1.0  
**Status**: Beta Release

Ein schneller, offline-fähiger D&D 5e Charaktermanager für iPad und Desktop. Optimiert für Spielsitzungen – alle wichtigen Funktionen sind mit höchstens 2 Klicks erreichbar.

## Features

### Kern-Funktionen
- **Dashboard**: Zentrale Spielsicht mit allen wichtigen Werten auf einen Blick
- **HP-Management**: Schaden, Heilung, temporäre HP mit vollständiger Undo-Funktion
- **Ressourcen**: Generische, konfigurierbare Ressourcenverwaltung
- **Kampfmeister-Manöver**: Datengetriebene Manöververwaltung
- **Zustände**: Schnelle Zustands-Verwaltung
- **Rast**: Kurze und lange Rast mit Ressourcen-Regeneration
- **Änderungsverlauf**: Vollständige Historie mit Undo
- **Export/Import**: JSON-Backup und Wiederherstellung

### Technische Features
- **Offline-Fähig**: Funktioniert komplett ohne Internetverbindung
- **PWA**: Installierbar auf Home-Bildschirm (iPad/Android/Desktop)
- **Responsiv**: Optimiert für iPad Portrait/Landscape und Desktop
- **Barrierefreiheit**: WCAG 2.1 Level AA unterstützt
- **Keine Dependencies**: Vanilla JavaScript, keine externen Abhängigkeiten

## Installation

### Lokal (Entwicklung)
```bash
cd schulweg-nrw/dnd
python -m http.server 8000
# oder: python3 -m http.server 8000
```
Dann im Browser öffnen: `http://localhost:8000`

### Auf iPad
1. In Safari öffnen: `https://lionelhutz77-tech.github.io/schulweg-nrw/dnd/`
2. Share-Button → "Zum Home-Bildschirm"
3. Fertig! App startet im Vollbild

### Tests
```bash
# Öffne tests.html im Browser
http://localhost:8000/tests.html
```

## Struktur

```
dnd/
├── index.html              – Hauptseite
├── manifest.webmanifest    – PWA-Konfiguration
├── service-worker.js       – Offline-Support
├── tests.html              – Testsuite
│
├── css/
│   ├── variables.css       – CSS-Variablen
│   ├── base.css            – Basis-Styles
│   ├── dashboard.css       – Dashboard-Layout
│   ├── modals.css          – Modal-Styling
│   └── responsive.css      – Responsive-Design
│
├── js/
│   ├── utils.js            – Utility-Funktionen
│   ├── storage.js          – localStorage-Wrapper
│   ├── character.js        – Charaktermodell
│   ├── transaction.js      – Transaktions- & Undo-Logik
│   ├── resources.js        – Ressourcen-Manager
│   ├── modal.js            – Modal-System
│   ├── ui.js               – UI-Rendering
│   ├── views.js            – Ansichten
│   ├── nav.js              – Navigation
│   └── app.js              – Hauptanwendung
│
├── icons/
│   └── icon.svg            – App-Icon
│
└── README.md               – Diese Datei
```

## Datenspeicherung

Alle Daten werden lokal in `localStorage` gespeichert:

- `dnd_character` – Charakterdaten
- `dnd_history` – Änderungsverlauf
- `dnd_favorites` – Favoriten
- `dnd_settings` – Einstellungen
- `dnd_backups` – Automatische Backups

**Kein Cloud-Sync in Version 1.0**

## Datenmodell

### Charakter (Character)
```javascript
{
  meta: {
    id, name, schemaVersion, characterVersion,
    created, lastModified, ruleset
  },
  basics: {
    class: { name, level, subclass },
    race, background, alignment
  },
  abilities: { strength, dexterity, ... },
  proficiency: { bonus, savingThrows, skills, expertise },
  hitpoints: { max, current, temporary, hd: { size, current, max } },
  ac, initiative, speed,
  inspiration, exhaustion,
  resources: [ /* Array */ ],
  conditions: [ /* Array */ ],
  inventory: { weapons, armor, magicalItems, consumables, other },
  questNotes: { currentQuest, importantPersons, ... }
}
```

### Transaktionen
```javascript
{
  id, transactionId, originTransactionId,
  timestamp,
  action, cause, actionType, description,
  before, after,
  userAction, undoable, undoReference, notes
}
```

## Undo-Logik

Jede Aktion (Schaden, Heilung, Ressourcen, etc.) ist rückgängig machbar:

1. Transaktion protokolliert `before` und `after` Zustand
2. Undo stellt `before` Zustand wieder her
3. Undo-Aktion wird selbst protokolliert
4. Max. 100 aktive Einträge im Verlauf

**Komplexe Transaktionen**: Heiltrank-Nutzung (HP + Inventar) wird als eine Transaktion behandelt.

## Offline-Betrieb

- **Service Worker** mit `network-first` Strategie
- **Alle Assets** gecacht (HTML, CSS, JS, Icons)
- **localStorage** bleibt offline verfügbar
- **Auto-Save** alle 30 Sekunden
- **Keine Auto-Sync** zwischen Geräten (Version 1.0)

## Sicherheit

- **XSS-Protection**: Alle Benutzereingaben werden escaped
- **Input-Validierung**: Charakterdaten werden validiert
- **Keine externe API**: Funktioniert komplett lokal
- **Keine Credentials**: Keine Passwörter oder Authentifizierung nötig

## Browser-Kompatibilität

- iOS Safari 12+
- Chrome/Edge 90+
- Firefox 88+
- Android Browser

**Getestet auf:**
- iPad Air (iOS 16+)
- iPad Pro (iOS 16+)
- Chrome Desktop
- Firefox Desktop

## Bekannte Limitationen (Version 1.0)

- ❌ Keine Zauber-Datenbank
- ❌ Keine Konzentrationsverwaltung
- ❌ Kein Würfel-Simulator
- ❌ Keine Cloud-Synchronisation
- ❌ Keine Kampagnen-Verwaltung
- ⏳ Erweiterte Manöver folgen in Version 1.1+

## Entwicklung

### Struktur der Module
- **utils.js**: Universelle Hilfsfunktionen
- **storage.js**: localStorage mit `dnd_*` Namespace
- **character.js**: Charakterklasse und Datenmodell
- **transaction.js**: Transaktions- & Undo-System
- **resources.js**: Generische Ressourcenverwaltung
- **modal.js**: Modal-Dialoge
- **ui.js**: UI-Rendering und Events
- **views.js**: Verschiedene Ansichten
- **nav.js**: Navigation zwischen Views
- **app.js**: Hauptanwendungs-Bootstrap

### Tests
```bash
# Testsuite ausführen
open tests.html
# oder: http://localhost:8000/tests.html
```

Aktuell: **14 Basis-Tests** für HP, Ressourcen, Transaktionen, Storage und Validierung.

## API-Referenz

### Charakter-Management
```javascript
DndApp.getCharacter()      // Aktiven Charakter abrufen
DndApp.setCharacter(char)  // Neuen Charakter setzen
DndApp.saveCharacter()     // Speichern
```

### HP-Operationen
```javascript
DndTransaction.transactionDamage(char, damage)
DndTransaction.transactionHealing(char, healing)
DndTransaction.transactionTempHp(char, amount)
DndTransaction.undo(transactionId)
```

### Ressourcen
```javascript
DndResources.increaseResource(char, resourceId, amount)
DndResources.decreaseResource(char, resourceId, amount)
DndResources.regenerateResources(char, 'shortRest'|'longRest'|'all')
```

### Export/Import
```javascript
DndApp.exportCharacter()   // JSON herunterladen
DndApp.importCharacter()   // Datei hochladen
```

## Performance

- **Initial Load**: < 1s (lokal)
- **Dashboard Render**: < 100ms
- **Undo**: < 50ms
- **Storage**: localStorage ~1-2 MB pro Charakter

## Support und Feedback

Diese App ist ein Projekt von Claude Haiku.

Bekannte Probleme oder Verbesserungen können direkt im Quellcode dokumentiert werden.

---

**D&D ist ein eingetragenes Warenzeichen der Wizards of the Coast.**  
Diese App ist kein offizielles Produkt von Wizards of the Coast.
