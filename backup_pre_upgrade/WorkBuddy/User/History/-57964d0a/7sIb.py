# -*- coding: utf-8 -*-
"""测试不同的百分位算法，找出与Excel匹配的"""
import sys, io, openpyxl
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

wb = openpyxl.load_workbook(r'd:\Project\QAScorer\综合评分_20260426_202924.xlsx')
ws = wb.active

excel_stocks = []
for row in ws.iter_rows(min_row=2, values_only=True):
    if row[0] is None:
        break
    excel_stocks.append({
        'ts_code': row[0], 'name': row[1],
        'roe': row[8], 'gross_margin': row[9], 'net_margin': row[10],
        'revenue_yoy': row[11], 'profit_yoy': row[12],
        'ocf_to_profit': row[13], 'debt_ratio': row[14],
        'total_score': row[3], 'profit_score': row[5],
        'growth_score': row[6], 'cfsafe_score': row[7],
    })

pool = [s for s in excel_stocks if s['roe'] is not None]

PROFIT_W, GROWTH_W, CFSAFE_W = 0.35, 0.30, 0.35
ROE_SUB_W, GROSS_SUB_W, NET_SUB_W = 0.40, 0.30, 0.30
REV_YOY_SUB_W, PROF_YOY_SUB_W = 0.40, 0.60
OCF_SUB_W, DEBT_SUB_W = 0.40, 0.60

def pv(pool, key):
    return [s[key] for s in pool if s.get(key) is not None]

# 测试不同的百分位算法
def pct_rank_v1(value, values, reverse=False):
    """当前算法：lo/(n-1)*100"""
    if not values: return 50.0
    n = len(values)
    if n == 1: return 50.0
    if max(values) == min(values): return 50.0
    sorted_vals = sorted(values, reverse=reverse)
    lo, hi = 0, n - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if (not reverse and sorted_vals[mid] <= value) or (reverse and sorted_vals[mid] >= value):
            lo = mid + 1
        else:
            hi = mid - 1
    return min((lo / (n - 1)) * 100.0, 100.0)

def pct_rank_v2(value, values, reverse=False):
    """替代算法：lo/n*100"""
    if not values: return 50.0
    n = len(values)
    if n == 1: return 50.0
    if max(values) == min(values): return 50.0
    sorted_vals = sorted(values, reverse=reverse)
    lo, hi = 0, n - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if (not reverse and sorted_vals[mid] <= value) or (reverse and sorted_vals[mid] >= value):
            lo = mid + 1
        else:
            hi = mid - 1
    return min((lo / n) * 100.0, 100.0)

def pct_rank_v3(value, values, reverse=False):
    """替代算法：(rank-1)/(n-1)*100，rank从1开始"""
    if not values: return 50.0
    n = len(values)
    if n == 1: return 50.0
    if max(values) == min(values): return 50.0
    sorted_vals = sorted(values, reverse=reverse)
    rank = sorted_vals.index(value) + 1
    return ((rank - 1) / (n - 1)) * 100.0

def calc_scores(target, pool, pct_func, discount):
    roe = target['roe']
    gross = target['gross_margin']
    net = target['net_margin']
    rev_yoy = target['revenue_yoy']
    prof_yoy = target['profit_yoy']
    ocf = target['ocf_to_profit']
    debt = target['debt_ratio']

    roe_s = 0.0 if roe is None else (0.0 if roe < 0 else pct_func(roe, pv(pool, 'roe')))
    gross_s = pct_func(gross, pv(pool, 'gross_margin')) if gross is not None else 0.0
    net_s = pct_func(net, pv(pool, 'net_margin')) if net is not None else 0.0
    profit_score = (roe_s * ROE_SUB_W + gross_s * GROSS_SUB_W + net_s * NET_SUB_W) * discount

    rev_s = pct_func(rev_yoy, pv(pool, 'revenue_yoy')) if rev_yoy is not None else 0.0
    prof_s = pct_func(prof_yoy, pv(pool, 'profit_yoy')) if prof_yoy is not None else 0.0
    growth_score = (rev_s * REV_YOY_SUB_W + prof_s * PROF_YOY_SUB_W) * discount

    ocf_s = pct_func(ocf, pv(pool, 'ocf_to_profit')) if ocf is not None else 0.0
    debt_s = pct_func(debt, pv(pool, 'debt_ratio'), reverse=True) if debt is not None else 0.0
    cfsafe_score = (ocf_s * OCF_SUB_W + debt_s * DEBT_SUB_W) * discount

    total = profit_score * PROFIT_W + growth_score * GROWTH_W + cfsafe_score * CFSAFE_W
    return total, profit_score, growth_score, cfsafe_score

excel_targets = {
    '301377.SZ': (73, 94.29, 60, 62.86),
    '603061.SH': (70.5, 72.86, 60, 77.14),
}

for pct_name, pct_func in [('v1(lo/(n-1))', pct_rank_v1), ('v2(lo/n)', pct_rank_v2), ('v3((rank-1)/(n-1))', pct_rank_v3)]:
    print(f"\n=== 百分位算法: {pct_name} ===")
    for target_code in ['301377.SZ', '603061.SH']:
        target = next(s for s in excel_stocks if s['ts_code'] == target_code)
        total, profit, growth, cfsafe = calc_scores(target, pool, pct_func, 1.0)
        e = excel_targets[target_code]
        diff = abs(total-e[0]) + abs(profit-e[1]) + abs(growth-e[2]) + abs(cfsafe-e[3])
        print(f"  {target_code}: 总{total:.2f}(Δ{total-e[0]:+.2f}) 盈{profit:.2f}(Δ{profit-e[1]:+.2f}) 成{growth:.2f}(Δ{growth-e[2]:+.2f}) 现{cfsafe:.2f}(Δ{cfsafe-e[3]:+.2f}) 总差{diff:.2f}")
