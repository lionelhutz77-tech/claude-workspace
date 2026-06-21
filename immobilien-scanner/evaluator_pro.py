"""
ULTRA-PROFESSIONAL EVALUATOR v2.0
- Phase 1: Miet-Check.de Integration (Mietpotenzial)
- Phase 2: ESG/Energieeffizienz + Lage-Scoring + Finanzierungs-Stress-Test
"""

import os
import json
import logging
from typing import Dict, List
from groq import Groq

logger = logging.getLogger(__name__)

# KONSTANTEN (2026-Standard)
RUHRGEBIET_MARKTMIETE = 5.73  # €/m² (Zensus 2022 Oberhausen)
BOTTROP_MARKTMIETE = 5.50     # €/m² (geschätzt, etwas ländlicher)
STRESS_TEST_ZINSSATZ = 6.0    # % (stress case)


def evaluate_properties_pro(properties: List[Dict], config: Dict) -> List[Dict]:
    """
    Ultra-professionelle Evaluierung mit Phase 1+2:
    - Mietpotenzial-Analyse (Marktmiete vs. aktuell)
    - ESG/Energieeffizienz (Green Premium/Brown Discount)
    - Lage-Scoring (Zentral/B-Lage/Rand + Infrastruktur)
    - Finanzierungs-Stress-Test
    """

    logger.info("🤖 GROQ ULTRA-PRO Evaluierung...")

    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    properties_text = json.dumps(properties, indent=2, ensure_ascii=False)

    prompt = f"""Du bist ein **Senior Immobilien-Analyst** (20+ Jahre) für professionelle Investoren.

BEWERTUNGS-FRAMEWORK 2026:
=========================

**FINANZIELLE METRIKEN:**
1. Kaltmiete × Wohnungen = Jahresmiete
2. Brutto-Rendite = Jahresmiete / Kaufpreis × 100
3. Kosten monatlich: Verwaltung (10%), Instandhaltung (1,50€/m²), Versicherung (40€), Leerstand (3%)
4. Netto-Cashflow = (Kaltmiete × Wohnungen) - Kosten
5. Kreditrate = (Kaufpreis × 80%) / (30J × 12M) × (4% + 1%)
6. Netto-Cashflow nach Kredit = Cashflow - Kreditrate
7. Netto-Rendite = (Netto-Cashflow × 12 / Eigenkapital 20%) × 100

**PHASE 1: MIETPOTENZIAL-ANALYSE** (Marktmiete Ruhrgebiet: {RUHRGEBIET_MARKTMIETE}€/m²)
- Vergleich: Aktuelle Miete vs. Marktmiete
- Potenzial = (Marktmiete - Aktuelle Miete) × Fläche × 12 / Jahr
- Beispiel: Aktuell 4,50€/m², Potential 5,73€/m² = +1,23€/m² = +650€/Monat bei 520m²
- **Score-Bonus:** Hoher Miete-upside = +20 Punkte

**PHASE 2A: ESG/ENERGIEEFFIZIENZ** (Mandatory 2026!)
- Energieklasse A-B: Green Premium +15% Wert, bessere Finanzierung
- Energieklasse C-D: Neutral
- Energieklasse E-G: Brown Discount -10% bis -30%, schwieriger finanzierbar
- **Baujahr vor 1978:** Energieverordnung oft nicht erfüllt = Risiko
- **Score-Faktor:** A/B = +15, C/D = 0, E/G = -20

**PHASE 2B: LAGE-SCORING** (Zentral vs. Randlage)
Oberhausen 46149 Innenstadt / Sterkrade: Zentral = +25 Punkte
Oberhausen sonst: B-Lage = +15 Punkte
Bottrop/Umlage: Randlage = +5 Punkte
+ Infrastruktur-Boni:
  - ÖPNV Anbindung (U/S-Bahn < 500m): +5
  - Einkaufen/Schulen (< 1km): +5
  - Grünflächen (Park < 500m): +5

**PHASE 2C: FINANZIERUNGS-STRESS-TEST**
Standard: 4% Zins, 1% Tilgung = 5% p.a.
Stress: 6% Zins, 1% Tilgung = 7% p.a. (Was wenn Zinsen steigen?)
- Wenn Netto-Cashflow bei 7% unter 300€ wird = ⚠️ Warnung
- Wenn unter 0€ = 🔴 Finanzierungsrisiko

**KATEGORIE 1: PROFIT** (6%+ Brutto, selbsttragend)
- Muss 6-8%+ Brutto haben
- Muss +500€ Netto-Cashflow/Monat haben
- Score = Brutto% + Lage + Energieeffizienz + Mietpotenzial (0-100)

**KATEGORIE 2: FAMILY** (0%+, für Eltern)
- Auch 0% oder negativ ok (Familie zahlt NK)
- Zentral 46149 = Bonus
- Score = (Brutto% + 10) × 5 + Lage + Energieeffizienz (0-100)

**ROTE FLAGGEN:**
- Brutto < 6% → PROFIT: AUSSCHLUSS
- Netto-Cashflow < -500€ → ALLE: AUSSCHLUSS
- Baujahr < 1950 → -20 Punkte (Keller, Heizung)
- Energieklasse E/F/G → -20 Punkte (Brown Discount!)
- Stress-Test-Cashflow < 300€ → ⚠️ Warnung

**INPUT-DATEN:**
{properties_text}

**ERWARTET STRUKTUR PRO IMMOBILIE:**
{{
  "adresse": "...",
  "kaufpreis": 450000,
  "wohnungen": 4,
  "baujahr": 1985,
  "groesse_qm": 320,
  "energieklasse": "D",  // ← Neu: aus Scraper

  // Finanzielle Metriken:
  "brutto_rendite": 7.6,
  "cashflow_vor_kredit": 2116,
  "netto_cashflow": 1116,
  "netto_rendite": 11.2,

  // Phase 1: Mietpotenzial
  "mietpotenzial": {{
    "aktuelle_miete_pro_m2": 5.10,
    "marktmiete_pro_m2": 5.73,
    "steigerungs_potential_euro_monatlich": 650,
    "steigerungs_potential_prozent": 12.3
  }},

  // Phase 2: ESG + Lage + Stress
  "esg_bewertung": {{
    "energieklasse": "D",
    "green_premium": 0,
    "brown_discount_prozent": 0,
    "finanzierungsrisiko": "niedrig"
  }},

  "lage": {{
    "kategorie": "B-Lage Zentral (46149)",
    "lage_score": 78,
    "infrastruktur": "ausgezeichnet"
  }},

  "finanzierungs_stress": {{
    "standard_cashflow": 1116,
    "stress_6pct_cashflow": 650,
    "stress_status": "ok" // oder "warnung"/"kritisch"
  }},

  "rote_flaggen": ["Baujahr 1985: Keller-Prüfung"],
  "positive_merkmale": ["Garage", "Garten"],

  "kategorie_profit": {{
    "qualifiziert": true,
    "score": 75,
    "empfehlung": "GUT — 7,6% Brutto, +1.1k€ Cashflow, Mietpotenzial +650€"
  }},

  "kategorie_family": {{
    "qualifiziert": false,
    "score": 0,
    "grund": "Nicht in PLZ 46149 (zentral)"
  }}
}}

Gib nur gültiges JSON zurück, pro Immobilie wie oben. Array von allen Properties.
"""

    message = client.messages.create(
        model="llama-3.3-70b-versatile",
        max_tokens=8000,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    response_text = message.content[0].text

    try:
        # JSON extrahieren
        if "```json" in response_text:
            json_str = response_text.split("```json")[1].split("```")[0].strip()
        elif "[" in response_text:
            json_str = response_text[response_text.index("["):response_text.rindex("]")+1]
        else:
            json_str = response_text

        evaluated = json.loads(json_str)
        return evaluated if isinstance(evaluated, list) else [evaluated]

    except json.JSONDecodeError as e:
        logger.error(f"JSON-Parse Fehler: {e}")
        return properties


def calculate_miet_potential(current_miete_per_m2: float, groesse_qm: float, region: str = "OB") -> Dict:
    """
    Mietpotenzial berechnen (Phase 1)
    """
    markt_miete = BOTTROP_MARKTMIETE if "Bottrop" in region else RUHRGEBIET_MARKTMIETE

    monthly_increase = (markt_miete - current_miete_per_m2) * groesse_qm
    yearly_increase = monthly_increase * 12
    percent_increase = ((markt_miete - current_miete_per_m2) / current_miete_per_m2) * 100 if current_miete_per_m2 > 0 else 0

    return {
        "aktuelle_miete_pro_m2": current_miete_per_m2,
        "marktmiete_pro_m2": markt_miete,
        "steigerungs_potential_euro_monatlich": round(monthly_increase, 2),
        "steigerungs_potential_prozent": round(percent_increase, 1)
    }


def evaluate_esg(energieklasse: str, baujahr: int) -> Dict:
    """
    ESG/Energieeffizienz-Bewertung (Phase 2A)
    """
    if not energieklasse:
        energieklasse = "N/A"

    green_premium = 15 if energieklasse in ["A", "B"] else 0
    brown_discount = -20 if energieklasse in ["E", "F", "G"] else 0

    # Baujahr-Faktor
    if baujahr < 1978:
        baujahr_factor = -10  # Oft nicht energetisch saniert
    elif baujahr < 2000:
        baujahr_factor = -5
    else:
        baujahr_factor = 5

    return {
        "energieklasse": energieklasse,
        "green_premium": green_premium,
        "brown_discount_prozent": brown_discount,
        "baujahr_faktor": baujahr_factor,
        "finanzierungsrisiko": "niedrig" if green_premium > 0 else ("hoch" if brown_discount < 0 else "mittel")
    }


if __name__ == "__main__":
    import yaml
    logging.basicConfig(level=logging.INFO)

    with open("config.yaml", "r") as f:
        config = yaml.safe_load(f)

    test_props = [{
        "adresse": "Musterstraße 42, 46149 Oberhausen",
        "kaufpreis": 450000, "wohnungen": 4, "baujahr": 1985,
        "groesse_qm": 320, "energieklasse": "D",
        "renovierungen": "Bad 2020", "merkmal_garten": True,
        "merkmal_balkon": True, "merkmal_garage": 2,
        "quelle": "ImmoScout24", "link": "https://example.com"
    }]

    result = evaluate_properties_pro(test_props, config)
    print(json.dumps(result, indent=2, ensure_ascii=False))
