#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试数据完整度门槛逻辑"""
import json, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

JSON_FILE = r'c:\Users\green\WorkBuddy\20260424203734\workplace\股票分析数据_20260426_000332.json'
with open(JSON_FILE, 'r', encoding='utf-8') as f:
    d = json.load(f)
all_stocks = d['stocks']

# 模拟 compute_completeness
def compute_completeness(stock):
    keys = ["annual_roe", "annual_gross_margin", "annual_net_margin", "annual_debt_ratio",
            "annual_revenue_yoy", "annual_profit_yoy", "annual_ocf_to_profit"]
    present = sum(1 for k in keys if stock.get(k) is not None)
    ratio = present / len(keys)
    if ratio >= 0.7: return "高", present
    if ratio >= 0.4: return "中", present
    return "低", present

MIN_INDICATORS_FOR_SCORING = 4

# 统计
would_skip = 0
would_score = 0
skip_rating_dist = {}
score_rating_dist = {}

for s in all_stocks:
    comp, present = compute_completeness(s)
    if present < MIN_INDICATORS_FOR_SCORING:
        would_skip += 1
        r = s.get('rating', 'N/A')
        skip_rating_dist[r] = skip_rating_dist.get(r, 0) + 1
    else:
        would_score += 1
        r = s.get('rating', 'N/A')
        score_rating_dist[r] = score_rating_dist.get(r, 0) + 1

print("=" * 60)
print("数据完整度门槛测试结果（MIN_INDICATORS_FOR_SCORING = 4）")
print("=" * 60)
print(f"\n有评分（≥4 个指标）: {would_score} 只")
print(f"  评级分布: {score_rating_dist}")
print(f"\n数据不足（<4 个指标）: {would_skip} 只")
print(f"  原评级分布: {skip_rating_dist}")

# 完整度分布统计
comp_dist = {}
for s in all_stocks:
    comp, present = compute_completeness(s)
    comp_dist[present] = comp_dist.get(present, 0) + 1
print(f"\n完整度分布（有效指标数 -> 股票数）:")
for k in sorted(comp_dist.keys()):
    marker = " ← 门槛" if k == MIN_INDICATORS_FOR_SCORING - 1 else ""
    print(f"  {k}/7: {comp_dist[k]:>5d} 只{marker}")

print(f"\n结论: {would_skip} 只股票将被标记为'数据不足'，不参与 A-E 评级")
