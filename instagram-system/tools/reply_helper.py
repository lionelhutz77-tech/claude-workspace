# -*- coding: utf-8 -*-
"""
Antwort-Assistent fuer Kommentare @kiai1977.

Entwirft warme, persoenliche Antworten in deinem Stil (du-Form, danken,
gezielt eingehen, bestaerken). Du gibst frei und postest – KEINE Voll-Automatik
(Authentizitaet + Schutz vor Spam-Erkennung).

  python -m tools.reply_helper                      # Entwuerfe fuer alle offenen Kommentare (API)
  python -m tools.reply_helper --text "..." [user]  # Entwurf fuer einen reinkopierten Kommentar
  python -m tools.reply_helper --post <comment_id> "Antworttext"   # freigegebene Antwort posten
"""

import re
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.gemini_client import get_client, generate_with_retry
from tools.read_comments import account, latest_media_id, read_comments

API = "https://graph.instagram.com/v21.0"
STIL = Path("vorlagen/antwort_stil.txt")

PROMPT = """Du formulierst eine Antwort auf einen Instagram-Kommentar fuer den
Account @kiai1977 ("Frueher & Heute"). Halte dich GENAU an diesen Stil:

{stil}

Kommentar von @{user}:
"{text}"

Schreibe NUR die Antwort (deutsch, du-Form, 1-3 Saetze), nichts weiter.
Verwende KORREKTE deutsche Umlaute (ä, ö, ü, ß) – niemals ae/oe/ue/ss."""


def draft_reply(text, username="jemand"):
    stil = STIL.read_text(encoding="utf-8") if STIL.exists() else ""
    client = get_client()
    prompt = PROMPT.format(stil=stil, user=username, text=text)
    return generate_with_retry(client, prompt).strip().strip('"')


def post_reply(comment_id, message):
    _, tok = account()
    r = requests.post(f"{API}/{comment_id}/replies",
                      data={"message": message, "access_token": tok}, timeout=30)
    r.raise_for_status()
    return r.json()


def drafts_from_api():
    uid, tok = account()
    mid = latest_media_id(uid, tok)
    data = read_comments(mid, tok)
    comments = data.get("data", [])
    if not comments:
        print("Hinweis: API liefert aktuell keine Kommentare aus.")
        print("Nutze stattdessen:  python -m tools.reply_helper --text \"<Kommentar>\" <username>")
        return
    for c in comments:
        # nur Kommentare ohne eigene Antwort
        replies = c.get("replies", {}).get("data", [])
        if any(r.get("username") == "kiai1977" for r in replies):
            continue
        entwurf = draft_reply(c.get("text", ""), c.get("username", "jemand"))
        print(f"\n[{c.get('username')}] {c.get('text')}")
        print(f"  ENTWURF: {entwurf}")
        print(f"  -> Posten mit: python -m tools.reply_helper --post {c['id']} \"{entwurf}\"")


def main():
    args = sys.argv[1:]
    if args and args[0] == "--post":
        print(post_reply(args[1], args[2]))
    elif args and args[0] == "--text":
        text = args[1]
        user = args[2] if len(args) > 2 else "jemand"
        print("ENTWURF:", draft_reply(text, user))
    else:
        drafts_from_api()


if __name__ == "__main__":
    main()
