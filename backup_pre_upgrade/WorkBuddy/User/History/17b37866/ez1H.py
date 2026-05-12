import sqlite3
conn = sqlite3.connect(r'D:\Project\AnnualScorer\stock_cache.db')
cur = conn.execute('SELECT sql FROM sqlite_master WHERE type="table"')
for row in cur.fetchall():
    print(row[0])
print("---")
cur = conn.execute('SELECT * FROM financial_reports LIMIT 3')
for row in cur.fetchall():
    print(row)
conn.close()
