"""
Test-Daten für Pipeline-Verifikation (ohne echte Scraper)
"""

test_properties = [
    {
        "adresse": "Musterstraße 42, 46149 Oberhausen",
        "kaufpreis": 450000,
        "wohnungen": 4,
        "baujahr": 1985,
        "groesse_qm": 320,
        "energieklasse": "D",
        "renovierungen": "Bad 2020",
        "merkmal_garten": True,
        "merkmal_balkon": True,
        "merkmal_garage": 2,
        "quelle": "Test-Mock",
        "link": "https://example.com/test1"
    },
    {
        "adresse": "Königstraße 100, 46149 Oberhausen",
        "kaufpreis": 320000,
        "wohnungen": 2,
        "baujahr": 1995,
        "groesse_qm": 180,
        "energieklasse": "C",
        "renovierungen": "Fassade 2019",
        "merkmal_garten": True,
        "merkmal_balkon": False,
        "merkmal_garage": 1,
        "quelle": "Test-Mock",
        "link": "https://example.com/test2"
    },
    {
        "adresse": "Sterkrader Str. 150, 46145 Oberhausen",
        "kaufpreis": 550000,
        "wohnungen": 6,
        "baujahr": 1978,
        "groesse_qm": 420,
        "energieklasse": "E",
        "renovierungen": "Keine",
        "merkmal_garten": False,
        "merkmal_balkon": True,
        "merkmal_garage": 0,
        "quelle": "Test-Mock",
        "link": "https://example.com/test3"
    },
]

if __name__ == "__main__":
    import json
    print(json.dumps(test_properties, indent=2, ensure_ascii=False))
