"""
Groq-basierte Bewertung von Immobilien nach Rendite- und Risiko-Kriterien
"""

import os
import json
from typing import Dict, List
from groq import Groq

def evaluate_properties(properties: List[Dict], config: Dict) -> List[Dict]:
    """
    Bewertet Immobilien mit Groq API basierend auf ZWEI KATEGORIEN:

    1. PROFIT: Mehrfamilienhäuser überall, 6%+ Rendite (klassisches Investment)
    2. FAMILY: PLZ 46149, 0%+ Rendite ok (Vermietung an Eltern/Bekannte)

    Args:
        properties: Liste von Immobilien-Daten
        config: Config-Dict mit Schwellwerten (beide Kategorien)

    Returns:
        properties mit Feldern:
        - score_profit, kategorie_profit, empfehlung_profit
        - score_family, kategorie_family, empfehlung_family
        - kategorie (primary)
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

PRO IMMOBILIE BERECHNE UND BEWERTE (ZWEI KATEGORIEN):

**FINANZIELLE METRIKEN (für beide Kategorien):**
1. **Kaltmiete-Basis**: {config['search_criteria']['kaltmiete_pro_einheit']}€ × Wohnungen × 12 = Jahresmiete
2. **Brutto-Rendite**: (Jahresmiete / Kaufpreis) × 100
3. **Kosten (monatlich)**: (Verwaltung + Instandh. + Versicherung + Leerstand)
4. **Cashflow-vor-Kredit**: (Kaltmiete × Wohnungen) - Kosten
5. **Kreditrate (monatlich)**: (Kaufpreis × {config['search_criteria']['ltv_prozent']}%) / (30 Jahre × 12) × ({config['search_criteria']['zinssatz_prozent']}% + {config['search_criteria']['tilgung_prozent']}%)
6. **Netto-Cashflow**: Cashflow-vor-Kredit - Kreditrate
7. **Netto-Rendite (auf EK)**: (Netto-Cashflow × 12 / Eigenkapital) × 100
8. **Price-Factor**: Kaufpreis / Jahresmiete ← investmentpunk: < 18 ist gut

**KATEGORIE 1: PROFIT (klassisches Investment)**
- Min. Brutto-Rendite: 6%
- Min. Netto-Cashflow: {config['evaluation_thresholds']['category_profit']['min_cashflow_monatlich']}€
- Suchradius: Ganz Oberhausen (überall)
- Zielgruppe: Selbsttragend, Hebel-Effekt

**KATEGORIE 2: FAMILY (Vermietung an Eltern/Bekannte)**
- Min. Brutto-Rendite: 0% (auch negativ ok!)
- Min. Netto-Cashflow: {config['evaluation_thresholds']['category_family']['min_cashflow_monatlich']}€ (auch -500€ ok)
- PLZ: 46149 ONLY (zentral, wo Familie ist)
- Zielgruppe: Sichere Mieter, emotionales Investment, Vermögensaufbau

**ROTE FLAGGEN (kategorie-spezifisch):**

**PROFIT (6%+ Rendite erforderlich):**
- ❌ Brutto-Rendite < 6% → AUSSCHLUSS (break-even!)
- ❌ Netto-Cashflow < 500€ → AUSSCHLUSS (zu knapp)
- ❌ Renovierungskosten > 50k€ → ⚠️ ROT/AUSSCHLUSS
- ❌ Baujahr < 1950 → ⚠️ ROT (feuchte Keller)
- ❌ C-Lage hohes Leerstand-Risiko → ⚠️ ROT

**FAMILY (auch 0% ok, aber Risiken prüfen):**
- ⚠️ Brutto-Rendite < 3% → Warnung, aber nicht AUSSCHLUSS
- ⚠️ Netto-Cashflow < -500€ → AUSSCHLUSS (zu viel Eigenkapital-Zehrung)
- ⚠️ Renovierungskosten > 75k€ → Warnung (aber verkraftbar)
- ⚠️ Baujahr < 1960 → Warnung (aber Familie kennt es)
- ✅ Bekannte Mieter → BONUS! (sicherer als fremd)

POSITIVE MERKMALE geben +5 Punkte je:
- Garten vorhanden
- Balkon (obere Wohnung)
- Garage/Stellplatz
- Renoviert (letzte 10 Jahre)
- Neue Heizung (letzte 5 Jahre)

SCORING (0-100) — ZWEI KATEGORIEN:

**KATEGORIE 1: PROFIT**
- < 40: ❌ NICHT EMPFOHLEN (< 6% Brutto ODER < 500€ Cashflow)
- 40-60: ⚠️ PRÜFEN (6-7% Brutto, ok Cashflow, Risiken)
- 60-80: ✅ GUT (6-8% Brutto, 600-1000€ Cashflow, B-Lage)
- 80+: 🔥 SEHR GUT (> 8% Brutto, > 1000€ Cashflow, echtes MFH)

**KATEGORIE 2: FAMILY**
- < 30: ❌ NICHT EMPFOHLEN (< -500€ Cashflow, zu viel Zehrung)
- 30-50: ⚠️ WARNUNG (< 3% Brutto, negativ Cashflow aber ok)
- 50-70: ✅ GUT (0-3% Brutto, neutral bis leicht positiv, Familie ok)
- 70+: 🔥 SEHR GUT (> 3% Brutto, positiv Cashflow, beste Lage zentral)

**PROFIT Score-Berechnung:**
- Basis: Brutto-Rendite in % (6-10% = 0-100)
- +10: Brutto > 8%
- +10: Netto-Cashflow > 1000€
- +10: Baujahr > 1970
- +5 pro Feature (Garten, Balkon, Garage, Renoviert)
- -20: Baujahr < 1950
- -15: Renovierungen 30-50k€
- -25: Renovierungen > 50k€

**FAMILY Score-Berechnung:**
- Basis: (Brutto-Rendite + 10) × 5 (um 0% auf 50 Punkte zu machen)
- +10: Zentral 46149
- +10: Baujahr > 1960 (nicht zu alt für Familie)
- +15: Sichere Mieter (Familie bekannt) ← BONUS!
- +5 pro Feature (Garten für Kinder, Garage, etc.)
- -10: Baujahr < 1960 (aber nicht so schlimm wie PROFIT)
- -5: Renovierungen > 30k€

**OUTPUT-FORMAT** (JSON, pro Immobilie — BEIDE Kategorien):
{{
  "adresse": "...",
  "kaufpreis": 12345,
  "wohnungen": 5,
  "baujahr": 1975,

  "cashflow_monatlich": 637,
  "brutto_rendite": 6.2,
  "netto_cashflow": 150,
  "netto_rendite": 8.5,

  "rote_flaggen": ["Baujahr 1975: Wahrscheinlich feuchte Keller", "Renovierung ~15k€"],
  "positive_merkmale": ["Garage", "Garten"],

  "kategorie_profit": {{
    "qualifiziert": true,
    "score": 72,
    "empfehlung": "GUT - 6-8% Brutto, moderate Risiken",
    "prioritaet": 2
  }},

  "kategorie_family": {{
    "qualifiziert": false,
    "score": 45,
    "grund": "Liegt nicht in PLZ 46149 (zentral), eher randlage",
    "empfehlung": "Nicht für Familie (zu weit weg)",
    "prioritaet": null
  }}
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
