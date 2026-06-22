"""
Publisher Agent
Uploads approved, produced content to Instagram via the Graph API.
Only runs after all other agents have completed their checks.
"""

import requests
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.video_host import upload_video, delete_video


GRAPH_API_BASE = "https://graph.instagram.com/v21.0"


def upload_reel(
    video_url: str,
    caption: str,
    account: dict,
    cover_url: str = None
) -> dict:
    """
    Upload a Reel to Instagram via the Graph API.
    video_url must be a publicly accessible URL (or use container upload flow).
    account: dict with instagram_user_id and access_token
    """
    user_id = account["instagram_user_id"]
    token = account["access_token"]

    # Step 1: Create media container
    container_params = {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "access_token": token,
    }
    if cover_url:
        container_params["cover_url"] = cover_url

    r = requests.post(
        f"{GRAPH_API_BASE}/{user_id}/media",
        data=container_params
    )
    r.raise_for_status()
    container_id = r.json()["id"]
    print(f"  Container created: {container_id}")

    # Step 2: Wait for processing
    for _ in range(12):  # max 2 minutes
        time.sleep(10)
        status_r = requests.get(
            f"{GRAPH_API_BASE}/{container_id}",
            params={"fields": "status_code", "access_token": token}
        )
        status = status_r.json().get("status_code")
        print(f"  Processing status: {status}")
        if status == "FINISHED":
            break
        if status == "ERROR":
            return {"success": False, "error": "Video processing failed"}

    # Step 3: Publish
    pub_r = requests.post(
        f"{GRAPH_API_BASE}/{user_id}/media_publish",
        data={"creation_id": container_id, "access_token": token}
    )
    pub_r.raise_for_status()
    post_id = pub_r.json()["id"]
    print(f"  Published! Post ID: {post_id}")

    return {"success": True, "post_id": post_id, "container_id": container_id}


def publish_next_approved(account_key: str, account_config: dict) -> bool:
    """Find the next approved+produced post and publish it."""
    queue_file = Path(__file__).parent.parent / "output" / f"publish_queue_{account_key}.json"
    if not queue_file.exists():
        print(f"No publish queue for {account_key}")
        return False

    with open(queue_file) as f:
        queue = json.load(f)

    pending = [p for p in queue if p.get("status") == "ready"]
    if not pending:
        print(f"No posts ready to publish for {account_key}")
        return False

    post = pending[0]
    print(f"\nPublishing for {account_key}: {post.get('title', '?')}")

    # Lokale Videodatei? Dann erst zum kostenlosen Host (GitHub) hochladen.
    video_url = post.get("video_url")
    remote_name = None
    if not video_url and post.get("video_file"):
        remote_name = f"reel_{int(time.time())}.mp4"
        print(f"  Lade Video zum Host hoch: {remote_name}")
        video_url = upload_video(post["video_file"], remote_name)

    try:
        result = upload_reel(
            video_url=video_url,
            caption=post["caption"],
            account=account_config,
        )
    finally:
        if remote_name:
            try:
                delete_video(remote_name)
                print(f"  Host aufgeraeumt: {remote_name} geloescht")
            except RuntimeError as e:
                print(f"  WARNUNG: Aufraeumen fehlgeschlagen: {e}")

    # Update queue
    post["status"] = "published" if result["success"] else "failed"
    post["publish_result"] = result

    with open(queue_file, "w") as f:
        json.dump(queue, f, indent=2)

    return result["success"]


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from config.settings import ACCOUNT

    if not ACCOUNT["access_token"]:
        print("ERROR: No access token. Run check_access.py first (see SETUP.md).")
        exit(1)

    publish_next_approved("main", ACCOUNT)
