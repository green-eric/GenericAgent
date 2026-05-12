#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""调试 600338.SH 西藏珠峰 数据"""
import sys
sys.path.insert(0, r'D:\Project\AnnualScorer')
from annual_scorer import *

token = load_token()
result = fetch_stock_finance('600338.SH', '西藏珠峰', token)

print("=" * 80)
print("原始返回内容:")
print("=" * 80)
print(result['content'][:3000])
print("=" * 80)
print("\n提取的段落:")
block = _extract_annual_block(result['content'])
print(block[:2000] if block else "(空)")
print("=" * 80)
print("\n解析的指标:")
metrics = result.get('metrics', {})
for k, v in metrics.items():
    print(f"  {k}: {v}")

# 也看看数据库里存的什么
import sqlite3
conn = sqlite3.connect(Config.DB_FILE)
cur = conn.execute(
    'SELECT report_date, roe, gross_margin, net_margin, revenue_yoy, profit_yoy, debt_ratio, net_profit, ocf_abs '
    'FROM financial_reports WHERE ts_code="600338.SH" AND report_type="annual" ORDER BY report_date DESC LIMIT 3'
)
print("\n数据库中的记录:")
for r in cur.fetchall():
    print(f"  {r}")
conn.close()
