#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sqlite3, json, sys, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

conn = sqlite3.connect('stock_cache.db')

# Check what report_date we have for stocks with null net_profit in JSON
# First, check the DB for 光线传媒
cur = conn.execute("SELECT * FROM financial_reports WHERE ts_code='300251.SZ' ORDER BY report_date DESC")
rows = cur.fetchall()
cols = [desc[0] for desc in cur.description]
print("=== 光线传媒 DB records ===")
for row in rows:
    print(dict(zip(cols, row)))

# Check a few stocks
for ts in ['600867.SH', '001316.SZ', '300139.SZ', '301611.SZ']:
    cur = conn.execute("SELECT ts_code, report_date, report_type, net_profit, deducted_profit, roe FROM financial_reports WHERE ts_code=? ORDER BY report_date DESC LIMIT 1", (ts,))
    row = cur.fetchone()
    if row:
        print(f"{ts}: report_date={row[1]}, type={row[2]}, net_profit={row[3]}, deducted={row[4]}, roe={row[5]}")

# Count how many have net_profit null in DB
cur = conn.execute("SELECT COUNT(*) FROM financial_reports WHERE report_type='annual' AND net_profit IS NULL")
print(f"\nDB中 net_profit为null的年报记录: {cur.fetchone()[0]}")

cur = conn.execute("SELECT COUNT(*) FROM financial_reports WHERE report_type='annual'")
print(f"DB中年报记录总数: {cur.fetchone()[0]}")

# Check if the issue is that net_profit is not being saved to DB
# Look at the save_reports_batch function - it saves 'net_profit' from r.get('annual_net_profit')
# But the JSON output comes from fresh_data which has annual_net_profit directly

# Let's check: does the JSON have annual_report_date for the first stock?
print("\n=== Checking JSON for report_date ===")
with open('股票分析数据_20260425_225222.json','r',encoding='utf-8') as f:
    data = json.load(f)

# Find stocks with report_date
has_rd = [(r['name'], r['ts_code'], r.get('annual_report_date')) for r in data if r.get('annual_report_date')]
print(f"JSON中有report_date的股票: {len(has_rd)}")
for n, ts, rd in has_rd[:5]:
    print(f"  {n}({ts}): {rd}")

# The issue: annual_report_date is parsed but not included in the output dict
# Let's check what parse_financial_all returns
print("\n=== Testing parse_financial_all ===")

def _extract_annual_block(text):
    annual_header_pat = re.compile(r'统计截止日期为(\d{4})1231的年报')
    m = annual_header_pat.search(text)
    if not m:
        return None
    year = m.group(1)
    start = m.start()
    next_section = re.search(r'统计截止日期为', text[start + 1:])
    if next_section:
        end = start + 1 + next_section.start()
    else:
        end = len(text)
    return text[start:end]

# Test with a block where 净利润 line has different formats
test_formats = [
    # Format 1: standard (works)
    "统计截止日期为20241231的年报\n净利润 80.00亿元；",
    # Format 2: no space (works)
    "统计截止日期为20241231的年报\n净利润80.00亿元，",
    # Format 3: with 元 unit (works)
    "统计截止日期为20241231的年报\n净利润1642130865.33元，",
    # Format 4: 净利润 with parentheses or other chars
    "统计截止日期为20241231的年报\n净利润（亿元）80.00；",
    # Format 5: 净利润 on same line as other metrics
    "统计截止日期为20241231的年报\n销售净利率 16.00%，净利润 80.00亿元，归母净利润 75.00亿元",
]

for i, block in enumerate(test_formats):
    line = None
    for l in block.split('\n'):
        l = l.strip()
        if l.startswith('净利润') and '归母' not in l and '扣非' not in l:
            line = l
            break
    print(f"Format {i+1}: line={line}")
    if line:
        m = re.search(r'([-+]?\d+\.?\d*)\s*(万亿元|亿元|万元|千元|元)', line)
        print(f"  Parsed: {m.group(1) if m else 'FAILED'}")

conn.close()
