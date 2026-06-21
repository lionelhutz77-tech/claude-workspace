"""
Scraper für Immobilien-Oberhausen
https://www.immobilien-oberhausen.com/
"""

import logging
import re
from typing import List, Dict
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def scrape_immo_oberhausen(postleitzahl: str = "46149") -> List[Dict]:
    """Immobilien-Oberhausen.com"""

    logger.info("🔄 Scraping Immobilien-Oberhausen...")
    properties = []
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})

    try:
        url = "https://www.immobilien-oberhausen.com/"
        response = session.get(url, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")
        listings = soup.select(".property, .listing, .immobilie, .item")

        logger.info(f"📊 Listings: {len(listings)}")

        for listing in listings[:30]:
            try:
                text = listing.get_text()

                addr = listing.select_one("h2, h3, .title, .name")
                adresse = addr.get_text(strip=True) if addr else "???"

                price_elem = listing.select_one(".price, .preis, [class*='kaufpreis']")
                price_text = price_elem.get_text(strip=True) if price_elem else "0"
                kaufpreis = parse_price(price_text)

                link_elem = listing.find("a", href=True)
                link = link_elem["href"] if link_elem else ""
                if link and not link.startswith("http"):
                    link = "https://www.immobilien-oberhausen.com" + link

                wohnungen = extract_number(text, "Wohnungen", 1)
                baujahr = extract_number(text, "Baujahr", 2000)
                groesse = extract_number(text, r"m²", 100)

                if wohnungen < 2 or kaufpreis < 50000:
                    continue

                prop = {
                    "adresse": adresse,
                    "kaufpreis": kaufpreis,
                    "wohnungen": wohnungen,
                    "baujahr": baujahr,
                    "groesse_qm": groesse,
                    "renovierungen": "",
                    "merkmal_garten": "Garten" in text,
                    "merkmal_balkon": "Balkon" in text,
                    "merkmal_garage": 1 if "Garage" in text else 0,
                    "quelle": "Immobilien-Oberhausen",
                    "link": link
                }
                properties.append(prop)

            except Exception as e:
                logger.warning(f"⚠️  Parse-Fehler: {e}")

    except Exception as e:
        logger.error(f"❌ Fehler Immobilien-Oberhausen: {e}")

    logger.info(f"✅ Immobilien-Oberhausen: {len(properties)} Objekte")
    return properties


def parse_price(price_str: str) -> int:
    try:
        clean = re.sub(r"[^0-9.]", "", price_str).replace(".", "")
        return int(clean) if clean else 0
    except:
        return 0


def extract_number(text: str, pattern: str, default: int = 0) -> int:
    try:
        match = re.search(rf"{pattern}\s*[:—]?\s*(\d+)", text, re.IGNORECASE)
        return int(match.group(1)) if match else default
    except:
        return default
