import sqlite3

conn = sqlite3.connect(r'D:\Project\QAScorer\quarterly_cache.db')
conn.row_factory = sqlite3.Row

# 查看300189的所有季度原始数据
print("=== quarterly_reports ===")
cur = conn.execute('SELECT * FROM quarterly_reports WHERE ts_code=? ORDER BY report_date DESC', ('300189.SZ',))
for row in cur.fetchall():
    d = dict(row)
    print("report_date=" + str(d['report_date'])
          + " | revenue=" + str(d.get('revenue'))
          + " | revenue_yoy=" + str(d.get('revenue_yoy'))
          + " | profit_yoy=" + str(d.get('profit_yoy'))
          + " | net_profit=" + str(d.get('net_profit')))

print("\n=== quarterly_ttm_cache ===")
cur = conn.execute('SELECT * FROM quarterly_ttm_cache WHERE ts_code=?', ('300189.SZ',))
for row in cur.fetchall():
    d = dict(row)
    for k, v in d.items():
        print(k + "=" + str(v))

conn.close()
