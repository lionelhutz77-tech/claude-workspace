"""
Template für Immobilien-Scraper

Kopiere diese Datei für neue Quellen und implementiere die scrape()-Funktion
"""

import logging
import time
from typing import List, Dict

logger = logging.getLogger(__name__)


def scrape_QUELLE_NAME(postleitzahl: str = "46149", delay: float = 2.0) -> List[Dict]:
    """
    Scraper für [QUELLE EINTRAGEN]

    Args:
        postleitzahl: PLZ zum Filtern (default: 46149)
        delay: Verzögerung zwischen Requests (Respekt für Server)

    Returns:
        Liste von Immobilien-Daten:
        {
            "adresse": "Straße 42, 46149 Oberhausen",
            "kaufpreis": 450000,
            "wohnungen": 4,
            "baujahr": 1985,
            "groesse_qm": 320,
            "renovierungen": "Bad 2020, Fenster 2018",
            "merkmal_garten": True,
            "merkmal_balkon": True,
            "merkmal_garage": 2,
            "quelle": "QUELLE_NAME",
            "link": "https://example.com/obj123"
        }
    """

    logger.info(f"🔄 Scraping [QUELLE_NAME] für PLZ {postleitzahl}...")

    properties = []

    # TODO: Implementierung
    # Option 1: HTML-Scraping (BeautifulSoup)
    # - requests.get() + BeautifulSoup
    # - CSS-Selektoren oder XPath
    # - Schleifen durch Cards/Items

    # Option 2: JavaScript-Rendering (Selenium/Playwright)
    # - Browser starten
    # - Seite laden
    # - Warten auf Daten
    # - JavaScript ausführen
    # - DOM parsen

    # Beispiel-Struktur:
    # from bs4 import BeautifulSoup
    # import requests
    #
    # url = "https://example.com/search?plz=46149"
    # response = requests.get(url, headers={"User-Agent": "Mozilla/5.0..."})
    # soup = BeautifulSoup(response.content, "html.parser")
    #
    # for item in soup.select(".immobilie-card"):  # CSS-Selector
    #     try:
    #         prop = {
    #             "adresse": item.select_one(".address").text.strip(),
    #             "kaufpreis": int(item.select_one(".price").text.replace("€", "").replace(".", "")),
    #             ...
    #             "quelle": "[QUELLE_NAME]",
    #             "link": item.select_one("a")["href"]
    #         }
    #         properties.append(prop)
    #     except Exception as e:
    #         logger.warning(f"⚠️  Parse-Fehler: {e}")
    #
    #     time.sleep(delay)

    logger.info(f"✅ {len(properties)} Objekte gefunden auf [QUELLE_NAME]")
    return properties


if __name__ == "__main__":
    # Test
    logging.basicConfig(level=logging.INFO)
    results = scrape_QUELLE_NAME()
    print(f"Ergebnis: {len(results)} Props")
    if results:
        print(results[0])
