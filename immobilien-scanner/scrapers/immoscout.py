"""
Scraper für ImmoScout24
JavaScript-Rendering nötig → Playwright
"""

import logging
import time
import re
from typing import List, Dict
from playwright.async_api import async_playwright
import asyncio

logger = logging.getLogger(__name__)


async def scrape_immoscout24(postleitzahl: str = "46149", delay: float = 2.0) -> List[Dict]:
    """
    Scraper für ImmoScout24 (Mehrfamilienhäuser/Wohnungen)

    Args:
        postleitzahl: PLZ zum Filtern (default: 46149)
        delay: Verzögerung zwischen Actions

    Returns:
        Liste von Immobilien-Daten
    """

    logger.info(f"🔄 Scraping ImmoScout24 für PLZ {postleitzahl}...")

    properties = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # User-Agent (ImmoScout mag keine Bots)
        await page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

        try:
            # Such-URL aufbauen (Mehrfamilienhäuser, 46149)
            # ImmoScout-Format: /Suche/de/immobilie-kaufen?postcode=46149&objecttype=2
            url = f"https://www.immobilienscout24.de/Suche/de/immobilie-kaufen?postcode={postleitzahl}&objecttype=2"

            logger.info(f"📍 Navigiere zu: {url}")
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(2000)  # Seite laden

            # Alle Listings scrollen und laden
            listings = await page.query_selector_all("li.is-search-result")
            logger.info(f"📊 Gefundene Listings: {len(listings)}")

            for i, listing in enumerate(listings[:50]):  # Max 50 pro Session
                try:
                    # Expose properties (Text extrahieren)
                    title = await listing.query_selector(".result-list-entry__address")
                    title_text = await title.inner_text() if title else "???"

                    price = await listing.query_selector(".result-list-entry__price")
                    price_text = await price.inner_text() if price else "0"

                    # Text-Parsing
                    kaufpreis = parse_price(price_text)
                    adresse = title_text.strip()

                    # Link zum Objekt
                    link_elem = await listing.query_selector("a.result-list-entry__brand-title")
                    link = await link_elem.get_attribute("href") if link_elem else ""
                    if link and not link.startswith("http"):
                        link = "https://www.immobilienscout24.de" + link

                    # Detail-Seite öffnen (für mehr Infos)
                    details = await scrape_immoscout_details(page, link) if link else {}

                    prop = {
                        "adresse": adresse,
                        "kaufpreis": kaufpreis,
                        "wohnungen": details.get("wohnungen", 1),
                        "baujahr": details.get("baujahr", 2000),
                        "groesse_qm": details.get("groesse_qm", 100),
                        "renovierungen": details.get("renovierungen", ""),
                        "merkmal_garten": details.get("garten", False),
                        "merkmal_balkon": details.get("balkon", False),
                        "merkmal_garage": details.get("garage", 0),
                        "quelle": "ImmoScout24",
                        "link": link
                    }
                    properties.append(prop)
                    logger.debug(f"✅ {adresse} ({kaufpreis}€)")

                except Exception as e:
                    logger.warning(f"⚠️  Parse-Fehler in Listing {i}: {e}")

                time.sleep(delay)

        except Exception as e:
            logger.error(f"❌ Fehler beim Scraping ImmoScout24: {e}")

        finally:
            await browser.close()

    logger.info(f"✅ ImmoScout24: {len(properties)} Objekte gefunden")
    return properties


async def scrape_immoscout_details(page, link: str) -> Dict:
    """
    Öffnet Expose und extrahiert Details (Baujahr, Wohnungen, etc.)
    """

    details = {}

    try:
        if not link:
            return details

        # Neue Tab für Details öffnen
        context = page.context
        detail_page = await context.new_page()

        logger.debug(f"📄 Lade Details: {link[:60]}...")
        await detail_page.goto(link, wait_until="networkidle", timeout=20000)
        await detail_page.wait_for_timeout(1000)

        # Baujahr extrahieren (oft in der Exposé)
        baujahr_text = await detail_page.inner_text("body")
        baujahr_match = re.search(r"Baujahr\s*[:—]\s*(\d{4})", baujahr_text, re.IGNORECASE)
        details["baujahr"] = int(baujahr_match.group(1)) if baujahr_match else 2000

        # Wohnungen (suche nach "Wohnungen" oder "Einheiten")
        wohnungen_match = re.search(r"(?:Anzahl\s+)?Wohnungen?\s*[:—]\s*(\d+)", baujahr_text, re.IGNORECASE)
        details["wohnungen"] = int(wohnungen_match.group(1)) if wohnungen_match else 1

        # Größe
        groesse_match = re.search(r"(?:Gesamtfläche|Wohnfläche)\s*[:—]\s*([\d.]+)\s*m", baujahr_text, re.IGNORECASE)
        details["groesse_qm"] = int(float(groesse_match.group(1))) if groesse_match else 100

        # Merkmale (Garten, Balkon, Garage)
        details["garten"] = bool(re.search(r"Garten", baujahr_text, re.IGNORECASE))
        details["balkon"] = bool(re.search(r"Balkon", baujahr_text, re.IGNORECASE))
        garage_match = re.search(r"(?:Garage|Stellplätze?)\s*[:—]\s*(\d+)", baujahr_text, re.IGNORECASE)
        details["garage"] = int(garage_match.group(1)) if garage_match else 0

        # Renovierungen (freier Text)
        if re.search(r"renoviert|Sanierung|Modernisierung", baujahr_text, re.IGNORECASE):
            reno_text = ""
            if re.search(r"(?:Bad|Badezimmer).*?renoviert", baujahr_text, re.IGNORECASE):
                reno_text += "Bad 2020er, "
            if re.search(r"(?:Fenster|Heizung).*?(?:neu|modern)", baujahr_text, re.IGNORECASE):
                reno_text += "Fenster/Heizung modern, "
            details["renovierungen"] = reno_text.rstrip(", ")

        await detail_page.close()

    except Exception as e:
        logger.debug(f"⚠️  Fehler bei Detail-Scraping: {e}")

    return details


def parse_price(price_str: str) -> int:
    """Preistext in Int konvertieren"""
    try:
        # "450.000 €" → 450000
        clean = re.sub(r"[^0-9.]", "", price_str).replace(".", "")
        return int(clean)
    except:
        return 0


def run_sync(postleitzahl: str = "46149") -> List[Dict]:
    """Sync-Wrapper für async Funktion"""
    return asyncio.run(scrape_immoscout24(postleitzahl))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = run_sync("46149")
    print(f"\n✅ Ergebnis: {len(results)} Props")
    for r in results[:3]:
        print(f"  - {r['adresse']} | {r['kaufpreis']}€ | {r['wohnungen']} Whg | {r['baujahr']}")
