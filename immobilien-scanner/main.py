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
        logger.error("❌ config.yaml nicht gefunden!")
        sys.exit(1)

    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def scrape_all_sources(config: Dict) -> List[Dict]:
    """
    Alle aktivierten Scraper ausführen (Placeholder)

    Returns:
        Liste von Immobilien-Daten (minimal):
        {
            "adresse": str,
            "kaufpreis": int,
            "wohnungen": int,
            "baujahr": int,
            "groesse_qm": int,
            "renovierungen": str,
            "merkmal_garten": bool,
            "merkmal_balkon": bool,
            "merkmal_garage": int,
            "quelle": str,
            "link": str
        }
    """
    logger.info("🔄 Scraping aller Quellen...")

    all_properties = []

    # TODO: Implementiere Scraper für jede Quelle
    # from scrapers.immoscout import scrape_immoscout24
    # from scrapers.immonet import scrape_immonet
    # etc.

    # Placeholder: Test-Daten
    logger.warning("⚠️  Scraper noch nicht implementiert, verwende Test-Daten")
    all_properties = [
        {
            "adresse": "Musterstraße 42, 46149 Oberhausen",
            "kaufpreis": 450000,
            "wohnungen": 4,
            "baujahr": 1985,
            "groesse_qm": 320,
            "renovierungen": "Bad 2020, Fenster 2018",
            "merkmal_garten": True,
            "merkmal_balkon": True,
            "merkmal_garage": 2,
            "quelle": "ImmoScout24",
            "link": "https://immobilienscout24.de/example"
        },
        {
            "adresse": "Königstr. 100, 46145 Oberhausen",
            "kaufpreis": 380000,
            "wohnungen": 3,
            "baujahr": 1975,
            "groesse_qm": 240,
            "renovierungen": "Heizung 2015",
            "merkmal_garten": False,
            "merkmal_balkon": True,
            "merkmal_garage": 0,
            "quelle": "KL Immobilien",
            "link": "https://kl-immo-web.de/example"
        }
    ]

    logger.info(f"✅ {len(all_properties)} Immobilien gefunden")
    return all_properties


def clean_data(properties: List[Dict]) -> List[Dict]:
    """Daten validieren und vereinheitlichen"""
    logger.info("🧹 Daten bereinigen...")

    cleaned = []
    for prop in properties:
        # Validierung
        if not all(k in prop for k in ["adresse", "kaufpreis", "wohnungen"]):
            logger.warning(f"⚠️  Unvollständig: {prop.get('adresse', '???')}")
            continue

        # Typkonvertierung
        prop["kaufpreis"] = int(prop.get("kaufpreis", 0))
        prop["wohnungen"] = int(prop.get("wohnungen", 0))
        prop["baujahr"] = int(prop.get("baujahr", 2000))
        prop["groesse_qm"] = int(prop.get("groesse_qm", 100))

        cleaned.append(prop)

    logger.info(f"✅ {len(cleaned)}/{len(properties)} gültig")
    return cleaned


def run_pipeline():
    """Haupt-Pipeline"""
    logger.info("=" * 60)
    logger.info("🚀 IMMOBILIEN-SCANNER GESTARTET")
    logger.info("=" * 60)

    # 1. Config laden
    config = load_config()
    logger.info(f"📋 Config geladen: {config['search_criteria']['postleitzahl']} {config['search_criteria']['stadt']}")

    # 2. Scrapen
    raw_properties = scrape_all_sources(config)

    # 3. Bereinigen
    cleaned_properties = clean_data(raw_properties)

    # 4. Evaluieren (Groq)
    logger.info("🤖 Groq-Evaluierung lädt...")
    # TODO: from evaluator import evaluate_properties
    # evaluated_properties = evaluate_properties(cleaned_properties, config)
    evaluated_properties = cleaned_properties  # Placeholder

    # 5. Filtern (nur Schwellwerte erfüllt)
    filtered = [
        p for p in evaluated_properties
        if p.get("netto_cashflow", 0) >= config["evaluation_thresholds"]["min_cashflow_monatlich"]
    ]
    logger.info(f"📊 Nach Filterung: {len(filtered)}/{len(evaluated_properties)} empfohlenswert")

    # 6. Mail versenden
    logger.info("📧 Report wird vorbereitet...")
    # TODO: from mailer import send_report
    # success = send_report(filtered, config)
    # if success:
    #     logger.info("✅ Mail versendet!")

    # 7. Archivieren
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)

    archive_file = data_dir / f"scan_{timestamp}.json"
    with open(archive_file, "w", encoding="utf-8") as f:
        json.dump(evaluated_properties, f, indent=2, ensure_ascii=False)
    logger.info(f"💾 Daten archiviert: {archive_file}")

    logger.info("=" * 60)
    logger.info("✅ PIPELINE ABGESCHLOSSEN")
    logger.info("=" * 60)


if __name__ == "__main__":
    try:
        run_pipeline()
    except Exception as e:
        logger.exception(f"❌ Kritischer Fehler: {e}")
        sys.exit(1)
