import sqlite3, os
db_path = r'D:\Project\QAScorer\quarterly_cache.db'
conn = sqlite3.connect(db_path)

print('=== quarterly_reports for 300189.SZ ===')
cur = conn.execute("SELECT ts_code, report_date, report_type, LENGTH(block_text) FROM quarterly_reports WHERE ts_code='300189.SZ' ORDER BY report_date DESC")
for r in cur.fetchall():
    print(r)

print()
print('=== quarterly_ttm_cache for 300189.SZ ===')
cur2 = conn.execute("SELECT * FROM quarterly_ttm_cache WHERE ts_code='300189.SZ'")
cols = [d[0] for d in cur2.description]
print(cols)
for r in cur2.fetchall():
    print(r)

conn.close()
