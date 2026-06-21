"""Bönighausen Immobilien (Bottrop/Marl/Ruhrgebiet)"""
import logging, re
from typing import List, Dict
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

def scrape_boenighausen(postleitzahl: str = "46119") -> List[Dict]:
    logger.info("🔄 Bönighausen...")
    properties = []
    try:
        session = requests.Session()
        session.headers.update({"User-Agent": "Mozilla/5.0"})
        url = "https://www.boenighausen-immobilien.de/objekte/"
        response = session.get(url, timeout=10)
        soup = BeautifulSoup(response.content, "html.parser")
        listings = soup.select(".property, .listing, .expose, article")

        for listing in listings[:30]:
            try:
                text = listing.get_text()
                addr = listing.select_one("h2, h3, .title")
                adresse = addr.get_text(strip=True) if addr else "???"
                price = listing.select_one(".price, [class*='preis']")
                kaufpreis = parse_price(price.get_text() if price else "0")
                link = listing.find("a", href=True)
                link = link["href"] if link else ""
                if link and not link.startswith("http"):
                    link = "https://www.boenighausen-immobilien.de" + link

                # Filter: nur PLZ-Bereich (wenn in Text)
                if postleitzahl and postleitzahl not in adresse and postleitzahl not in text:
                    continue

                wohnungen = extract_number(text, "Wohnungen", 1)
                baujahr = extract_number(text, "Baujahr", 2000)
                groesse = extract_number(text, "m²", 100)

                if wohnungen < 2 or kaufpreis < 50000:
                    continue

                energieklasse = extract_energy_class(text)

                properties.append({
                    "adresse": adresse, "kaufpreis": kaufpreis, "wohnungen": wohnungen,
                    "baujahr": baujahr, "groesse_qm": groesse, "renovierungen": "",
                    "merkmal_garten": "Garten" in text, "merkmal_balkon": "Balkon" in text,
                    "merkmal_garage": 1 if "Garage" in text else 0,
                    "energieklasse": energieklasse,
                    "quelle": "Bönighausen Immobilien", "link": link
                })
            except Exception as e:
                logger.warning(f"⚠️  {e}")
    except Exception as e:
        logger.error(f"❌ Bönighausen: {e}")

    logger.info(f"✅ Bönighausen: {len(properties)} Objekte")
    return properties

def parse_price(s: str) -> int:
    try:
        return int(re.sub(r"[^0-9.]", "", s).replace(".", ""))
    except:
        return 0

def extract_number(text: str, pattern: str, default: int = 0) -> int:
    try:
        match = re.search(rf"{pattern}\s*[:—]?\s*(\d+)", text, re.IGNORECASE)
        return int(match.group(1)) if match else default
    except:
        return default

def extract_energy_class(text: str) -> str:
    match = re.search(r"(?:Energieklasse|EPC|Energieeffizienzklasse)\s*[:—]?\s*([A-G])", text, re.IGNORECASE)
    return match.group(1) if match else None
