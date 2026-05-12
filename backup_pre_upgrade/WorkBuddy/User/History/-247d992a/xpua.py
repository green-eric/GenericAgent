# -*- coding: utf-8 -*-
import sqlite3
conn = sqlite3.connect(r'd:\Project\QAScorer\stock_cache.db')
conn.row_factory = sqlite3.Row

# 检查年报记录数
cur = conn.execute("SELECT ts_code, COUNT(*) as cnt FROM financial_reports WHERE report_type='annual' GROUP BY ts_code HAVING cnt > 1")
rows = cur.fetchall()
print(f"有多条年报记录的股票: {len(rows)}")
for r in rows:
    print(f"  {r['ts_code']}: {r['cnt']} 条")

# 检查季报记录数
cur = conn.execute("SELECT ts_code, COUNT(*) as cnt FROM financial_reports WHERE report_type='quarterly' GROUP BY ts_code HAVING cnt > 1")
rows = cur.fetchall()
print(f"\n有多条季报记录的股票: {len(rows)}")
for r in rows:
    print(f"  {r['ts_code']}: {r['cnt']} 条")

# 检查所有年报记录
cur = conn.execute("SELECT ts_code, report_date, roe, fetch_success FROM financial_reports WHERE report_type='annual' ORDER BY ts_code, report_date")
rows = cur.fetchall()
print(f"\n所有年报记录: {len(rows)} 条")
for r in rows:
    print(f"  {r['ts_code']} {r['report_date']} ROE={r['roe']} success={r['fetch_success']}")

conn.close()
