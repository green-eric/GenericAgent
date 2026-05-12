#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""调试300189神农种业：检查段落拆分和各段落的营收同比/净利润同比"""
import sys, os, re, json, time
sys.path.insert(0, r'D:\Project\QAScorer')
os.chdir(r'D:\Project\QAScorer')

from qa_scorer import (
    _extract_all_report_sections,
    _parse_single_block,
    run_neodata,
    Config,
)

ts_code = "300189.SZ"
name = "神农种业"

# 先清缓存，强制重新获取
import sqlite3
db_path = os.path.join(os.path.dirname(__file__), "quarterly_cache.db")
if os.path.exists(db_path):
    with sqlite3.connect(db_path) as conn:
        conn.execute("DELETE FROM quarterly_reports WHERE ts_code=?", (ts_code,))
        conn.execute("DELETE FROM quarterly_ttm_cache WHERE ts_code=?", (ts_code,))
        conn.commit()
    print(f"已清除 {ts_code} 的缓存")

# 获取API数据
from qa_scorer import load_token
token = load_token()
query = f"{ts_code} {name} 最新季报"
print(f"\n查询: {query}")
text = run_neodata(query, token)

if not text:
    print("API返回为空!")
    sys.exit(1)

# 写入原始文本供检查
with open(r'D:\Project\QAScorer\debug_300189_raw.txt', 'w', encoding='utf-8') as f:
    f.write(text)
print(f"\n原始文本已写入 debug_300189_raw.txt ({len(text)} 字符)")

# 段落拆分
sections = _extract_all_report_sections(text)
print(f"\n{'='*80}")
print(f"段落拆分结果: 共 {len(sections)} 个段落")
print(f"{'='*80}")

for i, (date, rtype, txt) in enumerate(sections):
    parsed = _parse_single_block(txt)
    revenue_yoy = parsed.get("revenue_yoy")
    profit_yoy = parsed.get("profit_yoy")
    revenue = parsed.get("revenue")
    profit = parsed.get("net_profit")

    print(f"\n--- 段落 {i+1}: {date} {rtype} ---")
    print(f"  revenue_yoy:  {revenue_yoy}")
    print(f"  profit_yoy:   {profit_yoy}")
    print(f"  revenue:      {revenue}")
    print(f"  net_profit:   {profit}")

    # 显示包含"同比"的行
    for line in txt.split("\n"):
        line = line.strip()
        if "同比" in line:
            print(f"  [同比行] {line}")
        if "营业收入" in line and "同比" not in line:
            print(f"  [营收行] {line}")
        if "归母净利润" in line and "同比" not in line:
            print(f"  [净利润行] {line}")

print(f"\n{'='*80}")
print("问题诊断")
print(f"{'='*80}")

# 检查第一个单季报段落
quarterly = [(d, t, txt) for d, t, txt in sections if "季报" in t]
annual = [(d, t, txt) for d, t, txt in sections if "年报" in t]

print(f"\n单季报段落: {len(quarterly)} 个")
for d, t, txt in quarterly:
    p = _parse_single_block(txt)
    print(f"  {d} {t}: revenue_yoy={p.get('revenue_yoy')}, profit_yoy={p.get('profit_yoy')}")

print(f"\n年报段落: {len(annual)} 个")
for d, t, txt in annual:
    p = _parse_single_block(txt)
    print(f"  {d} {t}: revenue_yoy={p.get('revenue_yoy')}, profit_yoy={p.get('profit_yoy')}")

# 模拟当前代码逻辑
print(f"\n--- 模拟 fetch_quarterly_data 逻辑 ---")
if quarterly:
    latest_date, latest_type, latest_text = quarterly[0]
    latest = _parse_single_block(latest_text)
    print(f"最新单季报: {latest_date} {latest_type}")
    print(f"  revenue_yoy from 单季报: {latest.get('revenue_yoy')}")
    print(f"  profit_yoy from 单季报: {latest.get('profit_yoy')}")

    if latest.get("revenue_yoy") is None and annual:
        print(f"  单季报无revenue_yoy，从年报取...")
        annual_parsed = _parse_single_block(annual[0][2])
        print(f"  年报revenue_yoy: {annual_parsed.get('revenue_yoy')}")
        latest["revenue_yoy"] = annual_parsed["revenue_yoy"]

    if latest.get("profit_yoy") is None and annual:
        print(f"  单季报无profit_yoy，从年报取...")
        annual_parsed = _parse_single_block(annual[0][2])
        print(f"  年报profit_yoy: {annual_parsed.get('profit_yoy')}")
        latest["profit_yoy"] = annual_parsed["profit_yoy"]
else:
    print("  没有单季报段落!")
