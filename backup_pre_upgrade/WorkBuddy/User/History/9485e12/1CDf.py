import sqlite3

# Check the actual structure and parameters
conn = sqlite3.connect('quarterly_cache.db')
cur = conn.execute('PRAGMA table_info(quarterly_reports)')
cols = [r[1] for r in cur.fetchall()]
print(f"Table has {len(cols)} columns: {cols}")

# Check a sample row that was inserted
cur = conn.execute('SELECT * FROM quarterly_reports LIMIT 1')
row = cur.fetchone()
if row:
    print(f"Sample row has {len(row)} fields")
else:
    print("No rows in table")
conn.close()