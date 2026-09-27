"""Holt den aktuellen Depot-/Lernstand aus der Cloud (GitHub, Branch master) auf den PC.

Seit 27.09.2026 rechnet das Trading-System ausschliesslich in GitHub Actions.
Die Cloud committet ihre Datenbanken nach jedem Lauf; dieses Skript kopiert sie
in den lokalen data/-Ordner, damit Dashboard und Auswertungen denselben Stand zeigen.
Lokale Laeufe sind deaktiviert, damit es keine zwei getrennten Depots mehr gibt.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
REPO = HIER.parent
DATEIEN = [
    "data/learnings.db",
    "data/market_memory.db",
    "data/multi_depot.db",
    "data/portfolio.db",
    "data/current-cycle.json",
    "output/dashboard_aktuell.html",
]


def hole_cloud_daten() -> bool:
    try:
        subprocess.run(["git", "-C", str(REPO), "fetch", "-q", "origin", "master"],
                       check=True, timeout=60)
    except (subprocess.SubprocessError, OSError) as exc:
        print(f"  Cloud-Stand nicht abrufbar ({exc}); lokaler Stand bleibt.")
        return False
    for rel in DATEIEN:
        pfad = f"origin/master:trading-system/{rel}"
        ergebnis = subprocess.run(["git", "-C", str(REPO), "show", pfad], capture_output=True, timeout=60)
        if ergebnis.returncode != 0:
            print(f"  {rel}: nicht in der Cloud vorhanden, uebersprungen.")
            continue
        ziel = HIER / rel
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_bytes(ergebnis.stdout)
    print("  Cloud-Stand geladen.")
    return True


if __name__ == "__main__":
    ok = hole_cloud_daten()
    if "--oeffnen" in sys.argv:
        dashboard = HIER / "output" / "dashboard_aktuell.html"
        if dashboard.exists():
            import webbrowser
            webbrowser.open(dashboard.as_uri())
    sys.exit(0 if ok else 1)
