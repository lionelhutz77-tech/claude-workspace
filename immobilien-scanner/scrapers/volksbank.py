"""
Scraper für Volksbank Immobilien Rhein-Ruhr
"""

import logging
import time
import re
from typing import List, Dict
from playwright.async_api import async_playwright
import asyncio

logger = logging.getLogger(__name__)


async def scrape_volksbank(postleitzahl: str = "46149", delay: float = 1.5) -> List[Dict]:
    """
    Scraper für Volksbank Immobilien Rhein-Ruhr
    Website: https://www.volksbank-immobilien-rhein-ruhr.de
    """

    logger.info(f"🔄 Scraping Volksbank Immobilien für PLZ {postleitzahl}...")

    properties = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        await page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

        try:
            url = f"https://www.volksbank-immobilien-rhein-ruhr.de/"

            logger.info(f"📍 Navigiere zu: {url}")
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(2000)

            # Listings finden
            listings = await page.query_selector_all(".property-item, article, .listing, [data-property]")

            logger.info(f"📊 Gefundene Listings: {len(listings)}")

            for i, listing in enumerate(listings[:35]):
                try:
                    text = await listing.inner_text()

                    # Adresse
                    addr_elem = await listing.query_selector("h2, h3, .title")
                    adresse = await addr_elem.inner_text() if addr_elem else "???"

                    # Preis
                    price_elem = await listing.query_selector(".price, [class*='preis']")
                    price_text = await price_elem.inner_text() if price_elem else "0"
                    kaufpreis = parse_price(price_text)

                    # Link
                    link_elem = await listing.query_selector("a[href*='immobilie']")
                    link = await link_elem.get_attribute("href") if link_elem else ""
                    if link and not link.startswith("http"):
                        link = "https://www.volksbank-immobilien-rhein-ruhr.de" + link

                    # Daten aus Text
                    wohnungen = extract_number(text, "Wohnungen", 1)
                    baujahr = extract_number(text, "Baujahr", 2000)
                    groesse = extract_number(text, r"m²", 100)

                    # Merkmale
                    garten = "Garten" in text
                    balkon = "Balkon" in text
                    garage = 1 if "Garage" in text else 0

                    prop = {
                        "adresse": adresse.strip(),
                        "kaufpreis": kaufpreis,
                        "wohnungen": wohnungen,
                        "baujahr": baujahr,
                        "groesse_qm": groesse,
                        "renovierungen": "",
                        "merkmal_garten": garten,
                        "merkmal_balkon": balkon,
                        "merkmal_garage": garage,
                        "quelle": "Volksbank Immobilien",
                        "link": link
                    }

                    if kaufpreis > 50000 and wohnungen >= 2:
                        properties.append(prop)
                        logger.debug(f"✅ {adresse.strip()[:50]}")

                except Exception as e:
                    logger.warning(f"⚠️  Parse-Fehler {i}: {e}")

                time.sleep(delay)

        except Exception as e:
            logger.error(f"❌ Fehler Volksbank: {e}")

        finally:
            await browser.close()

    logger.info(f"✅ Volksbank: {len(properties)} Objekte gefunden")
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


def run_sync(postleitzahl: str = "46149") -> List[Dict]:
    return asyncio.run(scrape_volksbank(postleitzahl))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = run_sync()
    print(f"\n✅ {len(results)} Props")
