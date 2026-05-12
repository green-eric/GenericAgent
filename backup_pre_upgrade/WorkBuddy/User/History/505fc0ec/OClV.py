#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全面测试修复后的revenue_yoy和profit_yoy取值
"""
import os, sys, re

sys.path.insert(0, r'D:\Project\QAScorer')

import importlib
import qa_scorer
importlib.reload(qa_scorer)

from qa_scorer import (
    run_neodata, load_token, _extract_all_report_sections,
    _parse_single_block, _compute_ttm, fetch_quarterly_data
)

token = load_token()

# 测试股票：包含各种情况
test_stocks = [
    ("300189.SZ", "神农种业"),    # 有Q1单季报+年报
    ("000001.SZ", "平安银行"),    # 有Q1单季报+年报
    ("600519.SH", "贵州茅台"),    # 有Q1单季报+年报
    ("300750.SZ", "宁德时代"),    # 有Q1单季报+年报
    ("002594.SZ", "比亚迪"),      # 最新是年报
    ("600036.SH", "招商银行"),    # 最新是年报
    ("000858.SZ", "五粮液"),      # 最新是Q3单季报
    ("601318.SH", "中国平安"),    # 最新是年报
    ("000333.SZ", "美的集团"),    # 最新是年报
    ("002415.SZ", "海康威视"),    # 有Q1单季报+年报
]

print("=" * 80)
print("全面测试：修复后各字段取值")
print("=" * 80)

for ts_code, name in test_stocks:
    print(f"\n{'='*60}")
    print(f"股票: {ts_code} {name}")
    print(f"{'='*60}")

    # 直接用新的段落拆分
    query = f"{ts_code} {name} 最新季报"
    text = run_neodata(query, token)
    sections = _extract_all_report_sections(text)

    print(f"  总段落数: {len(sections)}")
    quarterly = [(d, t, txt) for d, t, txt in sections if "季报" in t]
    annual = [(d, t, txt) for d, t, txt in sections if "年报" in t]
    print(f"  单季报段落: {len(quarterly)}, 年报段落: {len(annual)}")

    # 打印每个段落的类型和数据
    for i, (date, rtype, stext) in enumerate(sections):
        parsed = _parse_single_block(stext)
        rev_yoy = parsed.get("revenue_yoy")
        prof_yoy = parsed.get("profit_yoy")
        revenue = parsed.get("revenue")
        net_profit = parsed.get("net_profit")
        print(f"  段落{i}: {date} {rtype}")
        print(f"    revenue={revenue}, net_profit={net_profit}, revenue_yoy={rev_yoy}, profit_yoy={prof_yoy}")

    # 使用fetch_quarterly_data获取最终结果
    # 先清除缓存
    import sqlite3
    db_path = qa_scorer.Config.QUARTERLY_DB_FILE
    try:
        with sqlite3.connect(db_path, timeout=10.0) as conn:
            conn.execute("DELETE FROM quarterly_reports WHERE ts_code = ?", (ts_code,))
            conn.execute("DELETE FROM quarterly_ttm_cache WHERE ts_code = ?", (ts_code,))
            conn.commit()
    except:
        pass

    result = fetch_quarterly_data(ts_code, name, token)
    ttm = result.get("ttm_metrics", {})
    latest = result.get("latest_quarterly", {})

    print(f"\n  >>> fetch_quarterly_data 返回:")
    print(f"  >>> latest_quarter={result.get('latest_quarter')}, quarter_count={result.get('quarter_count')}")
    print(f"  >>> revenue_yoy={latest.get('revenue_yoy')}, profit_yoy={latest.get('profit_yoy')}")
    print(f"  >>> debt_ratio={latest.get('debt_ratio')}")
    print(f"  >>> roe_ttm={ttm.get('roe_ttm')}, gross_margin_ttm={ttm.get('gross_margin_ttm')}")
    print(f"  >>> net_margin_ttm={ttm.get('net_margin_ttm')}, ocf_ratio_ttm={ttm.get('ocf_ratio_ttm')}")
    print(f"  >>> revenue_ttm={ttm.get('revenue_ttm')}, net_profit_ttm={ttm.get('net_profit_ttm')}")
