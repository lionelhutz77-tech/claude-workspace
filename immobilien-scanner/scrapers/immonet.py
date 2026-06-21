"""
Scraper für Immonet
JavaScript-Rendering nötig → Playwright
"""

import logging
import time
import re
from typing import List, Dict
from playwright.async_api import async_playwright
import asyncio

logger = logging.getLogger(__name__)


async def scrape_immonet(postleitzahl: str = "46149", delay: float = 1.5) -> List[Dict]:
    """
    Scraper für Immonet (Mehrfamilienhäuser)

    Args:
        postleitzahl: PLZ (default: 46149)
        delay: Verzögerung zwischen Actions

    Returns:
        Liste von Immobilien-Daten
    """

    logger.info(f"🔄 Scraping Immonet für PLZ {postleitzahl}...")

    properties = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        await page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

        try:
            # Immonet Such-URL (Kauf, Mehrfamilienhaus)
            # API-basiert: /search/list?type=apartment&zip=46149
            url = f"https://www.immonet.de/immobilien/search.html?zip={postleitzahl}&objecttype=Mehrfamilienhaus&action=search"

            logger.info(f"📍 Navigiere zu: {url}")
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(2000)

            # Listings finden (Immonet-HTML-Struktur)
            listings = await page.query_selector_all(".ListItem")
            logger.info(f"📊 Gefundene Listings: {len(listings)}")

            for i, listing in enumerate(listings[:50]):
                try:
                    # Titel (Adresse)
                    title = await listing.query_selector(".ListItem-address")
                    title_text = await title.inner_text() if title else "???"

                    # Preis
                    price = await listing.query_selector(".ListItem-price")
                    price_text = await price.inner_text() if price else "0"
                    kaufpreis = parse_price(price_text)

                    # Link
                    link_elem = await listing.query_selector("a")
                    link = await link_elem.get_attribute("href") if link_elem else ""
                    if link and not link.startswith("http"):
                        link = "https://www.immonet.de" + link

                    # Meta-Infos (oft schon in der Liste)
                    meta_text = await listing.inner_text()

                    # Kurz-Parsing aus List-View
                    wohnungen = parse_number(meta_text, "Wohnungen", 1)
                    baujahr = parse_number(meta_text, "Baujahr", 2000)
                    groesse = parse_number(meta_text, "m²|Fläche", 100)

                    prop = {
                        "adresse": title_text.strip(),
                        "kaufpreis": kaufpreis,
                        "wohnungen": wohnungen,
                        "baujahr": baujahr,
                        "groesse_qm": groesse,
                        "renovierungen": "",
                        "merkmal_garten": "Garten" in meta_text,
                        "merkmal_balkon": "Balkon" in meta_text,
                        "merkmal_garage": 1 if "Garage" in meta_text else 0,
                        "quelle": "Immonet",
                        "link": link
                    }
                    properties.append(prop)
                    logger.debug(f"✅ {title_text.strip()[:50]} ({kaufpreis}€)")

                except Exception as e:
                    logger.warning(f"⚠️  Parse-Fehler in Listing {i}: {e}")

                time.sleep(delay)

        except Exception as e:
            logger.error(f"❌ Fehler beim Scraping Immonet: {e}")

        finally:
            await browser.close()

    logger.info(f"✅ Immonet: {len(properties)} Objekte gefunden")
    return properties


def parse_price(price_str: str) -> int:
    """Preis-String → Int"""
    try:
        clean = re.sub(r"[^0-9.]", "", price_str).replace(".", "")
        return int(clean) if clean else 0
    except:
        return 0


def parse_number(text: str, pattern: str, default: int = 0) -> int:
    """Zahl aus Text extrahieren"""
    try:
        match = re.search(rf"{pattern}\s*[:—]?\s*(\d+)", text, re.IGNORECASE)
        return int(match.group(1)) if match else default
    except:
        return default


def run_sync(postleitzahl: str = "46149") -> List[Dict]:
    """Sync-Wrapper"""
    return asyncio.run(scrape_immonet(postleitzahl))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = run_sync("46149")
    print(f"\n✅ Ergebnis: {len(results)} Props")
    for r in results[:3]:
        print(f"  - {r['adresse'][:50]} | {r['kaufpreis']}€")
