# Immobilien-Scanner (Oberhausen)

Automatisierter Immobilien-Finder für die Region Oberhausen (46149).

## Goal

Wöchentlich (Sonntag 12:00) Immobilien in Oberhausen durchsuchen, nach **Rendite- und Risiko-Kriterien** bewerten und eine Mail mit Top 10 versenden.

## Kriterien

**Suche:**
- PLZ 46149 (Oberhausen)
- Min. 2 Wohnungen (Mehrfamilienhaus)
- Kaufpreis 100k–750k€

**Rendite:**
- Angenommene Kaltmiete: 950€/Einheit
- Nebenkosten zahlt Mieter
- Verwaltung (~10%), Instandhaltung (~1.50€/m²), Versicherung (~40€), Leerstand (~3%)
- Min. Cashflow: 500€/Monat (netto nach Kreditrate)
- Min. Rendite: 5% p.a.

**Risiken:**
- Baujahr vor 1950 → feuchte Keller-Indikation
- Renovierungskosten > 50k€ → AUSSCHLUSS
- Netto-Cashflow < 500€ → AUSSCHLUSS

**Features (positiv):**
- Garten, Balkon, Garage
- Renovierungen bereits durchgeführt
- Neue Heizung/Fenster

## Tech Stack

- **Scraping**: Selenium/Playwright (JS-Rendering) + BeautifulSoup (HTML-Parsing)
- **AI-Evaluierung**: Groq API (kostenlos) — llama-3.3-70b
- **Mail**: GMx SMTP (App-Passwort)
- **Automation**: GitHub Actions (wöchentlich Sonntag 12:00)
- **Archiv**: JSON pro Scan in `data/`

## Quellen

1. ImmoScout24
2. Immonet
3. Sparkasse Immobilien
4. Volksbank Rhein-Ruhr
5. KL Immobilien
6. VON POLL IMMOBILIEN
7. atelier rheinruhr

## Workflow

```
main.py
  ├─ load_config() → config.yaml
  ├─ scrape_all_sources() → raw data
  ├─ clean_data() → validated
  ├─ evaluate_properties() → Groq-API (rendite, risiken, score)
  ├─ filter() → nur schwellwerte erfüllt
  ├─ send_report() → HTML-Mail via GMx
  └─ archive() → JSON in data/
```

## Setup

```bash
pip install -r requirements.txt
python -m playwright install chromium
cp .env.example .env
# Editiere .env: GMX_USER, GMX_APP_PASSWORD, GROQ_API_KEY
python main.py
```

## Phase-Roadmap

**Phase 1 (jetzt)**: Architektur + Core-Modules  
**Phase 2**: Scraper implementieren (ImmoScout, Immonet, Sparkasse, Volksbank, KL, VON POLL, ARR)  
**Phase 3**: Groq-Integration + Mail-Testing  
**Phase 4**: GitHub Actions Setup + Produktion  
**Phase 5**: Daten-Historisierung + Dashboard (optional)

## Wichtige Details

- **E-Mail-Adresse**: `hertz.r.kanal@gmx.de` (bitte überprüfen!)
- **GMx App-Passwort**: Nicht das normale Passwort! Unter https://www.gmx.de/app-passwort erstellen
- **Groq kostenlos**: https://console.groq.com (100 Requests/Minute ohne API-Key, mit Key unbegrenzt)
- **User-Agents**: Große Scraper (ImmoScout) blocken Bots → Realistic User-Agent nötig

## Nächste Schritte

1. `.env` ausfüllen (GMx App-Passwort, Groq-Key)
2. `config.yaml` überprüfen (E-Mail-Adresse!)
3. Phase 2 starten: Scraper-Implementierung
