# -*- coding: utf-8 -*-
"""用Excel中的旧评分池（只有8只股票有ROE数据）验证评分逻辑"""
import sys, io, openpyxl
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

wb = openpyxl.load_workbook(r'd:\Project\QAScorer\综合评分_20260426_202924.xlsx')
ws = wb.active

# 读取Excel中的数据（这是旧运行的实际输出）
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

# 旧评分池：只有Excel中有数据的股票（8只）
# 这些是那次运行时数据库中有年报数据的股票
old_pool = [s for s in excel_stocks if s['roe'] is not None]
print(f"旧评分池（有ROE数据）: {len(old_pool)} 只")
for s in old_pool:
    print(f"  {s['ts_code']} {s['name']} ROE={s['roe']} 毛利率={s['gross_margin']} 净利率={s['net_margin']} 利润同比={s['profit_yoy']} OCF={s['ocf_to_profit']} 负债率={s['debt_ratio']}")

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

# 用旧评分池计算
pool = old_pool
discount = 1.0  # 8只 >= 5，不触发备选

for target_code in ['301377.SZ', '603061.SH']:
    target = next(s for s in excel_stocks if s['ts_code'] == target_code)
    print(f"\n{'='*60}")
    print(f"{target['name']} ({target_code})")
    print(f"Excel: 总{target['total_score']} 盈{target['profit_score']} 成{target['growth_score']} 现{target['cfsafe_score']}")
    
    roe = target['roe']
    gross = target['gross_margin']
    net = target['net_margin']
    rev_yoy = target['revenue_yoy']
    prof_yoy = target['profit_yoy']
    ocf = target['ocf_to_profit']
    debt = target['debt_ratio']

    roe_s = 0.0 if roe is None else (0.0 if roe < 0 else percentile_rank(roe, pv(pool, 'roe')))
    gross_s = percentile_rank(gross, pv(pool, 'gross_margin')) if gross is not None else 0.0
    net_s = percentile_rank(net, pv(pool, 'net_margin')) if net is not None else 0.0
    profit_score = (roe_s * ROE_SUB_W + gross_s * GROSS_SUB_W + net_s * NET_SUB_W) * discount

    rev_s = percentile_rank(rev_yoy, pv(pool, 'revenue_yoy')) if rev_yoy is not None else 0.0
    prof_s = percentile_rank(prof_yoy, pv(pool, 'profit_yoy')) if prof_yoy is not None else 0.0
    growth_score = (rev_s * REV_YOY_SUB_W + prof_s * PROF_YOY_SUB_W) * discount

    ocf_s = percentile_rank(ocf, pv(pool, 'ocf_to_profit')) if ocf is not None else 0.0
    debt_s = percentile_rank(debt, pv(pool, 'debt_ratio'), reverse=True) if debt is not None else 0.0
    cfsafe_score = (ocf_s * OCF_SUB_W + debt_s * DEBT_SUB_W) * discount

    total = profit_score * PROFIT_W + growth_score * GROWTH_W + cfsafe_score * CFSAFE_W

    print(f"\n  盈利: ROE={roe}->{roe_s:.2f} 毛利率={gross}->{gross_s:.2f} 净利率={net}->{net_s:.2f}")
    print(f"    = {profit_score:.2f} (Excel: {target['profit_score']})")
    print(f"  成长: 营收同比={rev_yoy}->{rev_s:.2f} 利润同比={prof_yoy}->{prof_s:.2f}")
    print(f"    = {growth_score:.2f} (Excel: {target['growth_score']})")
    print(f"  现金流: OCF={ocf}->{ocf_s:.2f} 负债率={debt}->{debt_s:.2f}")
    print(f"    = {cfsafe_score:.2f} (Excel: {target['cfsafe_score']})")
    print(f"\n  计算总分 = {total:.2f} (Excel: {target['total_score']})")
    print(f"  差异: 总{total-target['total_score']:+.2f} 盈{profit_score-target['profit_score']:+.2f} 成{growth_score-target['growth_score']:+.2f} 现{cfsafe_score-target['cfsafe_score']:+.2f}")
