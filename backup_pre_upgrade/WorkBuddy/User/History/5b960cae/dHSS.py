import sqlite3
conn = sqlite3.connect(r'D:\Project\AnnualScorer\stock_cache.db')
cur = conn.execute('SELECT ts_code, name, industry_l1, industry_l2 FROM stocks')
for r in cur.fetchall():
    print(r)
conn.close()
