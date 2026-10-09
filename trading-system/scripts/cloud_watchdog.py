"""Prueft, ob die Trading-Cloudlaeufe aktuell und erfolgreich sind.

Der Watchdog laeuft selbst in GitHub Actions. Er veraendert keine Handelsdaten und
gibt keine Secrets aus. Ein Fehlercode signalisiert dem Workflow, eine Telegram-
Warnung zu senden.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class WorkflowCheck:
    label: str
    workflow: str
    max_age_hours: float
    max_runtime_hours: float


CHECKS = (
    WorkflowCheck("Markt-News-Digest", "news_digest.yml", 30.0, 1.0),
    WorkflowCheck("Trading-Tagesanalyse", "daily_trading.yml", 30.0, 3.0),
    WorkflowCheck("Sonntags-Review", "weekly_review.yml", 180.0, 2.0),
    WorkflowCheck("Alpaca-Wochenbericht", "alpaca_weekly.yml", 180.0, 1.0),
)


def _zeitpunkt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def bewerte_laeufe(
    runs: list[dict[str, Any]],
    check: WorkflowCheck,
    jetzt: datetime,
) -> tuple[bool, str]:
    """Bewertet den neuesten geplanten oder manuellen Lauf fail-closed."""
    relevante = [
        run for run in runs
        if run.get("event") in {"schedule", "workflow_dispatch"} and run.get("created_at")
    ]
    if not relevante:
        return False, f"{check.label}: kein Cloud-Lauf gefunden"

    letzter = max(relevante, key=lambda run: _zeitpunkt(str(run["created_at"])))
    gestartet = _zeitpunkt(str(letzter["created_at"]))
    alter_stunden = max(0.0, (jetzt - gestartet).total_seconds() / 3600.0)
    status = str(letzter.get("status") or "unbekannt")
    conclusion = str(letzter.get("conclusion") or "")
    url = str(letzter.get("html_url") or "")

    if alter_stunden > check.max_age_hours:
        return False, (
            f"{check.label}: letzter Lauf ist {alter_stunden:.1f} h alt "
            f"(Grenze {check.max_age_hours:.0f} h) {url}"
        )

    if status in {"queued", "in_progress", "waiting", "requested", "pending"}:
        if alter_stunden > check.max_runtime_hours:
            return False, (
                f"{check.label}: Lauf haengt seit {alter_stunden:.1f} h "
                f"(Grenze {check.max_runtime_hours:.0f} h) {url}"
            )
        return True, f"{check.label}: laeuft seit {alter_stunden:.1f} h"

    if status != "completed" or conclusion != "success":
        return False, (
            f"{check.label}: letzter Lauf {status}/{conclusion or 'ohne Ergebnis'} {url}"
        )

    return True, f"{check.label}: OK, letzter Erfolg vor {alter_stunden:.1f} h"


def _hole_laeufe(repository: str, workflow: str, token: str) -> list[dict[str, Any]]:
    workflow_id = urllib.parse.quote(workflow, safe="")
    url = (
        f"https://api.github.com/repos/{repository}/actions/workflows/"
        f"{workflow_id}/runs?per_page=20"
    )
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "lionel-trading-cloud-watchdog",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = json.load(response)
    return list(payload.get("workflow_runs") or [])


def main() -> int:
    repository = os.environ.get("GITHUB_REPOSITORY", "").strip()
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not repository or not token:
        print("WATCHDOG FEHLER: GitHub-Konfiguration fehlt.")
        return 2

    jetzt = datetime.now(timezone.utc)
    probleme: list[str] = []
    for check in CHECKS:
        try:
            runs = _hole_laeufe(repository, check.workflow, token)
            gesund, meldung = bewerte_laeufe(runs, check, jetzt)
        except (OSError, ValueError, urllib.error.URLError) as exc:
            gesund = False
            meldung = f"{check.label}: Statusabfrage fehlgeschlagen ({type(exc).__name__})"
        print(meldung)
        if not gesund:
            probleme.append(meldung)

    if probleme:
        print("WATCHDOG ALARM: Mindestens ein Cloud-Ablauf ist nicht gesund.")
        return 1
    print("WATCHDOG OK: Alle Trading-Cloud-Ablaufe sind aktuell und erfolgreich.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
