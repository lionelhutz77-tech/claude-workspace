"""
Test-Version der Pipeline mit Mock-Daten
"""

import yaml
import json
import logging
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from test_mock_data import test_properties

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


def run_test_pipeline():
    """Test-Pipeline mit Mock-Daten"""
    logger.info("=" * 60)
    logger.info("[START] TEST-PIPELINE MIT MOCK-DATEN")
    logger.info("=" * 60)

    # 1. Config laden
    with open("config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    logger.info(f"[CONFIG] Config geladen: {config['search_criteria']['postleitzahl']} {config['search_criteria']['stadt']}")

    # 2. Mock-Daten verwenden
    logger.info(f"[MOCK] Verwende {len(test_properties)} Test-Immobilien")
    raw_properties = test_properties

    # 3. Bereinigen
    logger.info("[CLEAN] Daten bereinigen...")
    cleaned_properties = []
    for prop in raw_properties:
        if not all(k in prop for k in ["adresse", "kaufpreis", "wohnungen"]):
            logger.warning(f"[WARNING] Unvollstaendig: {prop.get('adresse', '???')}")
            continue

        prop["kaufpreis"] = int(prop.get("kaufpreis", 0))
        prop["wohnungen"] = int(prop.get("wohnungen", 0))
        prop["baujahr"] = int(prop.get("baujahr", 2000))
        prop["groesse_qm"] = int(prop.get("groesse_qm", 100))
        cleaned_properties.append(prop)

    logger.info(f"[OK] {len(cleaned_properties)}/{len(raw_properties)} gültig")

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

    # 6. Detailausgabe
    logger.info("[RESULTS] Detailierte Ergebnisse:")
    for i, prop in enumerate(evaluated_properties[:5], 1):
        logger.info(f"  {i}. {prop['adresse']}")
        logger.info(f"     Brutto: {prop.get('brutto_rendite', 0):.1f}%, Cashflow: {prop.get('netto_cashflow', 0):.0f}€")
        logger.info(f"     PROFIT: {prop.get('kategorie_profit', {}).get('qualifiziert', False)}")
        logger.info(f"     FAMILY: {prop.get('kategorie_family', {}).get('qualifiziert', False)}")

    # 7. Mail versenden (Test)
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

    # 8. Archivieren
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)

    archive_file = data_dir / f"test_scan_{timestamp}.json"
    with open(archive_file, "w", encoding="utf-8") as f:
        json.dump(evaluated_properties, f, indent=2, ensure_ascii=False)
    logger.info(f"[ARCHIVE] Daten archiviert: {archive_file}")

    logger.info("=" * 60)
    logger.info("[DONE] TEST-PIPELINE ABGESCHLOSSEN")
    logger.info("=" * 60)


if __name__ == "__main__":
    try:
        run_test_pipeline()
    except Exception as e:
        logger.exception(f"[CRITICAL] Kritischer Fehler: {e}")
