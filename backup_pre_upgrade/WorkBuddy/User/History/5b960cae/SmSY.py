import sqlite3
conn = sqlite3.connect("stock_cache.db")
cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cursor.fetchall()]
print("Tables:", tables)
for t in tables:
    cols = conn.execute(f"PRAGMA table_info({t})").fetchall()
    print(f"\n{t}:")
    for c in cols:
        print(f"  {c[1]} ({c[2]})")
conn.close()
