#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

JSON_FILE = r'c:\Users\green\WorkBuddy\20260424203734\workplace\股票分析数据_20260426_000332.json'
with open(JSON_FILE, 'r', encoding='utf-8') as f:
    d = json.load(f)
all_stocks = d['stocks']

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

def calc_one(s, ind_stocks, all_stocks_fallback):
    """完全模拟 calc_score 逻辑"""
    ind = s.get('industry_l1', '未分类')
    use_ind = ind != '未分类'
    
    keys_map = [
        ('roe',         'annual_roe',           'roe_list',    True),
        ('gross_margin','annual_gross_margin',  'gm_list',     True),
        ('net_margin',  'annual_net_margin',    'nm_list',     True),
        ('revenue_yoy', 'annual_revenue_yoy',   'ry_list',     True),
        ('profit_yoy',  'annual_profit_yoy',    'py_list',     True),
        ('ocf_ratio',   'annual_ocf_to_profit', 'ocf_list',    True),
        ('debt',        'annual_debt_ratio',    'db_list',     False),
    ]
    
    scores = {}
    for nm, vk, _lk, higher in keys_map:
        val = s.get(vk)
        if val is None:
            scores[nm] = None
            continue
        if nm == 'roe' and isinstance(val, (int, float)) and val < 0:
            scores[nm] = 0.0
            continue
        if use_ind:
            all_vals = [x.get(vk) for x in ind_stocks]
        else:
            all_vals = [x.get(vk) for x in all_stocks_fallback]
        p = percentile_score(val, all_vals, higher)
        scores[nm] = p
    
    profit_w = sum(w for nm, w in PROFIT_SUB.items() if scores.get(nm) is not None)
    profit_s = sum(scores[nm] * w for nm, w in PROFIT_SUB.items() if scores.get(nm) is not None)
    profit_score = profit_s / profit_w if profit_w > 0 else 50.0
    
    growth_w = sum(w for nm, w in GROWTH_SUB.items() if scores.get(nm) is not None)
    growth_s = sum(scores[nm] * w for nm, w in GROWTH_SUB.items() if scores.get(nm) is not None)
    growth_score = growth_s / growth_w if growth_w > 0 else 50.0
    
    ocf_score = scores['ocf_ratio'] if scores.get('ocf_ratio') is not None else 50.0
    debt_score = scores['debt'] if scores.get('debt') is not None else 50.0
    
    ms = SCORE_WEIGHTS
    act = 0.0
    if profit_w > 0: act += ms['profit']
    if growth_w > 0: act += ms['growth']
    if scores.get('ocf_ratio') is not None: act += ms['ocf_quality']
    if scores.get('debt') is not None: act += ms['debt_risk']
    
    if act == 0:
        total = 50.0
    else:
        total = (profit_score * (ms['profit'] / act if profit_w > 0 else 0) +
                 growth_score * (ms['growth'] / act if growth_w > 0 else 0) +
                 ocf_score * (ms['ocf_quality'] / act if scores.get('ocf_ratio') is not None else 0) +
                 debt_score * (ms['debt_risk'] / act if scores.get('debt') is not None else 0))
    
    rating = 'A' if total >= 75 else ('B' if total >= 55 else ('C' if total >= 40 else ('D' if total >= 25 else 'E')))
    
    return profit_score, growth_score, ocf_score, debt_score, total, rating

# ====== 问题检查 ======
print("=" * 70)
print("【问题检查】fetch_success=False 但 error=None 的股票")
print("=" * 70)
problem = [s for s in all_stocks if s.get('fetch_success') == False and not s.get('error')]
print(f"数量: {len(problem)}")
grade_dist = {}
for s in problem:
    r = s.get('rating', 'N/A')
    grade_dist[r] = grade_dist.get(r, 0) + 1
print(f"评级分布: {grade_dist}")
score_ranges = {'0-25(E)': 0, '25-40(D)': 0, '40-55(C)': 0, '55-75(B)': 0, '75-100(A)': 0}
for s in problem:
    sc = s.get('total_score', 0)
    if sc >= 75: score_ranges['75-100(A)'] += 1
    elif sc >= 55: score_ranges['55-75(B)'] += 1
    elif sc >= 40: score_ranges['40-55(C)'] += 1
    elif sc >= 25: score_ranges['25-40(D)'] += 1
    else: score_ranges['0-25(E)'] += 1
print(f"评分分布: {score_ranges}")
print(f"\n样本（前3只）:")
for s in problem[:3]:
    print(f"  {s['name']} ({s['ts_code']}) | score={s.get('total_score')} | rating={s.get('rating')} | completeness={s.get('completeness')}")

# ====== 精确验证两只股票 ======
for ts_code, ind_name in [('300139.SZ', '有色金属'), ('002755.SZ', '建筑装饰')]:
    s = next(x for x in all_stocks if x['ts_code'] == ts_code)
    ind_stocks = [x for x in all_stocks if x.get('industry_l1') == ind_name and not x.get('error')]
    
    ps, gs, os, ds, tot, rt = calc_one(s, ind_stocks, all_stocks)
    
    print(f"\n{'=' * 70}")
    print(f"【精确验证】{s['name']} ({ts_code}) - {ind_name}")
    print("=" * 70)
    print(f"  盈利评分: 计算={ps:.1f} JSON={s['detail']['score_profit']} -> {'OK' if abs(ps - s['detail']['score_profit']) < 0.2 else 'DIFF=' + str(round(ps - s['detail']['score_profit'], 2))}")
    print(f"  成长评分: 计算={gs:.1f} JSON={s['detail']['score_growth']} -> {'OK' if abs(gs - s['detail']['score_growth']) < 0.2 else 'DIFF=' + str(round(gs - s['detail']['score_growth'], 2))}")
    print(f"  现金流:   计算={os} JSON={s['detail']['score_ocf']} -> {'OK' if abs(os - s['detail']['score_ocf']) < 0.2 else 'DIFF=' + str(round(os - s['detail']['score_ocf'], 2))}")
    print(f"  偿债:     计算={ds} JSON={s['detail']['score_debt']} -> {'OK' if abs(ds - s['detail']['score_debt']) < 0.2 else 'DIFF=' + str(round(ds - s['detail']['score_debt'], 2))}")
    print(f"  总评分:   计算={tot:.2f} JSON={s['total_score']} -> {'OK' if abs(tot - s['total_score']) < 0.1 else 'DIFF=' + str(round(tot - s['total_score'], 2))}")
    print(f"  评级:     计算={rt} JSON={s['rating']} -> {'OK' if rt == s['rating'] else 'DIFF'}")
