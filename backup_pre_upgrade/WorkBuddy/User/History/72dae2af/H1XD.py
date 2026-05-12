# -*- coding: utf-8 -*-
"""用Excel中的28只股票作为评分池，分别测试discount=1.0和0.95，找出匹配的组合"""
import sys, io, openpyxl
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

wb = openpyxl.load_workbook(r'd:\Project\QAScorer\综合评分_20260426_202924.xlsx')
ws = wb.active

all_stocks = []
for row in ws.iter_rows(min_row=2, values_only=True):
    if row[0] is None:
        break
    stock = {
        'ts_code': row[0], 'name': row[1],
        'roe': row[8], 'gross_margin': row[9], 'net_margin': row[10],
        'revenue_yoy': row[11], 'profit_yoy': row[12],
        'ocf_to_profit': row[13], 'debt_ratio': row[14],
        'total_score': row[3], 'grade': row[4],
        'profit_score': row[5], 'growth_score': row[6], 'cfsafe_score': row[7],
    }
    all_stocks.append(stock)

PROFIT_W, GROWTH_W, CFSAFE_W = 0.35, 0.30, 0.35
ROE_SUB_W, GROSS_SUB_W, NET_SUB_W = 0.40, 0.30, 0.30
REV_YOY_SUB_W, PROF_YOY_SUB_W = 0.40, 0.60
OCF_SUB_W, DEBT_SUB_W = 0.40, 0.60

def percentile_rank(value, values, reverse=False):
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
    pct = (lo / (n - 1)) * 100.0
    return min(pct, 100.0)

def pv(pool, key):
    return [s[key] for s in pool if s.get(key) is not None]

# 测试不同配置
for discount_val in [1.0, 0.95]:
    for use_all in [True, False]:
        pool = all_stocks if use_all else [s for s in all_stocks if s['roe'] is not None]
        label = f"discount={discount_val}, pool={'28只(全部)' if use_all else '19只(有数据)'}"
        
        results = {}
        for target_code in ['301377.SZ', '603061.SH']:
            target = next(s for s in all_stocks if s['ts_code'] == target_code)
            roe, gross, net = target['roe'], target['gross_margin'], target['net_margin']
            rev_yoy, prof_yoy = target['revenue_yoy'], target['profit_yoy']
            ocf, debt = target['ocf_to_profit'], target['debt_ratio']

            roe_s = 0.0 if roe is None else (0.0 if roe < 0 else percentile_rank(roe, pv(pool, 'roe')))
            gross_s = percentile_rank(gross, pv(pool, 'gross_margin')) if gross is not None else 0.0
            net_s = percentile_rank(net, pv(pool, 'net_margin')) if net is not None else 0.0
            profit_score = (roe_s * ROE_SUB_W + gross_s * GROSS_SUB_W + net_s * NET_SUB_W) * discount_val

            rev_s = percentile_rank(rev_yoy, pv(pool, 'revenue_yoy')) if rev_yoy is not None else 0.0
            prof_s = percentile_rank(prof_yoy, pv(pool, 'profit_yoy')) if prof_yoy is not None else 0.0
            growth_score = (rev_s * REV_YOY_SUB_W + prof_s * PROF_YOY_SUB_W) * discount_val

            ocf_s = percentile_rank(ocf, pv(pool, 'ocf_to_profit')) if ocf is not None else 0.0
            debt_s = percentile_rank(debt, pv(pool, 'debt_ratio'), reverse=True) if debt is not None else 0.0
            cfsafe_score = (ocf_s * OCF_SUB_W + debt_s * DEBT_SUB_W) * discount_val

            total = profit_score * PROFIT_W + growth_score * GROWTH_W + cfsafe_score * CFSAFE_W
            results[target_code] = (total, profit_score, growth_score, cfsafe_score)
        
        # 计算与Excel的差异
        d1 = results['301377.SZ']
        d2 = results['603061.SH']
        e1 = (73, 94.29, 60, 62.86)
        e2 = (70.5, 72.86, 60, 77.14)
        
        diff1 = abs(d1[0]-e1[0]) + abs(d1[1]-e1[1]) + abs(d1[2]-e1[2]) + abs(d1[3]-e1[3])
        diff2 = abs(d2[0]-e2[0]) + abs(d2[1]-e2[1]) + abs(d2[2]-e2[2]) + abs(d2[3]-e2[3])
        
        print(f"\n--- {label} ---")
        print(f"  鼎泰高科: 总{d1[0]:.2f}(Δ{d1[0]-e1[0]:+.2f}) 盈{d1[1]:.2f}(Δ{d1[1]-e1[1]:+.2f}) 成{d1[2]:.2f}(Δ{d1[2]-e1[2]:+.2f}) 现{d1[3]:.2f}(Δ{d1[3]-e1[3]:+.2f})")
        print(f"  金海通:   总{d2[0]:.2f}(Δ{d2[0]-e2[0]:+.2f}) 盈{d2[1]:.2f}(Δ{d2[1]-e2[1]:+.2f}) 成{d2[2]:.2f}(Δ{d2[2]-e2[2]:+.2f}) 现{d2[3]:.2f}(Δ{d2[3]-e2[3]:+.2f})")
        print(f"  总差异: {diff1+diff2:.2f}")
