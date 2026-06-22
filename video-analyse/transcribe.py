import os, glob, json, sys
import requests
from dotenv import load_dotenv

# Groq-Key aus bestehendem Projekt laden (nicht ausgeben)
load_dotenv(r"C:\Users\HP\Documents\Claude\trading-system\.env")
KEY = os.getenv("GROQ_API_KEY")
if not KEY:
    sys.exit("GROQ_API_KEY nicht gefunden")

BASE = r"C:\Users\HP\Documents\Claude\video-analyse"
URL = "https://api.groq.com/openai/v1/audio/transcriptions"
SEG = 600  # 10-Min-Stücke -> globaler Zeit-Offset

chunks = sorted(glob.glob(os.path.join(BASE, "audio", "chunk_*.mp3")))
all_segments = []
full_text_parts = []

def hhmmss(s):
    s = int(s); return f"{s//3600:02d}:{(s%3600)//60:02d}:{s%60:02d}"

for i, path in enumerate(chunks):
    offset = i * SEG
    print(f"Transkribiere {os.path.basename(path)} (Offset {hhmmss(offset)}) ...", flush=True)
    with open(path, "rb") as f:
        r = requests.post(
            URL,
            headers={"Authorization": f"Bearer {KEY}"},
            files={"file": (os.path.basename(path), f, "audio/mpeg")},
            data={"model": "whisper-large-v3", "response_format": "verbose_json"},
            timeout=300,
        )
    if r.status_code != 200:
        print(f"  FEHLER {r.status_code}: {r.text[:300]}", flush=True)
        continue
    j = r.json()
    full_text_parts.append(j.get("text", "").strip())
    for seg in j.get("segments", []):
        seg["start"] += offset; seg["end"] += offset
        all_segments.append(seg)
    print(f"  ok ({len(j.get('segments', []))} Segmente)", flush=True)

# Volltext speichern
with open(os.path.join(BASE, "transcript.txt"), "w", encoding="utf-8") as f:
    f.write("\n\n".join(full_text_parts))

# Zeitgestempeltes Transkript
with open(os.path.join(BASE, "transcript_timed.txt"), "w", encoding="utf-8") as f:
    for seg in all_segments:
        f.write(f"[{hhmmss(seg['start'])}] {seg['text'].strip()}\n")

json.dump(all_segments, open(os.path.join(BASE, "transcript_full.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

words = sum(len(p.split()) for p in full_text_parts)
print(f"\nFERTIG: {len(all_segments)} Segmente, ~{words} Wörter.")
print("Dateien: transcript.txt, transcript_timed.txt, transcript_full.json")
