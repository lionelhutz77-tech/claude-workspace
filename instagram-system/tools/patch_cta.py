# -*- coding: utf-8 -*-
"""Stellt die vollstaendige (zweizeilige) CTA-Frage in bereits gebauten Specs
wieder her. Beruehrt KEINE raw-Bilder. Nutzt das gefixte _normalize."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.theme_generator import _normalize

FRAGEN = {
    "item_06": ["Wann hast du zuletzt", "Nachsicht gezeigt statt gemeckert?"],
    "item_08": ["Wann hast du zuletzt", "einfach spontan geklingelt?"],
    "item_09": ["Wann hast du dein Kind zuletzt", "einfach losziehen lassen?"],
    "item_10": ["Wann hast du zuletzt", "etwas aus dem Nichts erfunden?"],
    "item_11": ["Wann hast du ein Album zuletzt", "ganz durchgehört?"],
    "item_12": ["Wann hast du zuletzt etwas erlebt,", "ohne es zu filmen?"],
    "item_13": ["Wann hast du zuletzt", "deinen Nachbarn gegrüßt?"],
    "item_14": ["Wann hast du dein Handy zuletzt", "einfach weggelegt?"],
}

for item, frage in FRAGEN.items():
    p = Path("output/queue") / item / "spec.json"
    if not p.exists():
        print(f"{item}: keine spec.json - uebersprungen")
        continue
    spec = json.load(open(p, encoding="utf-8"))
    spec["cta"]["zeilen"] = frage + ["", "Platzhalter"]  # _normalize ergaenzt Tail
    _normalize(spec)
    json.dump(spec, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"{item}: CTA -> {spec['cta']['zeilen'][:2]}")
