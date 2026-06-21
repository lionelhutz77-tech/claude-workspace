# 🚀 Immobilien-Scanner Setup (Phase 3)

## Schritt 1: Python Dependencies

```bash
pip install -r requirements.txt
python -m playwright install chromium
```

Dauert ~5 Minuten beim ersten Mal (Chrome-Browser wird heruntergeladen).

---

## Schritt 2: Secrets bereitstellen

### 2.1 .env erstellen

```bash
cp .env.example .env
```

### 2.2 GMx App-Passwort

⚠️ **WICHTIG:** Das ist NICHT dein normales GMx-Passwort!

1. Gehe zu https://www.gmx.de/app-passwort
2. Melde dich an
3. **Generiere neues App-Passwort** (z.B. "Immobilien Scanner")
4. Kopiere das Passwort

Dann in `.env` eintragen:
```env
GMX_USER=hutz.erkan@gmx.de
GMX_APP_PASSWORD=<HIER EINTRAGEN - z.B. abcd1234efgh5678>
```

### 2.3 Groq API-Key

1. Gehe zu https://console.groq.com
2. Melde dich an (oder registriere dich)
3. **API Keys** → **Create New Key**
4. Kopiere den Key

Dann in `.env`:
```env
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxx
```

---

## Schritt 3: Setup validieren

```bash
python setup_test.py
```

Output sollte sein:
```
✅ Python 3.x
✅ pyyaml
✅ python-dotenv
✅ groq
✅ requests
✅ beautifulsoup4
✅ playwright
✅ config.yaml geladen
✅ E-Mail-Adresse korrekt
✅ .env Secrets vorhanden
✅ Groq-API erreichbar

✅ SETUP OK — Ready to run: python main.py
```

Falls Fehler: Siehe Fehlermeldung und behebe sie.

---

## Schritt 4: Ersten Scan testen

```bash
python main.py
```

**Das erste Mal dauert länger** (Browser-Starts, Playwrights initialisiert).

Expected Output:
```
============================================================
🚀 IMMOBILIEN-SCANNER GESTARTET
============================================================

📋 Config geladen: 46149 Oberhausen
🔄 Scraping aller Quellen...
▶️  ImmoScout24 lädt...
✅ ImmoScout24: 12 Props
▶️  Immonet lädt...
✅ Immonet: 8 Props
...
✅ Gesamt nach Duplikat-Filter: 18 Immobilien gefunden
🧹 Daten bereinigen...
✅ 18/18 gültig
🤖 Groq-Evaluierung lädt...
✅ 18 Props evaluiert
📊 Nach Filterung: 5/18 empfohlenswert
📧 Report wird vorbereitet...
✅ Mail versendet an hutz.erkan@gmx.de
💾 Daten archiviert: data/scan_20260621_120000.json

============================================================
✅ PIPELINE ABGESCHLOSSEN
============================================================
```

**Mail Check:** Öffne dein GMx-Postfach → Sollte Report-Mail angekommen sein

---

## Schritt 5: Logs anschauen

```bash
cat immobilien_scanner.log
```

Zeigt detaillierte Infos über jeden Scraper, Fehler, etc.

---

## Schritt 6: Daten archiviert?

```bash
ls -la data/
```

Sollte ein `scan_YYYYMMDD_HHMMSS.json` enthalten mit allen evaluierten Immobilien.

---

## Phase 4: GitHub Actions (Automatisch wöchentlich)

Wenn lokal alles klappt, GitHub Actions setup:

```bash
# Secrets in GitHub hinzufügen:
# Settings → Secrets and variables → Actions
# GMX_USER=hutz.erkan@gmx.de
# GMX_APP_PASSWORD=<App-Passwort>
# GROQ_API_KEY=<API-Key>
```

Dann `.github/workflows/weekly_scan.yml` erstellen (siehe README.md).

---

## 🆘 Troubleshooting

### ❌ "playwright not found"
```bash
python -m playwright install chromium
```

### ❌ "No module named 'groq'"
```bash
pip install groq>=0.4.0
```

### ❌ "Groq API Key invalid"
- Prüfe `.env` auf Tippfehler
- API-Key sollte mit `gsk_` starten
- Neuen Key von https://console.groq.com erstellen

### ❌ "Mail nicht angekommen"
- Überprüfe `.env` — GMX_APP_PASSWORT korrekt?
- Mail landete evtl. im Spam/Junk → prüfen
- Logs anschauen: `tail immobilien_scanner.log`

### ❌ "Scraper bringt nichts"
- Websites könnten sich geändert haben (HTML-Struktur)
- Logs anschauen für Parse-Fehler
- Manuell ImmoScout24 checken: Gibt es Angebote für 46149?

### ❌ "Timeout beim Scraping"
- Netzwerk zu langsam?
- Websites überlastet?
- Delays in `config.yaml` erhöhen (5–10 Sekunden)

---

## ✅ Nächste Schritte

- ✅ Phase 3 (Setup) abgeschlossen
- Dann Phase 4: GitHub Actions für wöchentliche Automation
- Später Phase 5: VON POLL + atelier rheinruhr Scraper

---

**Fragen?** Siehe `CLAUDE.md` oder Logs.
