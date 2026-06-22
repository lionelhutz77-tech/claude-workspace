"""
Video-Host
Lädt Videos in das öffentliche GitHub-Repo `ig-media` hoch (kostenloser
Zwischenspeicher) und liefert die öffentliche URL, die die Instagram-API
zum Abholen braucht. Nach erfolgreichem Posten wird die Datei wieder gelöscht.

Voraussetzung: GitHub CLI (`gh`) ist eingeloggt.
Limit: max. ~100 MB pro Datei (GitHub-Grenze) — Reels liegen weit darunter.

Verifiziert am 2026-06-11: Instagram akzeptiert raw.githubusercontent.com-URLs
(Test via tools/check_video_url.py, Container-Status FINISHED).
"""

import base64
import json
import subprocess
import tempfile
from pathlib import Path

REPO = "lionelhutz77-tech/ig-media"
BRANCH = "main"


def _gh_api(*args: str, input_file: str = None) -> dict:
    cmd = ["gh", "api"] + list(args)
    if input_file:
        cmd += ["--input", input_file]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        raise RuntimeError(f"gh api fehlgeschlagen: {result.stderr.strip()}")
    return json.loads(result.stdout) if result.stdout.strip() else {}


def upload_video(local_path: str, remote_name: str = None) -> str:
    """Lädt ein Video hoch und gibt die öffentliche URL zurück."""
    path = Path(local_path)
    if not path.exists():
        raise FileNotFoundError(local_path)
    remote_name = remote_name or path.name

    payload = {
        "message": f"Upload {remote_name}",
        "content": base64.b64encode(path.read_bytes()).decode("ascii"),
        "branch": BRANCH,
    }
    with tempfile.NamedTemporaryFile(
        "w", suffix=".json", delete=False, encoding="ascii"
    ) as f:
        json.dump(payload, f)
        tmp = f.name
    try:
        _gh_api("-X", "PUT", f"repos/{REPO}/contents/{remote_name}", input_file=tmp)
    finally:
        Path(tmp).unlink(missing_ok=True)

    return f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/{remote_name}"


def delete_video(remote_name: str):
    """Löscht eine zuvor hochgeladene Datei (Aufräumen nach dem Posten)."""
    info = _gh_api(f"repos/{REPO}/contents/{remote_name}?ref={BRANCH}")
    payload = {
        "message": f"Aufraeumen: {remote_name}",
        "sha": info["sha"],
        "branch": BRANCH,
    }
    with tempfile.NamedTemporaryFile(
        "w", suffix=".json", delete=False, encoding="ascii"
    ) as f:
        json.dump(payload, f)
        tmp = f.name
    try:
        _gh_api("-X", "DELETE", f"repos/{REPO}/contents/{remote_name}", input_file=tmp)
    finally:
        Path(tmp).unlink(missing_ok=True)


if __name__ == "__main__":
    # Selbsttest: hochladen, URL prüfen, wieder löschen
    import sys
    import urllib.request

    if len(sys.argv) < 2:
        print("Aufruf: python tools/video_host.py <lokale_videodatei>")
        sys.exit(1)

    url = upload_video(sys.argv[1], "selftest.mp4")
    print(f"Hochgeladen: {url}")
    with urllib.request.urlopen(url) as r:
        print(f"Abrufbar: HTTP {r.status}, {r.headers['Content-Length']} Bytes")
    delete_video("selftest.mp4")
    print("Wieder geloescht — Selbsttest OK.")
