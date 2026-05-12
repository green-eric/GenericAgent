import sqlite3
conn = sqlite3.connect(r'D:\Project\AnnualScorer\stock_cache.db')

print("=== stocks 表 ===")
cur = conn.execute('SELECT * FROM stocks LIMIT 5')
cols = [d[0] for d in cur.description]
print(cols)
for r in conn.execute('SELECT * FROM stocks'):
    print(r)

print("\n=== financial_reports 表 ===")
cur = conn.execute('SELECT * FROM financial_reports LIMIT 3')
cols = [d[0] for d in cur.description]
print(cols)
for r in conn.execute('SELECT * FROM financial_reports'):
    print(r)

conn.close()
