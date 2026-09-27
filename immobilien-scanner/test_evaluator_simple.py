"""Regressionstest: Kreditrate und Flaechen-Plausibilisierung im einfachen Evaluator."""

import unittest
from pathlib import Path

import yaml

from evaluator_simple import evaluate_properties_simple

CONFIG = yaml.safe_load((Path(__file__).parent / "config.yaml").read_text(encoding="utf-8"))


def _objekt(**werte) -> dict:
    basis = {"kaufpreis": 500000, "wohnungen": 6, "groesse_qm": 420, "baujahr": 1975,
             "adresse": "46149 Oberhausen", "ist_einzelwohnung": False}
    basis.update(werte)
    return basis


class EvaluatorSimpleTests(unittest.TestCase):
    def test_kreditrate_ist_annuitaet_aus_config(self) -> None:
        p = evaluate_properties_simple([_objekt()], CONFIG)[0]
        k = CONFIG["search_criteria"]
        miete = k["kaltmiete_pro_einheit"] * 6
        kosten = (miete * k["verwaltungsquote_prozent"] / 100 + 420 * k["instandhaltung_euro_pro_qm"]
                  + k["versicherung_monatlich"] + miete * k["leerstand_puffer_prozent"] / 100)
        rate = 500000 * k["ltv_prozent"] / 100 * (k["zinssatz_prozent"] + k["tilgung_prozent"]) / 100 / 12
        self.assertAlmostEqual(p["netto_cashflow"], round(miete - kosten - rate), delta=1)

    def test_unplausible_flaeche_wird_geschaetzt_und_markiert(self) -> None:
        p = evaluate_properties_simple([_objekt(groesse_qm=3)], CONFIG)[0]
        self.assertTrue(any("Wohnflaeche" in f for f in p["rote_flaggen"]))


if __name__ == "__main__":
    unittest.main()
