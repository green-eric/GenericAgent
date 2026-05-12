#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全面测试revenue_yoy和profit_yoy的取值正确性"""
import os, sys, re, json, sqlite3

sys.path.insert(0, r'D:\Project\QAScorer')

import importlib
import qa_scorer
importlib.reload(qa_scorer)

from qa_scorer import (
    run_neodata, load_token, _extract_all_quarterly_blocks,
    _parse_single_block, _compute_ttm
)

token = load_token()

# 测试股票列表：包含已知有问题的300189和一些正常股票
test_stocks = [
    ("300189.SZ", "神农种业"),   # 已知有问题
    ("000001.SZ", "平安银行"),   # 大盘银行股
    ("600519.SH", "贵州茅台"),   # 大盘消费股
    ("000858.SZ", "五粮液"),     # 消费股
    ("601318.SH", "中国平安"),   # 金融股
    ("300750.SZ", "宁德时代"),   # 新能源
    ("002594.SZ", "比亚迪"),     # 汽车
    ("600036.SH", "招商银行"),   # 银行
]

print("=" * 80)
print("测试revenue_yoy和profit_yoy取值")
print("=" * 80)

for ts_code, name in test_stocks:
    print(f"\n{'='*60}")
    print(f"股票: {ts_code} {name}")
    print(f"{'='*60}")

    query = f"{ts_code} {name} 最新季报"
    try:
        text = run_neodata(query, token)
    except Exception as e:
        print(f"  API调用失败: {e}")
        continue

    if not text:
        print("  API返回为空")
        continue

    # 提取所有block
    blocks = _extract_all_quarterly_blocks(text)
    print(f"  Block数量: {len(blocks)}")

    for i, (year, q_date, block) in enumerate(blocks):
        parsed = _parse_single_block(block)
        rev_yoy = parsed.get("revenue_yoy")
        prof_yoy = parsed.get("profit_yoy")
        revenue = parsed.get("revenue")
        net_profit = parsed.get("net_profit")

        print(f"\n  Block {i}: {year}{q_date}")
        print(f"    revenue={revenue}, net_profit={net_profit}")
        print(f"    revenue_yoy={rev_yoy}, profit_yoy={prof_yoy}")

        # 如果yoy不为None，找出它在原始文本中的位置
        if rev_yoy is not None:
            for line in block.split("\n"):
                if "同比" in line and str(rev_yoy) in line:
                    print(f"    [营收同比来源] {line.strip()}")
                    break
        if prof_yoy is not None:
            for line in block.split("\n"):
                if "同比" in line and str(prof_yoy) in line:
                    print(f"    [净利润同比来源] {line.strip()}")
                    break

    # 检查最新季度的yoy
    if blocks:
        latest_year, latest_q, latest_block = blocks[0]
        latest = _parse_single_block(latest_block)
        print(f"\n  >>> 最新季度: {latest_year}{latest_q}")
        print(f"  >>> revenue_yoy={latest.get('revenue_yoy')}, profit_yoy={latest.get('profit_yoy')}")

        # 在原始API文本中搜索所有同比增长
        print(f"\n  [API文本中所有含'同比'的行 - 仅最新block]")
        for line in latest_block.split("\n"):
            if "同比" in line:
                print(f"    {line.strip()}")

    print()
