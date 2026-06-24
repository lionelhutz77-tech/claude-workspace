import sqlite3, sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

con = sqlite3.connect("data/learnings.db")
cur = con.cursor()

# Spalten ermitteln
cur.execute("PRAGMA table_info(system_lehren)")
cols = [r[1] for r in cur.fetchall()]
print("Spalten system_lehren:", cols)

cur.execute("SELECT * FROM system_lehren ORDER BY rowid DESC LIMIT 20")
rows = cur.fetchall()
print(f"\nSystem-Lehren ({len(rows)} Eintraege):")
for r in rows:
    row = dict(zip(cols, r))
    aktiv = row.get("aktiv", 1)
    marker = "AKTIV" if aktiv else "---"
    lektion = row.get("lektion", row.get("beschreibung", str(r)))[:90]
    print(f"  [{marker}] {lektion}")

con.close()
