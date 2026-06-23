"""
Blömker Immobilien (Bottrop/Ruhrgebiet)
Listing-Seite -> Detail-Seiten mit Label|Wert-Tabelle.
Hinweis: Blömker handelt überwiegend Ein-/Zweifamilienhäuser.
"""

import logging
import time
import re
import unicodedata
from typing import List, Dict
import requests
from bs4 import BeautifulSoup

try:
    from scrapers.objekt_klassifikation import klassifiziere
except ImportError:
    from objekt_klassifikation import klassifiziere

logger = logging.getLogger(__name__)

LISTING_URL = "https://bloemker-immobilien.de/immobilien/"
DETAIL_RE = re.compile(r"https://bloemker-immobilien\.de/immobilien/[a-z][a-z0-9\-]+-(\d+)/")


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    })
    return s


def _kv(text: str, label: str) -> str:
    """Wert nach 'Label|' aus normalisiertem Pipe-Text holen."""
    m = re.search(rf"{label}[^|]*\|\s*([^|]{{1,30}})", text)
    return m.group(1).strip() if m else ""


def _kv_int(text: str, label: str, default: int) -> int:
    raw = _kv(text, label)
    m = re.search(r"\d+", raw.replace(".", ""))
    return int(m.group(0)) if m else default


def scrape_bloemker(postleitzahl: str = "46119") -> List[Dict]:
    logger.info("[SCRAPE] Blömker Immobilien...")
    properties: List[Dict] = []
    session = _session()

    try:
        r = session.get(LISTING_URL, timeout=15)
        r.raise_for_status()

        # Detail-Links (nur Kauf, kein "mieten")
        links = sorted(set(
            m.group(0) for m in DETAIL_RE.finditer(r.text)
            if "mieten" not in m.group(0)
        ))
        logger.info(f"[DATA] Gefundene Exposes: {len(links)}")

        for link in links:
            try:
                d = session.get(link, timeout=15)
                d.raise_for_status()
                dsoup = BeautifulSoup(d.content, "html.parser")

                title = (dsoup.title.string or "").split("|")[0].strip() if dsoup.title else ""
                text = unicodedata.normalize("NFKC", dsoup.get_text("|", strip=True))

                kp_raw = _kv(text, "Kaufpreis")
                kp_m = re.search(r"([\d.]+)", kp_raw)
                kaufpreis = int(kp_m.group(1).replace(".", "")) if kp_m else 0

                groesse = _kv_int(text, "Wohnfläche", 100)
                baujahr = _kv_int(text, "Baujahr", 2000)
                slug = link.rstrip("/").split("/")[-1]
                kategorie, wohnungen, ist_einzelwohnung = klassifiziere(
                    f"{title} {slug.replace('-', ' ')}", groesse
                )

                # Stadt aus Slug: ...-in-{stadt}-kaufen-{id}
                stadt_m = re.search(r"-in-([a-z\-]+?)-(?:kaufen|kauf)", slug)
                stadt = stadt_m.group(1).replace("-", " ").title() if stadt_m else "Ruhrgebiet"

                ek_m = re.search(r"Energieeffizienzklasse[^|]*\|\s*([A-H])", text)
                energieklasse = ek_m.group(1).upper() if ek_m else ""

                if kategorie in ("EFH", "UNKLAR") or kaufpreis < 50000:
                    continue

                properties.append({
                    "adresse": f"{title[:70]} [{stadt}]",
                    "kaufpreis": kaufpreis,
                    "wohnungen": wohnungen,
                    "baujahr": baujahr,
                    "groesse_qm": groesse,
                    "renovierungen": "",
                    "merkmal_garten": "garten" in text.lower(),
                    "merkmal_balkon": "balkon" in text.lower(),
                    "merkmal_garage": 1 if "garage" in text.lower() else 0,
                    "energieklasse": energieklasse,
                    "objekt_typ": kategorie,
                    "ist_einzelwohnung": ist_einzelwohnung,
                    "quelle": "Blömker Immobilien",
                    "link": link,
                })
                logger.debug(f"[OK] {title[:45]} ({kaufpreis}€, {wohnungen} WE)")

            except requests.RequestException as e:
                logger.warning(f"[WARNING] Detail-Fehler {link}: {e}")
            except Exception as e:
                logger.warning(f"[WARNING] Parse-Fehler {link}: {e}")

            time.sleep(0.4)

    except Exception as e:
        logger.error(f"[ERROR] Blömker: {e}")

    logger.info(f"[OK] Blömker: {len(properties)} Objekte")
    return properties


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    res = scrape_bloemker()
    print(f"\n[OK] {len(res)} Props")
    for r in res:
        print(f"  - {r['adresse'][:55]} | {r['kaufpreis']:,}€ | {r['wohnungen']} WE | BJ {r['baujahr']}")
