#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""深入分析API返回的原始数据结构，特别是同比增长率的分布"""
import os, sys, re, json

sys.path.insert(0, r'D:\Project\QAScorer')

import importlib
import qa_scorer
importlib.reload(qa_scorer)

from qa_scorer import run_neodata, load_token, _extract_all_quarterly_blocks

token = load_token()

# 重点分析300189
ts_code, name = "300189.SZ", "神农种业"
query = f"{ts_code} {name} 最新季报"
text = run_neodata(query, token)

print("=" * 80)
print("原始API返回文本分析")
print("=" * 80)

# 找出所有"统计截止日期"锚点
pattern = r"统计截止日期为(\d{4})(0331|0630|0930|1231)的(?:Q[1-4]单?)?(?:季?年报?)"
matches = list(re.finditer(pattern, text))
print(f"\n锚点数量: {len(matches)}")
for i, m in enumerate(matches):
    print(f"  锚点{i}: {m.group()} @ pos={m.start()}")

blocks = _extract_all_quarterly_blocks(text)
print(f"\nBlock数量: {len(blocks)}")

# 对每个block，打印完整的"财务主要复合指标"段落
for i, (year, q_date, block) in enumerate(blocks):
    print(f"\n{'='*60}")
    print(f"Block {i}: {year}{q_date}")
    print(f"{'='*60}")

    # 找"财务主要复合指标"段落
    lines = block.split("\n")
    in_composite = False
    composite_lines = []
    for j, line in enumerate(lines):
        if "财务主要复合指标" in line or "主要复合指标" in line:
            in_composite = True
            composite_lines.append(f"[{j}] {line.strip()}")
            continue
        if in_composite:
            # 如果遇到下一个大段落标题（通常是没有缩进的中文标题），停止
            stripped = line.strip()
            if stripped and not stripped.startswith(" ") and not stripped.startswith("\t") and any(kw in stripped for kw in ["利润表", "资产负债表", "现金流量表", "财务指标", "主要指标", "---", "==="]):
                break
            composite_lines.append(f"[{j}] {stripped}")

    print("\n财务主要复合指标段落:")
    for cl in composite_lines:
        print(f"  {cl}")

    # 打印完整block文本（截取前2000字符）
    print(f"\n完整block文本 (前2000字符):")
    print(block[:2000])

# 现在分析其他几个股票
print("\n\n" + "=" * 80)
print("对比分析：其他股票的同比增长率分布")
print("=" * 80)

for ts_code, name in [("000001.SZ", "平安银行"), ("600519.SH", "贵州茅台")]:
    print(f"\n{'='*60}")
    print(f"股票: {ts_code} {name}")
    print(f"{'='*60}")

    query = f"{ts_code} {name} 最新季报"
    text = run_neodata(query, token)
    blocks = _extract_all_quarterly_blocks(text)

    for i, (year, q_date, block) in enumerate(blocks):
        print(f"\n  Block {i}: {year}{q_date}")
        # 提取所有同比增长
        for line in block.split("\n"):
            if "同比" in line and ("营业收入" in line or "归母净利润" in line or "净利润" in line):
                print(f"    {line.strip()}")
