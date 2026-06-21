"""
Scraper für KL Immobilien (lokaler Makler Oberhausen)
Statisches HTML → BeautifulSoup reicht
"""

import logging
import time
import re
from typing import List, Dict
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def scrape_kl_immobilien(postleitzahl: str = "46149", delay: float = 1.0) -> List[Dict]:
    """
    Scraper für KL Immobilien
    Website: https://kl-immo-web.de/immobilienangebot/

    Args:
        postleitzahl: PLZ (für Filterung, falls nötig)
        delay: Verzögerung zwischen Requests

    Returns:
        Liste von Immobilien-Daten
    """

    logger.info(f"🔄 Scraping KL Immobilien...")

    properties = []
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    })

    try:
        # KL Immobilien Listings-Seite
        url = "https://kl-immo-web.de/immobilienangebot/"

        logger.info(f"📍 Navigiere zu: {url}")
        response = session.get(url, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")

        # KL Immobilien HTML-Struktur identifizieren
        # Typischerweise: div.property-card, article.property, etc.
        listings = soup.select(".property, article.listing, div.immobilie-eintrag, .immobilien-card")

        # Fallback: generische Link-Suche
        if not listings:
            listings = soup.find_all("a", href=re.compile(r"/immobilie|/expose|/objekt"))

        logger.info(f"📊 Gefundene Listings: {len(listings)}")

        for i, listing in enumerate(listings[:30]):
            try:
                # HTML-Struktur variiert je nach Makler
                # Versuche verschiedene Selektoren

                # Adresse
                address_elem = listing.select_one(".address, .title, h2, h3, .property-title")
                adresse = address_elem.get_text(strip=True) if address_elem else "???"

                # Preis
                price_elem = listing.select_one(".price, .kaufpreis, .betrag")
                price_text = price_elem.get_text(strip=True) if price_elem else "0"
                kaufpreis = parse_price(price_text)

                # Link zu Expose
                link = ""
                link_elem = listing.find("a", href=True)
                if link_elem:
                    link = link_elem["href"]
                    if not link.startswith("http"):
                        link = "https://kl-immo-web.de" + link

                # Weitere Infos aus Text (Heuristik)
                listing_text = listing.get_text()

                wohnungen = extract_number(listing_text, "Wohnungen", 1)
                baujahr = extract_number(listing_text, "Baujahr", 2000)
                groesse = extract_number(listing_text, r"(?:qm|m²|Fläche)", 100)

                # Merkmale
                garten = bool(re.search(r"garten", listing_text, re.IGNORECASE))
                balkon = bool(re.search(r"balkon", listing_text, re.IGNORECASE))
                garage_match = re.search(r"(?:garage|stellplatz)\s*[:—]?\s*(\d+)", listing_text, re.IGNORECASE)
                garage = int(garage_match.group(1)) if garage_match else 0

                # Filter: nur Mehrfamilienhäuser (Wohnungen > 1)
                if wohnungen < 2:
                    continue

                prop = {
                    "adresse": adresse,
                    "kaufpreis": kaufpreis,
                    "wohnungen": wohnungen,
                    "baujahr": baujahr,
                    "groesse_qm": groesse,
                    "renovierungen": "",
                    "merkmal_garten": garten,
                    "merkmal_balkon": balkon,
                    "merkmal_garage": garage,
                    "quelle": "KL Immobilien",
                    "link": link
                }

                # Nur hinzufügen, wenn Kaufpreis > 0 (echte Angebote)
                if kaufpreis > 50000:
                    properties.append(prop)
                    logger.debug(f"✅ {adresse[:50]} ({kaufpreis}€)")

            except Exception as e:
                logger.warning(f"⚠️  Parse-Fehler in Listing {i}: {e}")

            time.sleep(delay)

    except requests.RequestException as e:
        logger.error(f"❌ HTTP-Fehler KL Immobilien: {e}")
    except Exception as e:
        logger.error(f"❌ Fehler beim Scraping KL Immobilien: {e}")

    logger.info(f"✅ KL Immobilien: {len(properties)} Objekte gefunden")
    return properties


def parse_price(price_str: str) -> int:
    """Preis-String → Int"""
    try:
        clean = re.sub(r"[^0-9.]", "", price_str).replace(".", "")
        return int(clean) if clean else 0
    except:
        return 0


def extract_number(text: str, pattern: str, default: int = 0) -> int:
    """Zahl aus Text extrahieren"""
    try:
        match = re.search(rf"{pattern}\s*[:—]?\s*(\d+)", text, re.IGNORECASE)
        return int(match.group(1)) if match else default
    except:
        return default


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_kl_immobilien()
    print(f"\n✅ Ergebnis: {len(results)} Props")
    for r in results[:3]:
        print(f"  - {r['adresse'][:50]} | {r['kaufpreis']}€ | {r['wohnungen']} Whg")
