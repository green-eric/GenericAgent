#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""分析错误日志中各种错误的含义和数量"""
import json, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

JSON_FILE = r'c:\Users\green\WorkBuddy\20260424203734\workplace\股票分析数据_20260426_000332.json'
with open(JSON_FILE, 'r', encoding='utf-8') as f:
    d = json.load(f)
all_stocks = d['stocks']

# 统计各种错误
api_error_stocks = [s for s in all_stocks if s.get('fetch_success') == False]
print(f"fetch_success=False 的股票: {len(api_error_stocks)}")

# 按评分和评级分布
grade_dist = {}
for s in api_error_stocks:
    r = s.get('rating', 'N/A')
    grade_dist[r] = grade_dist.get(r, 0) + 1
print(f"评级分布: {grade_dist}")

# 这些股票的 error 字段
has_error = sum(1 for s in api_error_stocks if s.get('error'))
no_error = sum(1 for s in api_error_stocks if not s.get('error'))
print(f"\n有 error 字段: {has_error}")
print(f"无 error 字段（仅 fetch_success=False）: {no_error}")

# 样本
print(f"\n样本（前10只）:")
for s in api_error_stocks[:10]:
    print(f"  {s['name']} ({s['ts_code']}) | error={s.get('error')} | score={s.get('total_score')} | rating={s.get('rating')}")

# 有 error 字段的样本
error_stocks = [s for s in api_error_stocks if s.get('error')]
print(f"\n有 error 字段的样本（前5只）:")
for s in error_stocks[:5]:
    print(f"  {s['name']} ({s['ts_code']}) | error={s.get('error')}")
