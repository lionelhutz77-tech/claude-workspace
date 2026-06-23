"""
Immowelt-Scraper (= Immonet, beide auf immowelt.de zusammengefuehrt)
Playwright (JS-Rendering). Daten direkt aus den Treffer-Karten der Suchseite.
Nicht durch Datadome blockiert (anders als ImmoScout24).
"""

import logging
import re
import unicodedata
from typing import List, Dict
from playwright.sync_api import sync_playwright

try:
    from scrapers.objekt_klassifikation import klassifiziere
except ImportError:
    from objekt_klassifikation import klassifiziere

logger = logging.getLogger(__name__)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

# Treffer-Karten-Text extrahieren: pro /expose/-Link den nahesten Text-Container
CARD_JS = """els=>els.map(a=>{
  let n=a; for(let i=0;i<6 && n.parentElement;i++){n=n.parentElement; if(n.innerText && n.innerText.length>60) break;}
  let href=a.getAttribute("href");
  return {href:href, text:(n.innerText||"").replace(/\\s+/g," ").trim()};
})"""


def _parse_card(href: str, text: str) -> Dict | None:
    # NFKC wandelt "m²"->"m2", "€/m²"->"€/m2"
    text = unicodedata.normalize("NFKC", text)

    # Nur Mehrfamilien-/Zweifamilien-Objekte (Vermietmodell); Einfamilienhaus raus
    typ_match = re.search(r"(Zwei|Drei|Vier|Fünf|Mehr)familienhaus|Wohnanlage|Wohnhaus|Einfamilienhaus|Reihen\w+haus|Doppelhaush|Haus zum Kauf", text, re.IGNORECASE)
    typ = typ_match.group(0) if typ_match else "Haus"

    # Kaufpreis: erste €-Zahl mit >= 50.000 (die €/m2-Zahl ist kleiner)
    kaufpreis = 0
    for m in re.finditer(r"([\d.]+)\s*€", text):
        val = int(m.group(1).replace(".", "")) if m.group(1).replace(".", "").isdigit() else 0
        if val >= 50000:
            kaufpreis = val
            break
    if kaufpreis < 50000:
        return None

    # Wohnflaeche: erste plausible "X m2" (>=20) die NICHT von "Grundst" gefolgt wird
    wohnflaeche = 0
    for m in re.finditer(r"(\d+)\s*m2", text):
        rest = text[m.end():m.end() + 12]
        val = int(m.group(1))
        if "Grundst" not in rest and val >= 20:
            wohnflaeche = val
            break

    # Zimmer (nur Info, nicht Einheiten)
    zi_m = re.search(r"([\d,]+)\s*Zimmer", text)
    zimmer = zi_m.group(1) if zi_m else ""

    # Zentrale Klassifikation (Einzelwohnung vs. ganzes MFH vs. EFH)
    kategorie, wohnungen, ist_einzelwohnung = klassifiziere(text, wohnflaeche)
    if kategorie in ("EFH", "UNKLAR"):
        return None  # Einfamilienhaus / unklar -> kein passendes Mietobjekt

    # Energieklasse: "... 22 E 249.000 €" -> Buchstabe zwischen Zahl und Preis
    ek_m = re.search(r"\d\s+([A-H])\s+[\d.]+\s*€", text)
    energieklasse = ek_m.group(1) if ek_m else ""

    # Ort + PLZ: "Stadtteil, Oberhausen (46149)" — Stadtteil ohne Leerzeichen,
    # damit fuehrendes "Grundstück " nicht miterfasst wird
    plz_m = re.search(r"([A-ZÄÖÜ][\wäöüß\-\.]+,\s*[A-ZÄÖÜ][\wäöüß\-\.]+\s*\((\d{5})\))", text)
    adresse = plz_m.group(1).strip() if plz_m else f"{typ} Oberhausen"

    baujahr_m = re.search(r"Baujahr\s*(\d{4})", text)
    baujahr = int(baujahr_m.group(1)) if baujahr_m else 2000

    if href and not href.startswith("http"):
        href = "https://www.immowelt.de" + href

    return {
        "adresse": adresse,
        "kaufpreis": kaufpreis,
        "wohnungen": wohnungen,
        "baujahr": baujahr,
        "groesse_qm": wohnflaeche or 100,
        "renovierungen": "",
        "merkmal_garten": "garten" in text.lower(),
        "merkmal_balkon": "balkon" in text.lower(),
        "merkmal_garage": 1 if re.search(r"garage|stellplatz", text, re.IGNORECASE) else 0,
        "energieklasse": energieklasse,
        "zimmer": zimmer,
        "objekt_typ": kategorie,
        "ist_einzelwohnung": ist_einzelwohnung,
        "quelle": "Immowelt/Immonet",
        "link": href.split("?")[0] if href else "",
    }


def scrape_immowelt(stadt: str = "oberhausen", max_seiten: int = 1) -> List[Dict]:
    """Scrapt Mehrfamilienhaeuser auf Immowelt fuer die angegebene Stadt."""
    logger.info(f"[SCRAPE] Immowelt/Immonet ({stadt})...")
    properties: List[Dict] = []
    seen_links = set()

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True, args=["--disable-blink-features=AutomationControlled"]
            )
            ctx = browser.new_context(user_agent=UA, locale="de-DE",
                                      viewport={"width": 1366, "height": 900})
            page = ctx.new_page()

            for seite in range(1, max_seiten + 1):
                sep = "&" if "?" in stadt else "?"
                url = f"https://www.immowelt.de/suche/{stadt}/haeuser/kaufen"
                if seite > 1:
                    url += f"?cp={seite}"

                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=40000)
                    page.wait_for_timeout(3500)
                except Exception as e:
                    logger.warning(f"[WARNING] Seite {seite} laden fehlgeschlagen: {e}")
                    continue

                if "roboter" in page.title().lower():
                    logger.error("[ERROR] Immowelt blockiert (Captcha)")
                    break

                cards = page.eval_on_selector_all('a[href*="/expose/"]', CARD_JS)
                neu = 0
                for c in cards:
                    if not c.get("href") or c["href"] in seen_links:
                        continue
                    seen_links.add(c["href"])
                    prop = _parse_card(c["href"], c["text"])
                    if prop:
                        properties.append(prop)
                        neu += 1
                logger.info(f"[DATA] Seite {seite}: {len(cards)} Karten, {neu} MFH uebernommen")

                # Immowelt paginiert nicht per URL -> bei keinen neuen Karten abbrechen
                if not cards or (seite > 1 and neu == 0):
                    break

            browser.close()

    except Exception as e:
        logger.error(f"[ERROR] Immowelt: {e}")

    logger.info(f"[OK] Immowelt/Immonet: {len(properties)} MFH-Objekte")
    return properties


def run_sync(postleitzahl: str = "46149") -> List[Dict]:
    """Sync-Wrapper (Interface fuer main.py). PLZ wird ignoriert (Stadt-Suche)."""
    return scrape_immowelt("oberhausen")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    res = scrape_immowelt("oberhausen", max_seiten=2)
    print(f"\n[OK] {len(res)} MFH-Objekte")
    for r in res:
        print(f"  - {r['adresse'][:40]:40} | {r['kaufpreis']:>9,}€ | {r['wohnungen']} WE | {r['groesse_qm']}m² | EK {r['energieklasse'] or '?'}")
