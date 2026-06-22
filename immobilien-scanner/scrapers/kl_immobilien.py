"""
Scraper für KL Immobilien (lokaler Makler Oberhausen)
WooCommerce-Shop: Immobilien sind "Produkte" unter /produkt/...
Listings-Seite -> Detail-Seiten (Label:Wert-Paare im HTML)
"""

import logging
import time
import re
from typing import List, Dict
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

LISTING_URL = "https://kl-immo-web.de/immobilienangeboten/kauf/"
BASE = "https://kl-immo-web.de"

# Wortzahl -> Anzahl Wohneinheiten (aus Titel)
WORTZAHL = {
    "ein": 1, "zwei": 2, "drei": 3, "vier": 4, "fünf": 5, "fuenf": 5,
    "sechs": 6, "sieben": 7, "acht": 8, "neun": 9, "zehn": 10,
}


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    })
    return s


def _parse_label(text: str, label: str) -> str:
    """Wert nach 'Label:' aus Fließtext holen (bis Zeilenende/nächstes Label)."""
    m = re.search(rf"{label}\s*(?:ca\.)?\s*:?\s*([^\n|]{{1,60}})", text, re.IGNORECASE)
    return m.group(1).strip() if m else ""


def _parse_price(text: str) -> int:
    """'449.000,00 EUR' -> 449000"""
    m = re.search(r"Kaufpreis\s*:?\s*([\d.]+)", text)
    if not m:
        return 0
    try:
        return int(m.group(1).replace(".", ""))
    except ValueError:
        return 0


def _parse_int(text: str, label: str, default: int) -> int:
    raw = _parse_label(text, label)
    m = re.search(r"\d+", raw)
    return int(m.group(0)) if m else default


def _units_from_title(title: str) -> int:
    """Anzahl Wohneinheiten aus Titel ableiten."""
    t = title.lower()
    # 1. Hausform mit Zahlwort: "Zweifamilienhaus", "Fünffamilienhaus" (am eindeutigsten)
    for wort, n in WORTZAHL.items():
        if f"{wort}familienhaus" in t:
            return n
    # 2. "24 Wohnungen" (explizite Einheiten-Zahl, nur wenn keine Hausform)
    m = re.search(r"(\d+)\s*(?:frei[a-z]*\s+)?wohnung", t)
    if m:
        return int(m.group(1))
    # 3. Generisches MFH ohne klare Zahl -> konservativer Default
    if "mehrfamilien" in t or "wohnensemble" in t or "portfolio" in t:
        return 3
    return 1


def scrape_kl_immobilien(postleitzahl: str = "46149", delay: float = 0.5) -> List[Dict]:
    """Scraper für KL Immobilien (WooCommerce-Detailseiten)."""
    logger.info("[SCRAPE] Scraping KL Immobilien...")

    properties: List[Dict] = []
    session = _session()

    try:
        r = session.get(LISTING_URL, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.content, "html.parser")

        # Alle Detail-Links (/produkt/...) einsammeln, deduplizieren
        produkt_links = []
        seen = set()
        for a in soup.find_all("a", href=re.compile(r"/produkt/")):
            href = a["href"]
            if not href.startswith("http"):
                href = BASE + href
            if href not in seen:
                seen.add(href)
                produkt_links.append(href)

        logger.info(f"[DATA] Gefundene Exposes: {len(produkt_links)}")

        for i, link in enumerate(produkt_links):
            try:
                dr = session.get(link, timeout=15)
                dr.raise_for_status()
                dsoup = BeautifulSoup(dr.content, "html.parser")

                title = dsoup.title.string if dsoup.title else ""
                title = title.split(" - KL Immobilien")[0].strip() if title else ""

                detail_text = dsoup.get_text("\n", strip=True)

                kaufpreis = _parse_price(detail_text)
                groesse = _parse_int(detail_text, "Wohnfläche", 100)
                baujahr = _parse_int(detail_text, "Baujahr", 2000)
                wohnungen = _units_from_title(title)

                # Adresse: KL veröffentlicht keine Objekt-Adresse (nur Büro-Adresse
                # "Dorstener Str. 313" auf jeder Seite). Daher Titel als Bezeichnung.
                # Stadt/PLZ aus Titel extrahieren, falls vorhanden.
                stadt_match = re.search(r"\b(4\d{4})\b|\b(Oberhausen|Bottrop|Essen|Mülheim|Duisburg)\b", title)
                stadt = (stadt_match.group(0) if stadt_match else "Oberhausen/Umgebung")
                adresse = f"{title[:70]} [{stadt}]"

                # Energieklasse (A-H), falls vorhanden
                ek_match = re.search(r"Energieeffizienzklasse\s*:?\s*([A-H])", detail_text, re.IGNORECASE)
                energieklasse = ek_match.group(1).upper() if ek_match else ""

                merkmal_garten = bool(re.search(r"garten", detail_text, re.IGNORECASE))
                merkmal_balkon = bool(re.search(r"balkon", detail_text, re.IGNORECASE))
                garage_match = re.search(r"(\d+)\s*(?:garage|stellpl)", detail_text, re.IGNORECASE)
                merkmal_garage = int(garage_match.group(1)) if garage_match else (
                    1 if re.search(r"garage|stellplatz", detail_text, re.IGNORECASE) else 0
                )

                # Filter: nur Mehrfamilienhäuser (>= 2 WE) und echte Preise
                if wohnungen < 2:
                    continue
                if kaufpreis < 50000:
                    continue

                properties.append({
                    "adresse": adresse,
                    "kaufpreis": kaufpreis,
                    "wohnungen": wohnungen,
                    "baujahr": baujahr,
                    "groesse_qm": groesse,
                    "renovierungen": "",
                    "merkmal_garten": merkmal_garten,
                    "merkmal_balkon": merkmal_balkon,
                    "merkmal_garage": merkmal_garage,
                    "energieklasse": energieklasse,
                    "quelle": "KL Immobilien",
                    "link": link,
                })
                logger.debug(f"[OK] {adresse[:50]} ({kaufpreis}€, {wohnungen} WE)")

            except requests.RequestException as e:
                logger.warning(f"[WARNING] Detail-Fehler {link}: {e}")
            except Exception as e:
                logger.warning(f"[WARNING] Parse-Fehler {link}: {e}")

            time.sleep(delay)

    except requests.RequestException as e:
        logger.error(f"[ERROR] HTTP-Fehler KL Immobilien: {e}")
    except Exception as e:
        logger.error(f"[ERROR] Fehler beim Scraping KL Immobilien: {e}")

    logger.info(f"[OK] KL Immobilien: {len(properties)} Objekte gefunden")
    return properties


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_kl_immobilien()
    print(f"\n[OK] Ergebnis: {len(results)} Props")
    for r in results:
        print(f"  - {r['adresse'][:55]} | {r['kaufpreis']:,}€ | {r['wohnungen']} WE | BJ {r['baujahr']} | {r['groesse_qm']}m²")
