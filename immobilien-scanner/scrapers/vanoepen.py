"""
Immobilien van Oepen (Bottrop/Marl)
WordPress mit "inx-detail-list"-Plugin: saubere Label/Wert-Span-Paare.
Listing-Seite -> Detail-Seiten.
"""

import logging
import time
import re
import unicodedata
from typing import List, Dict
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

BASE = "https://immobilien-vanoepen.de"
LISTING_URL = "https://immobilien-vanoepen.de/immobilien/"
DETAIL_RE = re.compile(r"https://immobilien-vanoepen\.de/immobilien/[a-z0-9][a-z0-9%\-]+/")

WORTZAHL = {"zwei": 2, "drei": 3, "vier": 4, "fünf": 5, "fuenf": 5, "sechs": 6}


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    })
    return s


def parse_inx_details(soup: BeautifulSoup) -> Dict[str, str]:
    """Liest die inx-detail-list Label/Wert-Paare in ein Dict."""
    details = {}
    for item in soup.select(".inx-detail-list__item"):
        title = item.select_one(".inx-detail-list__title")
        value = item.select_one(".inx-detail-list__value")
        if title and value:
            key = unicodedata.normalize("NFKC", title.get_text(strip=True)).rstrip(":").strip()
            val = unicodedata.normalize("NFKC", value.get_text(" ", strip=True)).strip()
            details[key] = val
    return details


def _num(val: str, default: int = 0) -> int:
    m = re.search(r"[\d.]+", val.replace(".", "") if val else "")
    return int(m.group(0)) if m else default


def _units(title: str, details: Dict[str, str]) -> int:
    blob = (title + " " + details.get("Objektart", "") + " " + details.get("Objekttyp", "")).lower()
    for wort, n in WORTZAHL.items():
        if f"{wort}familienhaus" in blob:
            return n
    if "mehrfamilien" in blob or "zinshaus" in blob or "wohnanlage" in blob:
        return 3
    we = details.get("Wohneinheiten") or details.get("Anzahl Wohneinheiten") or ""
    if we and _num(we):
        return _num(we)
    return 1


def scrape_vanoepen(postleitzahl: str = "46236") -> List[Dict]:
    logger.info("[SCRAPE] van Oepen...")
    properties: List[Dict] = []
    session = _session()

    try:
        r = session.get(LISTING_URL, timeout=15)
        r.raise_for_status()
        links = sorted(set(
            l for l in DETAIL_RE.findall(r.text)
            if l.rstrip("/") != LISTING_URL.rstrip("/") and "/page" not in l
        ))
        logger.info(f"[DATA] Gefundene Exposes: {len(links)}")

        for link in links:
            try:
                d = session.get(link, timeout=15)
                d.raise_for_status()
                ds = BeautifulSoup(d.content, "html.parser")

                title = (ds.title.string or "").split("–")[0].split("|")[0].strip() if ds.title else ""
                det = parse_inx_details(ds)

                kp_raw = det.get("Kaufpreis", "")
                if not kp_raw:
                    continue  # Mietobjekt oder Preis auf Anfrage
                kaufpreis = _num(kp_raw)
                if kaufpreis < 50000:
                    continue

                groesse = _num(det.get("Wohnfläche", ""), 100)
                baujahr = _num(det.get("Baujahr", ""), 2000)
                wohnungen = _units(title, det)
                if wohnungen < 2:
                    continue  # nur Mehrfamilienobjekte

                full_text = unicodedata.normalize("NFKC", ds.get_text(" ", strip=True)).lower()
                ek_m = re.search(r"energieeffizienzklasse\s*:?\s*([a-h])", full_text)
                energieklasse = ek_m.group(1).upper() if ek_m else ""

                ort = det.get("Ort") or det.get("Lage") or "Bottrop/Marl"

                properties.append({
                    "adresse": f"{title[:60]} [{ort[:20]}]",
                    "kaufpreis": kaufpreis,
                    "wohnungen": wohnungen,
                    "baujahr": baujahr,
                    "groesse_qm": groesse,
                    "renovierungen": "",
                    "merkmal_garten": "garten" in full_text,
                    "merkmal_balkon": "balkon" in full_text,
                    "merkmal_garage": 1 if ("garage" in full_text or "stellplatz" in full_text) else 0,
                    "energieklasse": energieklasse,
                    "quelle": "van Oepen",
                    "link": link,
                })
                logger.debug(f"[OK] {title[:45]} ({kaufpreis}€, {wohnungen} WE)")

            except requests.RequestException as e:
                logger.warning(f"[WARNING] Detail-Fehler {link}: {e}")
            except Exception as e:
                logger.warning(f"[WARNING] Parse-Fehler {link}: {e}")
            time.sleep(0.3)

    except Exception as e:
        logger.error(f"[ERROR] van Oepen: {e}")

    logger.info(f"[OK] van Oepen: {len(properties)} Objekte")
    return properties


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    res = scrape_vanoepen()
    print(f"\n[OK] {len(res)} MFH-Objekte")
    for r in res:
        print(f"  - {r['adresse'][:55]} | {r['kaufpreis']:,}€ | {r['wohnungen']} WE | BJ {r['baujahr']} | {r['groesse_qm']}m²")
