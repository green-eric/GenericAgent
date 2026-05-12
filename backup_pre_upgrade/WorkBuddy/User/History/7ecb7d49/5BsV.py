import sqlite3

conn = sqlite3.connect(r'D:\Project\QAScorer\quarterly_cache.db')
conn.row_factory = sqlite3.Row

# 看看300189在quarterly_reports中的所有字段
cur = conn.execute('SELECT * FROM quarterly_reports WHERE ts_code=? ORDER BY report_date ASC', ('300189.SZ',))
for row in cur.fetchall():
    d = dict(row)
    print("--- report_date=" + str(d['report_date']) + " ---")
    for k, v in d.items():
        if v is not None and k not in ('ts_code',):
            print("  " + k + "=" + str(v))

conn.close()
