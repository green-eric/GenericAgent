import sqlite3

conn = sqlite3.connect(r'D:\Project\QAScorer\quarterly_cache.db')
conn.row_factory = sqlite3.Row

# 看看缓存中所有记录
print("=== quarterly_reports for 300189.SZ ===")
cur = conn.execute('SELECT * FROM quarterly_reports WHERE ts_code=? ORDER BY report_date ASC', ('300189.SZ',))
cols = [d[0] for d in cur.description]
print("Columns: " + str(cols))
for row in cur.fetchall():
    d = dict(row)
    print(str(d))

conn.close()
