# 🧪 TEST-ANLEITUNG: ULTRA-PRO System

## **SCHRITT 1: Setup Validieren (5 Minuten)**

```bash
cd immobilien-scanner
python setup_test.py
```

**Erwartet:**
```
✅ Python 3.x
✅ pyyaml
✅ python-dotenv
✅ groq
✅ requests
✅ beautifulsoup4
✅ playwright
✅ config.yaml geladen
✅ .env Secrets vorhanden
✅ Groq-API erreichbar

✅ SETUP OK
```

**Falls Fehler:**
- `pip install -r requirements.txt`
- `python -m playwright install chromium`
- `.env` überprüfen (GMX_USER, GMX_APP_PASSWORD, GROQ_API_KEY)

---

## **SCHRITT 2: Erste Scan (10-30 Minuten je nach Internet)**

```bash
python main.py
```

**Was passiert:**
1. Config laden (0,5s)
2. **13 Quellen scrapen parallel** (5-15 Min):
   - ImmoScout24, Immonet, Sparkasse, Volksbank (JS-Rendering = langsam)
   - KL, Sariguel, Piezonka, Immo-OB, Marquardt, Blömker, van Oepen, Bönighausen (HTML = schnell)
3. Daten bereinigen (1s)
4. **Groq Evaluierung** (2-3 Min):
   - Mietpotenzial-Analyse
   - ESG/Energieeffizienz
   - Lage-Scoring
   - Finanzierungs-Stress-Test
5. Mail vorbereiten (1s)
6. Mail versenden (2s)
7. Daten archivieren (1s)

**Logs anschauen:**
```bash
tail -f immobilien_scanner.log
```

**Erwartet Output:**
```
============================================================
🚀 IMMOBILIEN-SCANNER GESTARTET
============================================================

📋 Config geladen: 46149 Oberhausen
🔄 Scraping aller Quellen...
▶️  ImmoScout24 lädt...
✅ ImmoScout24: 15 Props
▶️  Immonet lädt...
✅ Immonet: 12 Props
▶️  Sparkasse lädt...
✅ Sparkasse: 8 Props
▶️  Volksbank lädt...
✅ Volksbank: 6 Props
▶️  KL Immobilien lädt...
✅ KL Immobilien: 3 Props
▶️  Blömker lädt...
✅ Blömker: 4 Props
▶️  van Oepen lädt...
✅ van Oepen: 2 Props
▶️  Bönighausen lädt...
✅ Bönighausen: 5 Props
...

✅ Gesamt nach Duplikat-Filter: 65 Immobilien gefunden
🧹 Daten bereinigen...
✅ 65/65 gültig
🤖 Groq ULTRA-PRO Evaluierung (Phase 1+2)...
✅ 65 Props mit Mietpotenzial + ESG + Lage + Stress-Test evaluiert
📊 Nach Filterung: 28/65 empfehlenswert (PROFIT: 18, FAMILY: 10)
📧 Report wird vorbereitet...
✅ Mail versendet an hutz.erkan@gmx.de
💾 Daten archiviert: data/scan_20260622_150000.json

============================================================
✅ PIPELINE ABGESCHLOSSEN
============================================================
```

---

## **SCHRITT 3: Ergebnisse Checken**

### **3a: Mail überprüfen**
- GMx-Postfach öffnen
- Mail vom Immobilien-Scanner sollte da sein
- Subject: `[Immobilien-Scanner] Wöchentlicher Report 22.06.2026`
- **Zwei Tabellen:**
  - 🏢 **KATEGORIE 1: PROFIT** (6%+ Rendite, ganz Oberhausen)
  - 👨‍👩‍👧‍👦 **KATEGORIE 2: FAMILY** (0%+, PLZ 46149, für Eltern)

### **3b: Lokal-Daten überprüfen**
```bash
ls -la data/
```

→ `scan_20260622_HHMMSS.json` sollte da sein

```bash
cat data/scan_*.json | head -100
```

→ JSON mit allen evaluierten Props (Mietpotenzial, ESG, Lage-Score, etc.)

### **3c: Logs überprüfen**
```bash
cat immobilien_scanner.log | tail -50
```

→ Detaillierte Logs von jedem Scraper + Groq

---

## **EXPECTED RESULTS (Erstes Mal)**

| Metrik | Expected Range | Bedeutung |
|--------|---|---|
| Props gefunden | 40-80 | Abhängig von Marktangebot |
| Duplikate | 5-15% | Normal (Makler multiply listings) |
| PROFIT qualifiziert | 30-50% | 6%+ Rendite ist streng |
| FAMILY qualifiziert | 20-40% | 46149 zentral, unter Limit |
| Top PROFIT Score | 70-90 | Sehr gutes Angebot |
| Top FAMILY Score | 60-80 | Geeignet für Familie |

---

## **HÄUFIGE FEHLER + FIXES**

### ❌ "playwright not found"
```bash
python -m playwright install chromium
```

### ❌ "No module named 'groq'"
```bash
pip install groq>=0.4.0
```

### ❌ "Groq API Key invalid"
- `.env` überprüfen → GMX_USER + GMX_APP_PASSWORD + GROQ_API_KEY
- API-Key sollte mit `gsk_` starten
- Neuen Key von https://console.groq.com generieren

### ❌ "Mail nicht angekommen"
- Logs anschauen: `grep "Mail" immobilien_scanner.log`
- `.env`: GMX_APP_PASSWORD korrekt? (nicht Main-Passwort!)
- Gmail/GMx Spam-Folder checken

### ❌ "Keine Props gefunden"
- Scraper timeout? → Logs anschauen
- Netzwerk ok? → `ping google.com`
- Websites erreichbar? → Browser öffnen + manuell checken

### ❌ "Groq Error: Rate limit exceeded"
- Warten 1 Minute + erneut starten
- Oder Props in kleineren Batches evaluieren

---

## **WENN ALLES OK IST**

✅ Scanner läuft  
✅ Mail kommt an  
✅ PROFIT + FAMILY Props sind gelistet  

**Dann:** Gib mir Bescheid, welche Verbesserungen wir noch einbauen!

---

## **WENN FEHLER AUFTAUCHEN**

**Poste mir:**
1. Der Fehler-Output (komplett, mit Stack Trace)
2. Relevante Logs (letzten 50 Zeilen)
3. Was genau fehlgeschlagen ist

→ Dann fixen wir es iterativ!

---

## **NACH DEM TEST: Optimization-Cycle**

1. **Probleme identifizieren** (welche Scraper zu langsam? Welche Props falsch bewertet?)
2. **Fixes bauen** (Scraper optimieren, Groq-Prompt verfeinern, etc.)
3. **Re-test** (erneut laufen lassen)
4. **Loop bis alles perfekt**

Das ist der **iterative Build-Prozess für Production-Ready Software**!

---

**Du bist ready. Los geht's!** 🚀
