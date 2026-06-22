"""
Immobilien-Scanner Haupt-Orchestration

Workflow:
1. Config laden
2. Alle Scraper parallel ausführen → Rohdaten
3. Daten bereinigen & vereinheitlichen
4. Groq-API: Alle Props evaluieren
5. HTML-Report generieren
6. Mail versenden
7. Daten archivieren
"""

import os
import sys
import json
import yaml
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict
from dotenv import load_dotenv

# Module importieren (später)
# from scrapers import *
# from evaluator import evaluate_properties
# from mailer import send_report

# Setup
load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("immobilien_scanner.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def load_config() -> Dict:
    """Config laden"""
    config_path = Path("config.yaml")
    if not config_path.exists():
        logger.error("[ERROR] config.yaml nicht gefunden!")
        sys.exit(1)

    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def scrape_all_sources(config: Dict) -> List[Dict]:
    """
    Alle aktivierten Scraper ausführen

    Returns:
        Liste von Immobilien-Daten
    """
    logger.info("[SCRAPE] Scraping aller Quellen...")

    all_properties = []
    postleitzahl = config['search_criteria']['postleitzahl']

    # Scraper-Imports (nur aktivierte laden)
    scrapers_to_import = {}

    # HTML-Scraper (kein Playwright-Problem)
    if config['scraper_sources'].get('kl_immobilien', {}).get('enabled', False):
        try:
            from scrapers.kl_immobilien import scrape_kl_immobilien
            scrapers_to_import['KL Immobilien'] = scrape_kl_immobilien
        except ImportError as e:
            logger.error(f"[ERROR] KL Immobilien Import: {e}")

    if config['scraper_sources'].get('sariguel', {}).get('enabled', False):
        try:
            from scrapers.sariguel import scrape_sariguel
            scrapers_to_import['CT-Immobilien (Sariguel)'] = scrape_sariguel
        except ImportError as e:
            logger.error(f"[ERROR] Sariguel Import: {e}")

    if config['scraper_sources'].get('piezonka', {}).get('enabled', False):
        try:
            from scrapers.piezonka import scrape_piezonka
            scrapers_to_import['Piezonka-Immobilien'] = scrape_piezonka
        except ImportError as e:
            logger.error(f"[ERROR] Piezonka Import: {e}")

    if config['scraper_sources'].get('immo_oberhausen', {}).get('enabled', False):
        try:
            from scrapers.immo_oberhausen import scrape_immo_oberhausen
            scrapers_to_import['Immobilien-Oberhausen'] = scrape_immo_oberhausen
        except ImportError as e:
            logger.error(f"[ERROR] Immo-Oberhausen Import: {e}")

    if config['scraper_sources'].get('marquardt', {}).get('enabled', False):
        try:
            from scrapers.marquardt import scrape_marquardt
            scrapers_to_import['Marquardt Immobilien'] = scrape_marquardt
        except ImportError as e:
            logger.error(f"[ERROR] Marquardt Import: {e}")

    if config['scraper_sources'].get('bloemker', {}).get('enabled', False):
        try:
            from scrapers.bloemker import scrape_bloemker
            scrapers_to_import['Blömker Immobilien'] = scrape_bloemker
        except ImportError as e:
            logger.error(f"[ERROR] Blömker Import: {e}")

    if config['scraper_sources'].get('vanoepen', {}).get('enabled', False):
        try:
            from scrapers.vanoepen import scrape_vanoepen
            scrapers_to_import['Immobilien van Oepen'] = scrape_vanoepen
        except ImportError as e:
            logger.error(f"[ERROR] van Oepen Import: {e}")

    if config['scraper_sources'].get('boenighausen', {}).get('enabled', False):
        try:
            from scrapers.boenighausen import scrape_boenighausen
            scrapers_to_import['Bönighausen Immobilien'] = scrape_boenighausen
        except ImportError as e:
            logger.error(f"[ERROR] Bönighausen Import: {e}")

    # JavaScript-Scraper (Playwright) — nur wenn nötig
    if config['scraper_sources'].get('immoscout24', {}).get('enabled', False):
        try:
            from scrapers.immoscout import run_sync as scrape_immoscout24
            scrapers_to_import['ImmoScout24'] = scrape_immoscout24
        except ImportError as e:
            logger.warning(f"[WARNING] ImmoScout24 Import (Playwright): {e}")

    if config['scraper_sources'].get('immonet', {}).get('enabled', False):
        try:
            from scrapers.immonet import run_sync as scrape_immonet
            scrapers_to_import['Immonet'] = scrape_immonet
        except ImportError as e:
            logger.warning(f"[WARNING] Immonet Import (Playwright): {e}")

    if config['scraper_sources'].get('sparkasse', {}).get('enabled', False):
        try:
            from scrapers.sparkasse import run_sync as scrape_sparkasse
            scrapers_to_import['Sparkasse'] = scrape_sparkasse
        except ImportError as e:
            logger.warning(f"[WARNING] Sparkasse Import (Playwright): {e}")

    if config['scraper_sources'].get('volksbank', {}).get('enabled', False):
        try:
            from scrapers.volksbank import run_sync as scrape_volksbank
            scrapers_to_import['Volksbank'] = scrape_volksbank
        except ImportError as e:
            logger.warning(f"[WARNING] Volksbank Import (Playwright): {e}")

    # Scraper ausführen
    for name, scraper_func in scrapers_to_import.items():
        try:
            logger.info(f"[LOAD] {name} ladet...")
            props = scraper_func(postleitzahl)
            all_properties.extend(props)
            logger.info(f"[OK] {name}: {len(props)} Props")
        except Exception as e:
            logger.error(f"[ERROR] Fehler in {name}: {e}")

    # Duplikate entfernen (gleiche Adresse + Preis)
    unique_props = {}
    for prop in all_properties:
        key = (prop['adresse'], prop['kaufpreis'])
        if key not in unique_props:
            unique_props[key] = prop

    all_properties = list(unique_props.values())
    logger.info(f"[OK] Gesamt nach Duplikat-Filter: {len(all_properties)} Immobilien gefunden")
    return all_properties


def clean_data(properties: List[Dict]) -> List[Dict]:
    """Daten validieren und vereinheitlichen"""
    logger.info("[CLEAN] Daten bereinigen...")

    cleaned = []
    for prop in properties:
        # Validierung
        if not all(k in prop for k in ["adresse", "kaufpreis", "wohnungen"]):
            logger.warning(f"[WARNING] Unvollstaendig: {prop.get('adresse', '???')}")
            continue

        # Typkonvertierung
        prop["kaufpreis"] = int(prop.get("kaufpreis", 0))
        prop["wohnungen"] = int(prop.get("wohnungen", 0))
        prop["baujahr"] = int(prop.get("baujahr", 2000))
        prop["groesse_qm"] = int(prop.get("groesse_qm", 100))

        cleaned.append(prop)

    logger.info(f"[OK] {len(cleaned)}/{len(properties)} gültig")
    return cleaned


def run_pipeline():
    """Haupt-Pipeline"""
    logger.info("=" * 60)
    logger.info("[START] IMMOBILIEN-SCANNER GESTARTET")
    logger.info("=" * 60)

    # 1. Config laden
    config = load_config()
    logger.info(f"[CONFIG] Config geladen: {config['search_criteria']['postleitzahl']} {config['search_criteria']['stadt']}")

    # 2. Scrapen
    raw_properties = scrape_all_sources(config)

    # 3. Bereinigen
    cleaned_properties = clean_data(raw_properties)

    # 4. Evaluieren (Simple lokale Regellogik)
    logger.info("[EVAL] Einfache lokale Evaluierung...")
    try:
        from evaluator_simple import evaluate_properties_simple
        evaluated_properties = evaluate_properties_simple(cleaned_properties, config)
        logger.info(f"[OK] {len(evaluated_properties)} Props evaluiert")
    except Exception as e:
        logger.error(f"[ERROR] Evaluierung fehlgeschlagen: {e}")
        evaluated_properties = cleaned_properties

    # 5. Filtern (nur Schwellwerte erfüllt)
    filtered = [
        p for p in evaluated_properties
        if p.get("netto_cashflow", 0) >= config["evaluation_thresholds"]["category_profit"]["min_cashflow_monatlich"]
    ]
    logger.info(f"[FILTER] Nach Filterung: {len(filtered)}/{len(evaluated_properties)} empfohlenswert")

    # 6. Mail versenden
    logger.info("[MAIL] Report wird vorbereitet...")
    try:
        from mailer import send_report
        success = send_report(filtered, config)
        if success:
            logger.info("[OK] Mail versendet!")
        else:
            logger.warning("[WARNING] Mail-Versand fehlgeschlagen")
    except Exception as e:
        logger.error(f"[ERROR] Mail-Fehler: {e}")

    # 7. Archivieren
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)

    archive_file = data_dir / f"scan_{timestamp}.json"
    with open(archive_file, "w", encoding="utf-8") as f:
        json.dump(evaluated_properties, f, indent=2, ensure_ascii=False)
    logger.info(f"[ARCHIVE] Daten archiviert: {archive_file}")

    # 8. Lokalen Report im Browser oeffnen (falls vorhanden)
    report_file = Path("reports") / "report_neuester.html"
    if report_file.exists() and filtered:
        try:
            import webbrowser
            webbrowser.open(report_file.resolve().as_uri())
            logger.info(f"[OPEN] Report im Browser geoeffnet: {report_file.resolve()}")
        except Exception as e:
            logger.warning(f"[WARNING] Report konnte nicht geoeffnet werden: {e}")

    logger.info("=" * 60)
    logger.info("[DONE] PIPELINE ABGESCHLOSSEN")
    logger.info("=" * 60)


if __name__ == "__main__":
    try:
        run_pipeline()
    except Exception as e:
        logger.exception(f"[CRITICAL] Kritischer Fehler: {e}")
        sys.exit(1)
