"""
Groq-basierte Bewertung von Immobilien nach Rendite- und Risiko-Kriterien
"""

import os
import json
from typing import Dict, List
from groq import Groq

def evaluate_properties(properties: List[Dict], config: Dict) -> List[Dict]:
    """
    Bewertet Immobilien mit Groq API basierend auf Kriterien

    Args:
        properties: Liste von Immobilien-Daten
        config: Config-Dict mit Schwellwerten

    Returns:
        properties mit hinzugefügten Feldern: score, rendite, cashflow, rote_flaggen, empfehlung
    """

    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    # Batch-Verarbeitung: Alle Props auf einmal evaluieren
    properties_text = json.dumps(properties, indent=2, ensure_ascii=False)

    prompt = f"""Du bist ein Immobilien-Analyist mit 20 Jahren Erfahrung in der Renditeberechnung.

BEWERTUNGS-KRITERIEN (aus config):
- Min. Wohnungen: {config['search_criteria']['min_wohnungen']}
- Kaltmiete/Einheit: {config['search_criteria']['kaltmiete_pro_einheit']}€/Monat
- Verwaltungsquote: {config['search_criteria']['verwaltungsquote_prozent']}%
- Instandhaltung: {config['search_criteria']['instandhaltung_euro_pro_qm']}€/m²
- Versicherung: {config['search_criteria']['versicherung_monatlich']}€
- Leerstand-Puffer: {config['search_criteria']['leerstand_puffer_prozent']}%
- Finanzierung: {config['search_criteria']['ltv_prozent']}% LTV, {config['search_criteria']['zinssatz_prozent']}% Zinssatz, {config['search_criteria']['tilgung_prozent']}% Tilgung

SCHWELLWERTE:
- Min. Cashflow: {config['evaluation_thresholds']['min_cashflow_monatlich']}€/Monat
- Min. Rendite: {config['evaluation_thresholds']['min_rendite_prozent']}% p.a.
- Max. Renovierungskosten: {config['evaluation_thresholds']['max_renovierungskosten']}€
- Baujahr-Risiko: vor {config['evaluation_thresholds']['baujahr_vor']}

FOLGENDE IMMOBILIEN analysieren:
{properties_text}

PRO IMMOBILIE BERECHNE UND BEWERTE:
1. **Cashflow pro Monat**: (Kaltmiete × Wohnungen) - (Verwaltung + Instandh. + Versicherung + Leerstand)
2. **Groß-Finanzierungsbedarf**: Kaufpreis × (1 - LTV%)
3. **Monatliche Kreditrate**: (Kaufpreis × LTV%) / (360 Monate / 12) × (Zinssatz + Tilgung)%
4. **Netto-Cashflow**: Cashflow - Kreditrate
5. **Brutto-Rendite**: (Cashflow × 12 / Kaufpreis) × 100
6. **Netto-Rendite**: (Netto-Cashflow × 12 / Eigenkapital) × 100

ROTE FLAGGEN prüfen:
- Baujahr älter als {config['evaluation_thresholds']['baujahr_vor']}? (→ feuchte Keller, alte Heizung wahrscheinlich)
- Renovierungsangaben vorhanden? (→ Kosten einschätzen)
- Renovierungskosten > {config['evaluation_thresholds']['max_renovierungskosten']}€? (AUSSCHLUSSKRITERIUM)
- Netto-Cashflow < {config['evaluation_thresholds']['min_cashflow_monatlich']}€? (AUSSCHLUSSKRITERIUM)

POSITIVE MERKMALE geben +5 Punkte je:
- Garten vorhanden
- Balkon (obere Wohnung)
- Garage/Stellplatz
- Renoviert (letzte 10 Jahre)
- Neue Heizung (letzte 5 Jahre)

SCORING (0-100):
- < 40: NICHT EMPFOHLEN (rote Flaggen überwiegen)
- 40-60: PRÜFEN (Potenzial, aber Risiken)
- 60-80: GUT (rentabel, moderate Risiken)
- 80+: SEHR GUT (hohe Rendite, wenig Risiken)

**OUTPUT-FORMAT** (JSON, pro Immobilie):
{{
  "adresse": "...",
  "kaufpreis": 12345,
  "wohnungen": 5,
  "baujahr": 1975,
  "cashflow_monatlich": 637,
  "brutto_rendite": 6.2,
  "netto_cashflow": 150,
  "netto_rendite": 8.5,
  "score": 72,
  "rote_flaggen": ["Baujahr 1975: Wahrscheinlich feuchte Keller", "Renovierung ansteht (Bad ~15k€)"],
  "positive_merkmale": ["Garage vorhanden", "Garten"],
  "empfehlung": "GUT - Rendite ok, aber Keller-Prüfung vor Kauf essentiell",
  "prioritaet": 1
}}

Rangiere nach Priorität (Score absteigend). Gib nur gültige JSON-Array zurück, keine Erklärungen.
"""

    message = client.messages.create(
        model="llama-3.3-70b-versatile",
        max_tokens=4096,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    # Parse Groq-Response
    response_text = message.content[0].text

    try:
        # Versuche JSON aus Response zu extrahieren
        if "```json" in response_text:
            json_str = response_text.split("```json")[1].split("```")[0].strip()
        elif "[" in response_text:
            json_str = response_text[response_text.index("["):response_text.rindex("]")+1]
        else:
            json_str = response_text

        evaluated = json.loads(json_str)
        return evaluated if isinstance(evaluated, list) else [evaluated]

    except json.JSONDecodeError as e:
        print(f"Fehler beim JSON-Parse: {e}")
        print(f"Response: {response_text}")
        return properties


if __name__ == "__main__":
    # Test-Beispiel
    test_props = [
        {
            "adresse": "Musterstraße 42, 46149 Oberhausen",
            "kaufpreis": 450000,
            "wohnungen": 4,
            "baujahr": 1985,
            "groesse_qm": 320,
            "renovierungen": "Bad 2020, Fenster 2018",
            "merkmal_garten": True,
            "merkmal_balkon": True,
            "merkmal_garage": 2,
            "link": "https://example.com"
        }
    ]

    import yaml
    with open("config.yaml", "r") as f:
        config = yaml.safe_load(f)

    result = evaluate_properties(test_props, config)
    print(json.dumps(result, indent=2, ensure_ascii=False))
