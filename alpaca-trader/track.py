# -*- coding: utf-8 -*-
"""
Beobachtungs-Modus (Shadow-Tracking) fuer das 5-Segmente-Experiment.
KEINE Orders. Friert beim ersten Lauf die Einstiegspreise ein und verfolgt
danach die Wertentwicklung je Segment und je Wert.

AUFRUF:
  python track.py          -> Stand anzeigen + in Historie schreiben
  python track.py --reset  -> Startpunkt neu setzen (Vorsicht: loescht Baseline)

Dateien:
  baseline.json   -> eingefrorener Startpunkt (Datum, Stueckzahl, Einstiegspreis)
  history.csv     -> eine Zeile pro Lauf: Datum + Wert je Segment
"""
import os
import sys
import json
import csv
from datetime import datetime
import requests
from dotenv import load_dotenv
from segments import SEGMENTS, SEGMENT_CAPITAL

HERE = os.path.dirname(__file__)
load_dotenv(os.path.join(HERE, ".env"))

KEY = os.getenv("ALPACA_API_KEY", "")
SECRET = os.getenv("ALPACA_SECRET_KEY", "")
DATA = "https://data.alpaca.markets"
HEADERS = {"APCA-API-KEY-ID": KEY, "APCA-API-SECRET-KEY": SECRET}

BASELINE = os.path.join(HERE, "baseline.json")
HISTORY = os.path.join(HERE, "history.csv")


def get_price(ticker):
    r = requests.get(f"{DATA}/v2/stocks/{ticker}/trades/latest",
                     headers=HEADERS, params={"feed": "iex"}, timeout=15)
    if r.status_code == 200:
        return float(r.json()["trade"]["p"])
    return None


def build_baseline():
    """Friert Stueckzahl + Einstiegspreis von heute ein."""
    print("Setze Startpunkt (Baseline) mit den heutigen Kursen ...")
    data = {"erstellt": datetime.now().isoformat(timespec="seconds"), "segmente": {}}
    for seg_id, seg in SEGMENTS.items():
        pro_ticker = SEGMENT_CAPITAL / len(seg["tickers"])
        positionen = {}
        for t in seg["tickers"]:
            preis = get_price(t)
            if preis is None:
                print(f"  WARNUNG: kein Preis fuer {t}, uebersprungen")
                continue
            qty = int(pro_ticker // preis)
            positionen[t] = {"stueck": qty, "einstieg": round(preis, 2)}
        data["segmente"][seg_id] = {"name": seg["name"], "positionen": positionen}
    with open(BASELINE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Baseline gespeichert: {BASELINE}\n")
    return data


def load_baseline():
    with open(BASELINE, encoding="utf-8") as f:
        return json.load(f)


def report(baseline):
    print("=" * 64)
    print(f"  BEOBACHTUNG  --  Start: {baseline['erstellt'][:10]}  --  heute: {datetime.now():%Y-%m-%d %H:%M}")
    print("=" * 64)

    seg_werte = {}
    seg_start = {}
    bewegungen = []  # (segment, ticker, pct) fuer Erfolgs-/Misserfolgsanalyse

    for seg_id, seg in baseline["segmente"].items():
        start_val = 0.0
        now_val = 0.0
        print(f"\n[{seg_id}] {seg['name']}")
        print("  " + "-" * 56)
        for t, pos in seg["positionen"].items():
            qty, einstieg = pos["stueck"], pos["einstieg"]
            jetzt = get_price(t)
            if jetzt is None:
                print(f"  {t:6s}  kein aktueller Preis")
                continue
            s_val = qty * einstieg
            n_val = qty * jetzt
            start_val += s_val
            now_val += n_val
            pct = (jetzt / einstieg - 1) * 100
            bewegungen.append((seg["name"], t, pct))
            pfeil = "+" if pct >= 0 else ""
            print(f"  {t:6s}  {einstieg:8.2f} -> {jetzt:8.2f}   {pfeil}{pct:6.2f}%   ({qty} St.)")
        seg_start[seg_id] = start_val
        seg_werte[seg_id] = now_val
        seg_pct = (now_val / start_val - 1) * 100 if start_val else 0
        pfeil = "+" if seg_pct >= 0 else ""
        print(f"  => Segment: {start_val:10,.0f} -> {now_val:10,.0f} USD   {pfeil}{seg_pct:6.2f}%")

    # Rangliste
    print("\n" + "=" * 64)
    print("  RANGLISTE (beste -> schlechteste)")
    print("  " + "-" * 56)
    rang = sorted(seg_werte.items(),
                  key=lambda kv: (kv[1] / seg_start[kv[0]] - 1) if seg_start[kv[0]] else 0,
                  reverse=True)
    for i, (seg_id, val) in enumerate(rang, 1):
        pct = (val / seg_start[seg_id] - 1) * 100 if seg_start[seg_id] else 0
        name = baseline["segmente"][seg_id]["name"]
        print(f"  {i}. {name:42s} {pct:+6.2f}%")

    # Erfolgs-/Misserfolgsfaktoren: Top- und Flop-Einzelwerte
    if bewegungen:
        bewegungen.sort(key=lambda x: x[2], reverse=True)
        print("\n  TREIBER (beste 3 Einzelwerte):")
        for name, t, pct in bewegungen[:3]:
            print(f"    + {t:6s} {pct:+6.2f}%   ({name})")
        print("  BREMSER (schlechteste 3 Einzelwerte):")
        for name, t, pct in bewegungen[-3:][::-1]:
            print(f"    - {t:6s} {pct:+6.2f}%   ({name})")

    gesamt_start = sum(seg_start.values())
    gesamt_now = sum(seg_werte.values())
    gesamt_pct = (gesamt_now / gesamt_start - 1) * 100 if gesamt_start else 0
    print("\n" + "=" * 64)
    print(f"  GESAMT: {gesamt_start:,.0f} -> {gesamt_now:,.0f} USD   {gesamt_pct:+.2f}%")
    print("=" * 64)

    # Historie fortschreiben
    write_history(seg_werte, gesamt_now)
    return seg_werte


def write_history(seg_werte, gesamt):
    neu = not os.path.exists(HISTORY)
    with open(HISTORY, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if neu:
            w.writerow(["datum"] + list(seg_werte.keys()) + ["gesamt"])
        w.writerow([datetime.now().strftime("%Y-%m-%d %H:%M")]
                   + [round(v, 2) for v in seg_werte.values()] + [round(gesamt, 2)])
    print(f"\n  (Stand in Historie geschrieben: {os.path.basename(HISTORY)})")


def main():
    if "--reset" in sys.argv and os.path.exists(BASELINE):
        os.remove(BASELINE)
        print("Baseline zurueckgesetzt.\n")
    baseline = build_baseline() if not os.path.exists(BASELINE) else load_baseline()
    report(baseline)


if __name__ == "__main__":
    main()
