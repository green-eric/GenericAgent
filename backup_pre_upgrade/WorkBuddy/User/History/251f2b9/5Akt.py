#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""精确验证评分计算 + 检查 fetch_success=False 但 error=None 的情况"""
import json, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

JSON_FILE = r'c:\Users\green\WorkBuddy\20260424203734\workplace\股票分析数据_20260426_000332.json'

with open(JSON_FILE, 'r', encoding='utf-8') as f:
    d = json.load(f)

stocks_list = d['stocks']
stocks = {s['ts_code']: s for s in stocks_list}

# ====== 问题检查：fetch_success=False 但 error=None 的股票 ======
print("=" * 70)
print("【关键问题检查】fetch_success=False 但 error=None 的股票")
print("=" * 70)

problem_stocks = [s for s in stocks_list if s.get('fetch_success') == False and not s.get('error')]
print(f"\n数量: {len(problem_stocks)}")

# 这些股票的评分分布
grade_dist = {}
for s in problem_stocks:
    r = s.get('rating', 'N/A')
    grade_dist[r] = grade_dist.get(r, 0) + 1
print(f"评级分布: {grade_dist}")

# 这些股票的总评分分布
score_ranges = {'0-25': 0, '25-40': 0, '40-55': 0, '55-75': 0, '75-100': 0}
for s in problem_stocks:
    sc = s.get('total_score', 0)
    if sc < 25: score_ranges['0-25'] += 1
    elif sc < 40: score_ranges['25-40'] += 1
    elif sc < 55: score_ranges['40-55'] += 1
    elif sc < 75: score_ranges['55-75'] += 1
    else: score_ranges['75-100'] += 1
print(f"评分分布: {score_ranges}")

# 样本
print(f"\n样本（前5只）:")
for s in problem_stocks[:5]:
    print(f"  {s['name']} ({s['ts_code']}) | fetch={s.get('fetch_success')} | error={s.get('error')} | score={s.get('total_score')} | rating={s.get('rating')}")

# ====== 精确验证晓程科技评分 ======
print(f"\n{'=' * 70}")
print("【精确验证】晓程科技 (300139.SZ)")
print("=" * 70)

PROFIT_SUB = {"roe": 0.4, "gross_margin": 0.3, "net_margin": 0.3}
GROWTH_SUB = {"revenue_yoy": 0.4, "profit_yoy": 0.6}
SCORE_WEIGHTS = {"profit": 0.35, "growth": 0.30, "ocf_quality": 0.15, "debt_risk": 0.20}

def percentile_score(value, values, higher_better=True):
    if value is None: return None
    valid = [v for v in values if isinstance(v, (int, float))]
    if len(valid) < 5: return None
    below = sum(1 for v in valid if v < value)
    equal = sum(1 for v in valid if v == value)
    pct = (below + 0.5 * equal) / len(valid) * 100
    return round(pct, 1) if higher_better else round(100 - pct, 1)

s = stocks['300139.SZ']
ind_stocks = [x for x in stocks_list if x.get('industry_l1') == '有色金属' and not x.get('error')]

indicators = [
    ('roe',         'annual_roe',           True),
    ('gross_margin','annual_gross_margin',  True),
    ('net_margin',  'annual_net_margin',    True),
    ('revenue_yoy', 'annual_revenue_yoy',   True),
    ('profit_yoy',  'annual_profit_yoy',    True),
    ('ocf_ratio',   'annual_ocf_to_profit', True),
    ('debt',        'annual_debt_ratio',    False),
]

scores = {}
for nm, vk, higher in indicators:
    val = s.get(vk)
    all_vals = [x.get(vk) for x in ind_stocks]
    p = percentile_score(val, all_vals, higher)
    scores[nm] = p

# 盈利评分
profit_w = sum(w for nm, w in PROFIT_SUB.items() if scores[nm] is not None)
profit_s = sum(scores[nm] * w for nm, w in PROFIT_SUB.items() if scores[nm] is not None)
profit_score = profit_s / profit_w if profit_w > 0 else 50.0

# 成长评分
growth_w = sum(w for nm, w in GROWTH_SUB.items() if scores[nm] is not None)
growth_s = sum(scores[nm] * w for nm, w in GROWTH_SUB.items() if scores[nm] is not None)
growth_score = growth_s / growth_w if growth_w > 0 else 50.0

ocf_score = scores['ocf'] if scores['ocf'] is not None else 50.0
debt_score = scores['debt'] if scores['debt'] is not None else 50.0

ms = SCORE_WEIGHTS
act = 0.0
if profit_w > 0: act += ms['profit']
if growth_w > 0: act += ms['growth']
if scores['ocf'] is not None: act += ms['ocf_quality']
if scores['debt'] is not None: act += ms['debt_risk']

total = (profit_score * (ms['profit'] / act if profit_w > 0 else 0) +
         growth_score * (ms['growth'] / act if growth_w > 0 else 0) +
         ocf_score * (ms['ocf_quality'] / act if scores['ocf'] is not None else 0) +
         debt_score * (ms['debt_risk'] / act if scores['debt'] is not None else 0))

print(f"\n  手动计算 vs JSON 对比:")
print(f"    盈利评分: {profit_score:.1f} vs {s['detail']['score_profit']} -> {'OK' if abs(profit_score - s['detail']['score_profit']) < 0.2 else 'DIFF'}")
print(f"    成长评分: {growth_score:.1f} vs {s['detail']['score_growth']} -> {'OK' if abs(growth_score - s['detail']['score_growth']) < 0.2 else 'DIFF'}")
print(f"    现金流:   {ocf_score} vs {s['detail']['score_ocf']} -> {'OK' if abs(ocf_score - s['detail']['score_ocf']) < 0.2 else 'DIFF'}")
print(f"    偿债:     {debt_score} vs {s['detail']['score_debt']} -> {'OK' if abs(debt_score - s['detail']['score_debt']) < 0.2 else 'DIFF'}")
print(f"    总评分:   {total:.2f} vs {s['total_score']} -> {'OK' if abs(total - s['total_score']) < 0.1 else 'DIFF'}")

# ====== 精确验证奥赛康 ======
print(f"\n{'=' * 70}")
print("【精确验证】奥赛康 (002755.SZ)")
print("=" * 70)

s2 = stocks['002755.SZ']
ind_stocks2 = [x for x in stocks_list if x.get('industry_l1') == '建筑装饰' and not x.get('error')]

scores2 = {}
for nm, vk, higher in indicators:
    val = s2.get(vk)
    all_vals = [x.get(vk) for x in ind_stocks2]
    p = percentile_score(val, all_vals, higher)
    scores2[nm] = p

profit_w2 = sum(w for nm, w in PROFIT_SUB.items() if scores2[nm] is not None)
profit_s2 = sum(scores2[nm] * w for nm, w in PROFIT_SUB.items() if scores2[nm] is not None)
profit_score2 = profit_s2 / profit_w2 if profit_w2 > 0 else 50.0

growth_w2 = sum(w for nm, w in GROWTH_SUB.items() if scores2[nm] is not None)
growth_s2 = sum(scores2[nm] * w for nm, w in GROWTH_SUB.items() if scores2[nm] is not None)
growth_score2 = growth_s2 / growth_w2 if growth_w2 > 0 else 50.0

ocf_score2 = scores2['ocf'] if scores2['ocf'] is not None else 50.0
debt_score2 = scores2['debt'] if scores2['debt'] is not None else 50.0

act2 = 0.0
if profit_w2 > 0: act2 += ms['profit']
if growth_w2 > 0: act2 += ms['growth']
if scores2['ocf'] is not None: act2 += ms['ocf_quality']
if scores2['debt'] is not None: act2 += ms['debt_risk']

total2 = (profit_score2 * (ms['profit'] / act2 if profit_w2 > 0 else 0) +
          growth_score2 * (ms['growth'] / act2 if growth_w2 > 0 else 0) +
          ocf_score2 * (ms['ocf_quality'] / act2 if scores2['ocf'] is not None else 0) +
          debt_score2 * (ms['debt_risk'] / act2 if scores2['debt'] is not None else 0))

print(f"\n  手动计算 vs JSON 对比:")
print(f"    盈利评分: {profit_score2:.1f} vs {s2['detail']['score_profit']} -> {'OK' if abs(profit_score2 - s2['detail']['score_profit']) < 0.2 else 'DIFF'}")
print(f"    成长评分: {growth_score2:.1f} vs {s2['detail']['score_growth']} -> {'OK' if abs(growth_score2 - s2['detail']['score_growth']) < 0.2 else 'DIFF'}")
print(f"    现金流:   {ocf_score2} vs {s2['detail']['score_ocf']} -> {'OK' if abs(ocf_score2 - s2['detail']['score_ocf']) < 0.2 else 'DIFF'}")
print(f"    偿债:     {debt_score2} vs {s2['detail']['score_debt']} -> {'OK' if abs(debt_score2 - s2['detail']['score_debt']) < 0.2 else 'DIFF'}")
print(f"    总评分:   {total2:.2f} vs {s2['total_score']} -> {'OK' if abs(total2 - s2['total_score']) < 0.1 else 'DIFF'}")
