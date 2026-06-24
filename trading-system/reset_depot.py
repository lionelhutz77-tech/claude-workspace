"""
Musterdepot-Reset — setzt beide DBs auf Startkapital zurück.
Learnings bleiben erhalten (werden im nächsten Lauf angewendet).
"""
import sqlite3
import sys
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

STARTKAPITAL = 1000.0
MULTI_STARTKAPITAL = 1000.0  # je Strategie

def reset_portfolio():
    con = sqlite3.connect("data/portfolio.db")
    cur = con.cursor()

    # offene Positionen: erst anzeigen
    cur.execute("SELECT asset, investiert_eur, status FROM positionen WHERE status='offen'")
    offen = cur.fetchall()
    if offen:
        print(f"  Offene Positionen werden geschlossen: {[r[0] for r in offen]}")

    # Alles löschen und neu starten
    cur.execute("DELETE FROM positionen")
    cur.execute("DELETE FROM depot_verlauf")
    cur.execute("DELETE FROM sqlite_sequence WHERE name='positionen'")

    # Cash und Startdatum zurücksetzen
    cur.execute("UPDATE depot_config SET wert=? WHERE schluessel='cash'", (str(STARTKAPITAL),))
    cur.execute("UPDATE depot_config SET wert=? WHERE schluessel='startkapital'", (str(STARTKAPITAL),))
    cur.execute("UPDATE depot_config SET wert=? WHERE schluessel='erstellt_am'",
                (datetime.now().strftime("%Y-%m-%d"),))

    # Erster Verlaufs-Eintrag
    cur.execute(
        "INSERT INTO depot_verlauf (datum, depotwert, cash, positionen, tagesrendite) VALUES (?,?,?,?,?)",
        (datetime.now().strftime("%Y-%m-%d"), STARTKAPITAL, STARTKAPITAL, 0, 0.0)
    )

    con.commit()
    con.close()
    print(f"  portfolio.db zurückgesetzt → Cash: {STARTKAPITAL:.2f} EUR")


def reset_multi_depot():
    con = sqlite3.connect("data/multi_depot.db")
    cur = con.cursor()

    cur.execute("SELECT strategie FROM depots")
    strategien = [r[0] for r in cur.fetchall()]

    cur.execute("DELETE FROM positionen")
    cur.execute("DELETE FROM verlauf")
    cur.execute("DELETE FROM sqlite_sequence WHERE name='positionen'")

    for strat in strategien:
        cur.execute("UPDATE depots SET cash=? WHERE strategie=?", (MULTI_STARTKAPITAL, strat))
        # Startdatum aktualisieren
        cur.execute("UPDATE depots SET erstellt_am=? WHERE strategie=?",
                    (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), strat))

    # Erste Verlaufs-Einträge
    heute = datetime.now().strftime("%Y-%m-%d")
    for strat in strategien:
        cur.execute(
            "INSERT INTO verlauf (datum, strategie, depotwert, pnl_eur, pnl_pct) VALUES (?,?,?,?,?)",
            (heute, strat, MULTI_STARTKAPITAL, 0.0, 0.0)
        )

    con.commit()
    con.close()
    print(f"  multi_depot.db zurückgesetzt → je Strategie {MULTI_STARTKAPITAL:.2f} EUR ({len(strategien)} Strategien)")


def zeige_learnings():
    con = sqlite3.connect("data/learnings.db")
    cur = con.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cur.fetchall()]
    total = 0
    for t in tables:
        cur.execute(f"SELECT COUNT(*) FROM {t}")
        cnt = cur.fetchone()[0]
        total += cnt
        if cnt > 0:
            print(f"  learnings.db / {t}: {cnt} Einträge (bleiben erhalten)")
    con.close()
    return total


if __name__ == "__main__":
    print("=" * 55)
    print("MUSTERDEPOT-RESET")
    print(f"Datum: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    print("=" * 55)

    print("\n[1] Learnings prüfen (werden NICHT gelöscht):")
    n = zeige_learnings()
    if n == 0:
        print("  Noch keine Learnings gespeichert.")

    print("\n[2] portfolio.db:")
    reset_portfolio()

    print("\n[3] multi_depot.db:")
    reset_multi_depot()

    print("\n" + "=" * 55)
    print("Reset abgeschlossen.")
    print(f"Startkapital je Depot:   {STARTKAPITAL:.2f} EUR")
    print(f"Startkapital Multi-Depot: {MULTI_STARTKAPITAL:.2f} EUR je Strategie")
    print("\nNächster Lauf wendet alle gespeicherten Learnings an.")
    print("=" * 55)
