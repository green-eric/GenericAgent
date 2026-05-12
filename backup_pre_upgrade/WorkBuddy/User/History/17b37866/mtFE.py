# -*- coding: utf-8 -*-
import sqlite3
conn = sqlite3.connect(r'd:\Project\QAScorer\stock_cache.db')
conn.row_factory = sqlite3.Row

print("=== 年报记录 (fetch_success=1) ===")
cur = conn.execute("SELECT ts_code, roe, gross_margin, net_margin, revenue_yoy, profit_yoy, ocf_to_profit, debt_ratio FROM financial_reports WHERE report_type='annual' AND fetch_success=1 ORDER BY ts_code")
rows = cur.fetchall()
print(f"共 {len(rows)} 条")
for r in rows:
    print(f"  {r['ts_code']} ROE={r['roe']} 毛利率={r['gross_margin']} 净利率={r['net_margin']} 营收同比={r['revenue_yoy']} 利润同比={r['profit_yoy']} OCF={r['ocf_to_profit']} 负债率={r['debt_ratio']}")

print("\n=== 季报记录 (fetch_success=1) ===")
cur = conn.execute("SELECT ts_code, roe, gross_margin, net_margin, revenue_yoy, profit_yoy, ocf_to_profit, debt_ratio FROM financial_reports WHERE report_type='quarterly' AND fetch_success=1 ORDER BY ts_code")
rows = cur.fetchall()
print(f"共 {len(rows)} 条")
for r in rows:
    print(f"  {r['ts_code']} ROE={r['roe']} 毛利率={r['gross_margin']} 净利率={r['net_margin']} 营收同比={r['revenue_yoy']} 利润同比={r['profit_yoy']} OCF={r['ocf_to_profit']} 负债率={r['debt_ratio']}")

print("\n=== 股票名称 ===")
cur = conn.execute("SELECT ts_code, name FROM stocks ORDER BY ts_code")
rows = cur.fetchall()
print(f"共 {len(rows)} 条")
for r in rows:
    print(f"  {r['ts_code']} {r['name']}")

conn.close()
