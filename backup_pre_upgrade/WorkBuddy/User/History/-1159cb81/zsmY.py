import sqlite3, os
db_path = r'D:\Project\QAScorer\quarterly_cache.db'
conn = sqlite3.connect(db_path)

print('=== quarterly_reports for 300189.SZ ===')
cur = conn.execute("SELECT ts_code, report_date, report_type, block_text FROM quarterly_reports WHERE ts_code='300189.SZ' ORDER BY report_date DESC")
rows = cur.fetchall()
for r in rows:
    ts_code, date, rtype, text = r
    print(f"\n--- {date} {rtype} (len={len(text)}) ---")
    # 显示包含同比的行
    for line in text.split('\n'):
        line = line.strip()
        if '同比' in line or '营收' in line[:10] or '净利润' in line[:10]:
            print(f"  {line}")

print()
print('=== quarterly_ttm_cache for 300189.SZ ===')
cur2 = conn.execute("SELECT * FROM quarterly_ttm_cache WHERE ts_code='300189.SZ'")
cols = [d[0] for d in cur2.description]
print('Columns:', cols)
for r in cur2.fetchall():
    print(r)

conn.close()
