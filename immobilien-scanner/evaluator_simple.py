"""
EINFACHER FALLBACK-EVALUATOR (keine Groq API)
Lokale Regellogik für Immobilien-Bewertung
"""

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

RUHRGEBIET_MARKTMIETE = 5.73


def evaluate_properties_simple(properties: List[Dict], config: Dict) -> List[Dict]:
    """
    Einfache lokale Evaluierung ohne Groq API
    Verwendet Regellogik statt LLM
    """

    logger.info("[EVAL] Einfache lokale Evaluierung...")

    for prop in properties:
        # Basis-Metriken
        kaufpreis = prop.get("kaufpreis", 0)
        wohnungen = prop.get("wohnungen", 1)
        groesse_qm = prop.get("groesse_qm", 100)
        baujahr = prop.get("baujahr", 2000)

        # Angenommene Kaltmiete
        kaltmiete_pro_unit = config['search_criteria']['kaltmiete_pro_einheit']
        jahresmiete = kaltmiete_pro_unit * wohnungen * 12
        brutto_rendite = (jahresmiete / kaufpreis * 100) if kaufpreis > 0 else 0

        # Kosten
        verwaltung = kaltmiete_pro_unit * wohnungen * 12 * 0.10 / 12
        instandhaltung = groesse_qm * 1.50
        versicherung = 40
        leerstand = kaltmiete_pro_unit * wohnungen * 0.03
        kosten_monatlich = verwaltung + instandhaltung + versicherung + leerstand

        # Cashflow
        cashflow_vor_kredit = kaltmiete_pro_unit * wohnungen - kosten_monatlich
        kreditrate = (kaufpreis * 0.80) / (30 * 12) * 0.05  # 5% total
        netto_cashflow = cashflow_vor_kredit - kreditrate
        eigenkapital = kaufpreis * 0.20
        netto_rendite = (netto_cashflow * 12 / eigenkapital * 100) if eigenkapital > 0 else 0

        # Simpel Scoring
        score = 0
        if brutto_rendite >= 8:
            score += 40
        elif brutto_rendite >= 6:
            score += 25
        elif brutto_rendite >= 4:
            score += 15
        else:
            score += 5

        if netto_cashflow >= 1000:
            score += 30
        elif netto_cashflow >= 500:
            score += 20
        elif netto_cashflow >= 0:
            score += 10

        if baujahr > 1970:
            score += 15
        if baujahr < 1950:
            score -= 10

        # Merkmale
        if prop.get("merkmal_garten"):
            score += 5
        if prop.get("merkmal_balkon"):
            score += 5
        if prop.get("merkmal_garage"):
            score += 5

        # ESG simple
        energieklasse = prop.get("energieklasse", "D")
        if energieklasse in ["A", "B"]:
            score += 10
        elif energieklasse in ["E", "F", "G"]:
            score -= 15

        # Rote Flaggen
        rote_flaggen = []
        if baujahr < 1950:
            rote_flaggen.append("Baujahr vor 1950: Keller-Risiko")
        if brutto_rendite < 4:
            rote_flaggen.append(f"Niedrige Rendite: {brutto_rendite:.1f}%")

        # Kategorie PROFIT
        kategorie_profit = {
            "qualifiziert": brutto_rendite >= 6 and netto_cashflow >= 500,
            "score": max(0, min(100, score)),
            "empfehlung": f"Brutto {brutto_rendite:.1f}%, Cashflow {netto_cashflow:.0f}€"
        }

        # Kategorie FAMILY
        kategorie_family = {
            "qualifiziert": "46149" in prop.get("adresse", "") and netto_cashflow > -500,
            "score": max(0, min(100, score - 10)) if "46149" in prop.get("adresse", "") else 0,
            "empfehlung": "Zentral 46149, fuer Familie geeignet" if "46149" in prop.get("adresse", "") else "Nicht zentral"
        }

        # Output
        prop.update({
            "brutto_rendite": round(brutto_rendite, 1),
            "netto_cashflow": round(netto_cashflow, 0),
            "netto_rendite": round(netto_rendite, 1),
            "rote_flaggen": rote_flaggen,
            "positive_merkmale": [m for m in ["Garage", "Garten", "Balkon", "Renoviert"]
                                 if ("garage" in str(prop).lower() or "garten" in str(prop).lower() or m.lower() in str(prop).lower())],
            "kategorie_profit": kategorie_profit,
            "kategorie_family": kategorie_family,
        })

    logger.info(f"[OK] {len(properties)} Properties evaluiert (simple)")
    return properties
