import sqlite3

for dbname in ["data/portfolio.db", "data/multi_depot.db"]:
    con = sqlite3.connect(dbname)
    cur = con.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cur.fetchall()]
    print(f"\n=== {dbname} ===")
    print("Tabellen:", tables)
    for t in tables:
        cur.execute(f"SELECT COUNT(*) FROM {t}")
        cnt = cur.fetchone()[0]
        print(f"  {t}: {cnt} Zeilen")
        cur.execute(f"SELECT * FROM {t} LIMIT 5")
        cols = [d[0] for d in cur.description]
        print(f"  Spalten: {cols}")
        for r in cur.fetchall():
            print(f"    {r}")
    con.close()
