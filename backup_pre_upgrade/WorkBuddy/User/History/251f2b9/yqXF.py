#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""精确验证评分计算"""
import json, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

JSON_FILE = r'c:\Users\green\WorkBuddy\20260424203734\workplace\股票分析数据_20260426_000332.json'

with open(JSON_FILE, 'r', encoding='utf-8') as f:
    d = json.load(f)

stocks = {s['ts_code']: s for s in d['stocks']}

# 配置
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

def verify_stock(ts_code, industry_name):
    s = stocks[ts_code]
    ind_stocks = [x for x in d['stocks'] if x.get('industry_l1') == industry_name and not x.get('error')]
    
    indicators = [
        ('roe',    'annual_roe',           'roe_list',    True),
        ('gross',  'annual_gross_margin',  'gross_list',  True),
        ('net',    'annual_net_margin',    'net_list',    True),
        ('rev_yoy','annual_revenue_yoy',   'rev_list',    True),
        ('prof_yoy','annual_profit_yoy',   'prof_list',   True),
        ('ocf',    'annual_ocf_to_profit', 'ocf_list',    True),
        ('debt',   'annual_debt_ratio',    'debt_list',   False),
    ]
    
    scores = {}
    for nm, vk, lk, higher in indicators:
        val = s.get(vk)
        all_vals = [x.get(vk) for x in ind_stocks]
        p = percentile_score(val, all_vals, higher)
        scores[nm] = p
        print(f"  {nm:>10s}: val={str(val):>12s} -> percentile={str(p):>6s}%")
    
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
    
    print(f"\n  手动计算:")
    print(f"    盈利评分 = {profit_score:.1f} (期望 {s['detail']['score_profit']}) {'OK' if abs(profit_score - s['detail']['score_profit']) < 0.2 else 'MISMATCH'}")
    print(f"    成长评分 = {growth_score:.1f} (期望 {s['detail']['score_growth']}) {'OK' if abs(growth_score - s['detail']['score_growth']) < 0.2 else 'MISMATCH'}")
    print(f"    现金流评分 = {ocf_score} (期望 {s['detail']['score_ocf']}) {'OK' if abs(ocf_score - s['detail']['score_ocf']) < 0.2 else 'MISMATCH'}")
    print(f"    偿债评分 = {debt_score} (期望 {s['detail']['score_debt']}) {'OK' if abs(debt_score - s['detail']['score_debt']) < 0.2 else 'MISMATCH'}")
    print(f"    总评分 = {total:.2f} (期望 {s['total_score']}) {'OK' if abs(total - s['total_score']) < 0.1 else 'MISMATCH'}")
    
    return abs(total - s['total_score']) < 0.1

print("=" * 70)
print("晓程科技 (300139.SZ) - 有色金属行业")
print("=" * 70)
ok1 = verify_stock('300139.SZ', '有色金属')

print(f"\n{'=' * 70}")
print("奥赛康 (002755.SZ) - 建筑装饰行业")
print("=" * 70)
ok2 = verify_stock('002755.SZ', '建筑装饰')

print(f"\n{'=' * 70}")
print(f"结论: {'全部OK' if ok1 and ok2 else '存在差异'}")
print("=" * 70)
