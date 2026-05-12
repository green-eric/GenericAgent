import sqlite3
conn = sqlite3.connect(r'D:\Project\QAScorer\quarterly_cache.db')

# 查表结构
cur = conn.execute("PRAGMA table_info(quarterly_reports)")
print('=== quarterly_reports columns ===')
for r in cur.fetchall():
    print(r)

print()
cur2 = conn.execute("PRAGMA table_info(quarterly_ttm_cache)")
print('=== quarterly_ttm_cache columns ===')
for r in cur2.fetchall():
    print(r)

print()
# 查300189的数据
cur3 = conn.execute("SELECT * FROM quarterly_reports WHERE ts_code='300189.SZ' ORDER BY report_date DESC")
rows = cur3.fetchall()
print(f'=== 300189 reports: {len(rows)} rows ===')
for r in rows:
    print(r)
    print()

conn.close()
