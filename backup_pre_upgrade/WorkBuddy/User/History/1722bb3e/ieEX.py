#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, re

sys.path.insert(0, r'D:\Project\QAScorer')

# 重新加载模块（清除旧缓存）
import importlib
import qa_scorer
importlib.reload(qa_scorer)

from qa_scorer import run_neodata, load_token, _extract_all_quarterly_blocks, _parse_single_block, _compute_ttm

token = load_token()
text = run_neodata("300189.SZ 神农种业 最新季报", token)

# 测试修复后的正则
blocks = _extract_all_quarterly_blocks(text)
print("=== 修复后: Number of blocks: " + str(len(blocks)) === "")
for i, (year, q_date, block) in enumerate(blocks):
    print("\n--- Block " + str(i) + " (year=" + year + ", q=" + q_date + ") ---")
    parsed = _parse_single_block(block)
    # 只打印非None的关键字段
    key_fields = ['revenue', 'net_profit', 'revenue_yoy', 'profit_yoy', 'gross_margin', 'net_margin', 'total_assets', 'total_liabilities', 'net_assets']
    for k in key_fields:
        v = parsed.get(k)
        if v is not None:
            print("  " + k + "=" + str(v))

# 测试TTM计算
print("\n\n=== TTM计算 ===")
ttm = _compute_ttm(blocks)
for k, v in ttm.items():
    if v is not None:
        print("  " + k + "=" + str(v))

# 验证20260331 Q1的数据
print("\n\n=== 验证 ===")
print("20260331 Q1 营业总收入应为: 28,089,539.46")
print("20260331 Q1 归母净利润应为: -6,497,683.81")
print("20260331 Q1 营收同比应为: None (API未直接提供)")
print("20260331 Q1 归母净利润同比应为: 48.60%")

# 找到20260331的block
for year, q_date, block in blocks:
    if year == "2026" and q_date == "0331":
        parsed = _parse_single_block(block)
        print("\n实际解析结果 (20260331):")
        print("  revenue=" + str(parsed.get('revenue')))
        print("  net_profit=" + str(parsed.get('net_profit')))
        print("  revenue_yoy=" + str(parsed.get('revenue_yoy')))
        print("  profit_yoy=" + str(parsed.get('profit_yoy')))
        break
