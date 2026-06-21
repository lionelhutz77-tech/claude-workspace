# 🏘️ Immobilien-Scanner für Oberhausen

Automatisierter Scanner, der wöchentlich Immobilien in Oberhausen (46149) analysiert und nach **Rendite-Kriterien** bewertet.

## Features

✅ **Multi-Source-Scraping**: ImmoScout24, Immonet, Sparkasse, Volksbank, KL Immobilien, VON POLL, atelier rheinruhr  
✅ **Groq-AI-Evaluierung**: Automatische Rendite-, Cashflow- und Risiko-Bewertung  
✅ **HTML-Report mit Ranking**: Top 10 nach Score sortiert  
✅ **Automatische GMx-Mail**: Jede Woche Sonntag 12:00 Uhr  
✅ **Daten-Archivierung**: JSON pro Scan für historische Analyse  

## Setup

### 1. Abhängigkeiten installieren

```bash
pip install -r requirements.txt
python -m playwright install chromium
```

### 2. Umgebungsvariablen

Kopiere `.env.example` zu `.env` und trage ein:

```bash
cp .env.example .env
```

Dann in `.env` editieren:

```env
GMX_USER=hutz.erkan@gmx.de
GMX_APP_PASSWORD=your_app_password_here
GROQ_API_KEY=gsk_xxxxxxxxxxxxx
```

**Wichtig:** 
- GMx App-Passwort erstellen unter https://www.gmx.de/app-passwort
- Groq API-Key kostenlos von https://console.groq.com

### 3. Config überprüfen

In `config.yaml`:
- `to_email` sollte `hertz.r.kanal@gmx.de` sein (bitte überprüfen!)
- Schwellwerte nach Bedarf anpassen

## Nutzung

### Manuell testen

```bash
python main.py
```

Logs werden in `immobilien_scanner.log` geschrieben.

### Wöchentlich automatisieren (GitHub Actions)

Datei `.github/workflows/weekly_scan.yml` (noch zu erstellen):

```yaml
name: Weekly Immobilien Scan
on:
  schedule:
    - cron: '0 12 * * 0'  # Sonntag 12:00 UTC

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: 3.11
      - run: pip install -r requirements.txt && python -m playwright install chromium
      - run: python main.py
        env:
          GMX_USER: ${{ secrets.GMX_USER }}
          GMX_APP_PASSWORD: ${{ secrets.GMX_APP_PASSWORD }}
          GROQ_API_KEY: ${{ secrets.GROQ_API_KEY }}
```

Secrets in GitHub hinzufügen: Settings → Secrets and variables → Actions

## TODO (Phase 2)

- [ ] Scraper für ImmoScout24 implementieren
- [ ] Scraper für Immonet implementieren
- [ ] Scraper für Sparkasse implementieren
- [ ] Scraper für Volksbank implementieren
- [ ] Scraper für KL Immobilien implementieren
- [ ] Scraper für VON POLL implementieren
- [ ] Scraper für atelier rheinruhr implementieren
- [ ] Groq-Integration testen
- [ ] Mail-Integration testen
- [ ] GitHub Actions Setup
- [ ] Daten-Historisierung erweitern

## Struktur

```
immobilien-scanner/
├── main.py              # Orchestration
├── evaluator.py         # Groq-Integration
├── mailer.py            # GMx Mail-Versand
├── scrapers/
│   ├── __init__.py
│   ├── immoscout.py
│   ├── immonet.py
│   ├── sparkasse.py
│   ├── volksbank.py
│   ├── kl_immobilien.py
│   ├── von_poll.py
│   └── arr_immobilien.py
├── data/                # Archiv (JSONs)
├── config.yaml          # Konfiguration
├── .env.example         # Secrets-Template
├── requirements.txt     # Dependencies
└── .github/
    └── workflows/
        └── weekly_scan.yml  # GitHub Actions
```

## Bewertungs-Logik (Groq)

Für jede Immobilie:
1. **Cashflow** = (Kaltmiete × Wohnungen) - (Verwaltung + Instandhaltung + Versicherung + Leerstand)
2. **Finanzierungsbedarf** = Kaufpreis × (1 - LTV%)
3. **Kreditrate monatlich** = Finanzierungsbedarf / 360 × (Zinssatz + Tilgung)%
4. **Netto-Cashflow** = Cashflow - Kreditrate
5. **Rendite** = (Netto-Cashflow × 12 / Eigenkapital) × 100%

**Rote Flaggen:**
- Baujahr < 1950 → feuchte Keller wahrscheinlich
- Renovierungskosten > 50k€ → AUSSCHLUSS
- Netto-Cashflow < 500€ → AUSSCHLUSS

**Score (0-100):**
- 80+: Sehr gut
- 60-80: Gut
- 40-60: Prüfen
- <40: Nicht empfohlen

## Kontakt

Fragen? Siehe `CLAUDE.md` oder kontaktiere den Owner.

---

**Haftungsausschluss:** Diese Analyse ist automatisiert und ersetzt keine fachliche Beratung. Vor jedem Immobilienkauf sollten Experten (Makler, Bankberater, Gutachter) konsultiert werden.
