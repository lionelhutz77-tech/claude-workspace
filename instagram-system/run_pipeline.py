# -*- coding: utf-8 -*-
"""
Main pipeline runner.

Usage:
  python run_pipeline.py --step all         # Komplette Pipeline
  python run_pipeline.py --step research    # Nur Nischenrecherche
  python run_pipeline.py --step ideate      # Nur Content-Ideen
  python run_pipeline.py --step compliance  # Nur Compliance-Check
  python run_pipeline.py --step publish     # Status anzeigen
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from tools.gemini_client import get_client
from agents.niche_researcher import research_niches, select_best_niche
from agents.content_ideator import generate_content_briefs
from agents.compliance_checker import check_all_briefs


def step_research(client):
    print("\n[1/4] NISCHENRECHERCHE")
    print("-" * 40)
    niches = research_niches(client, num_niches=3)
    print(f"Gefunden: {len(niches)} Nischen-Kandidaten.")
    selection = select_best_niche(client, niches)

    out = Path("output/niche_selection.json")
    out.parent.mkdir(exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(selection, f, indent=2, ensure_ascii=False)

    name = selection.get("account_niche", {}).get("niche_name", "?")
    print(f"Ausgewaehlte Nische -> {name}")
    return selection


def step_ideate(client, selection=None):
    print("\n[2/4] CONTENT-IDEEN")
    print("-" * 40)
    if selection is None:
        with open("output/niche_selection.json", encoding="utf-8") as f:
            selection = json.load(f)
    niche = selection.get("account_niche", {})
    print(f"Erstelle Briefs für: {niche.get('niche_name', '')}...")
    briefs = generate_content_briefs(client, niche, num_briefs=7)
    out = Path("output/briefs.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(briefs, f, indent=2, ensure_ascii=False)
    print(f"  {len(briefs)} Briefs gespeichert.")


def step_compliance(client):
    print("\n[3/4] COMPLIANCE-CHECK")
    print("-" * 40)
    briefs_file = Path("output/briefs.json")
    if not briefs_file.exists():
        print("  Zuerst --step ideate ausführen.")
        return
    with open(briefs_file, encoding="utf-8") as f:
        briefs = json.load(f)
    approved, rejected = check_all_briefs(client, briefs)
    with open("output/approved.json", "w", encoding="utf-8") as f:
        json.dump(approved, f, indent=2, ensure_ascii=False)
    with open("output/rejected.json", "w", encoding="utf-8") as f:
        json.dump(rejected, f, indent=2, ensure_ascii=False)


def step_publish():
    print("\n[4/4] VERÖFFENTLICHEN")
    print("-" * 40)
    approved_file = Path("output/approved.json")
    if not approved_file.exists():
        print("  Zuerst --step compliance ausführen.")
        return
    with open(approved_file, encoding="utf-8") as f:
        approved = json.load(f)
    print(f"  {len(approved)} Posts bereit zum Veröffentlichen.")
    print("  -> Instagram-Zugangsdaten in config/settings.py eintragen, dann publisher.py starten.")


def main():
    parser = argparse.ArgumentParser(description="Instagram AI Pipeline")
    parser.add_argument("--step", default="all",
                        choices=["all", "research", "ideate", "compliance", "publish"])
    args = parser.parse_args()

    client = get_client()

    if args.step == "all":
        selection = step_research(client)
        step_ideate(client, selection)
        step_compliance(client)
        step_publish()
    elif args.step == "research":
        step_research(client)
    elif args.step == "ideate":
        step_ideate(client)
    elif args.step == "compliance":
        step_compliance(client)
    elif args.step == "publish":
        step_publish()

    print("\nFertig.")


if __name__ == "__main__":
    main()
