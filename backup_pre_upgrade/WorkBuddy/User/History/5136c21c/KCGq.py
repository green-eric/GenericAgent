# -*- coding: utf-8 -*-
"""详细打印每项指标的百分位排名计算过程"""
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
        'total_score': row[3], 'profit_score': row[5], 'growth_score': row[6], 'cfsafe_score': row[7],
        'market_fallback': row[17],
    }
    all_stocks.append(stock)

# 只用有ROE数据的股票（19只）
pool = [s for s in all_stocks if s['roe'] is not None]
print(f"评分池: {len(pool)} 只（有ROE数据）")

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

# 打印每项指标的池子
print("\n=== 各指标评分池 ===")
for key, name in [('roe', 'ROE'), ('gross_margin', '毛利率'), ('net_margin', '净利率'),
                   ('revenue_yoy', '营收同比'), ('profit_yoy', '利润同比'),
                   ('ocf_to_profit', 'OCF/利润'), ('debt_ratio', '负债率')]:
    vals = pv(pool, key)
    if vals:
        print(f"\n{name} ({len(vals)} 只): min={min(vals):.2f} max={max(vals):.2f} avg={sum(vals)/len(vals):.2f}")
        sorted_vals = sorted(vals)
        for i, v in enumerate(sorted_vals):
            # 找到对应的股票
            stocks_with_v = [s['ts_code'] for s in pool if s.get(key) == v]
            print(f"  [{i:2d}] {v:8.2f} - {', '.join(stocks_with_v)}")

# 详细计算两只股票
for target_code in ['301377.SZ', '603061.SH']:
    target = next(s for s in pool if s['ts_code'] == target_code)
    print(f"\n{'='*70}")
    print(f"{target['name']} ({target_code})")
    print(f"Excel: 总{target['total_score']} 盈{target['profit_score']} 成{target['growth_score']} 现{target['cfsafe_score']} 备选={target['market_fallback']}")
    
    roe, gross, net = target['roe'], target['gross_margin'], target['net_margin']
    rev_yoy, prof_yoy = target['revenue_yoy'], target['profit_yoy']
    ocf, debt = target['ocf_to_profit'], target['debt_ratio']

    # ROE
    roe_pool = pv(pool, 'roe')
    roe_s = percentile_rank(roe, roe_pool) if roe is not None else 0.0
    roe_rank = sorted(roe_pool).index(roe) + 1 if roe in roe_pool else -1
    print(f"\n  ROE={roe} 池大小={len(roe_pool)} 排名={roe_rank}/{len(roe_pool)} 百分位={roe_s:.2f}")

    # 毛利率
    gross_pool = pv(pool, 'gross_margin')
    gross_s = percentile_rank(gross, gross_pool) if gross is not None else 0.0
    gross_rank = sorted(gross_pool).index(gross) + 1 if gross in gross_pool else -1
    print(f"  毛利率={gross} 池大小={len(gross_pool)} 排名={gross_rank}/{len(gross_pool)} 百分位={gross_s:.2f}")

    # 净利率
    net_pool = pv(pool, 'net_margin')
    net_s = percentile_rank(net, net_pool) if net is not None else 0.0
    net_rank = sorted(net_pool).index(net) + 1 if net in net_pool else -1
    print(f"  净利率={net} 池大小={len(net_pool)} 排名={net_rank}/{len(net_pool)} 百分位={net_s:.2f}")

    profit = roe_s * 0.4 + gross_s * 0.3 + net_s * 0.3
    print(f"  盈利(无折扣) = {roe_s:.2f}x0.4 + {gross_s:.2f}x0.3 + {net_s:.2f}x0.3 = {profit:.2f}")
    print(f"  盈利(折扣0.95) = {profit * 0.95:.2f}")
    print(f"  盈利(折扣1.0) = {profit * 1.0:.2f}")
    print(f"  Excel盈利 = {target['profit_score']}")

    # 营收同比
    rev_pool = pv(pool, 'revenue_yoy')
    rev_s = percentile_rank(rev_yoy, rev_pool) if rev_yoy is not None else 0.0
    print(f"\n  营收同比={rev_yoy} 池大小={len(rev_pool)} 百分位={rev_s:.2f}")

    # 利润同比
    prof_pool = pv(pool, 'profit_yoy')
    prof_s = percentile_rank(prof_yoy, prof_pool) if prof_yoy is not None else 0.0
    prof_rank = sorted(prof_pool).index(prof_yoy) + 1 if prof_yoy in prof_pool else -1
    print(f"  利润同比={prof_yoy} 池大小={len(prof_pool)} 排名={prof_rank}/{len(prof_pool)} 百分位={prof_s:.2f}")

    growth = rev_s * 0.4 + prof_s * 0.6
    print(f"  成长(无折扣) = {rev_s:.2f}x0.4 + {prof_s:.2f}x0.6 = {growth:.2f}")
    print(f"  成长(折扣0.95) = {growth * 0.95:.2f}")
    print(f"  成长(折扣1.0) = {growth * 1.0:.2f}")
    print(f"  Excel成长 = {target['growth_score']}")

    # OCF/利润
    ocf_pool = pv(pool, 'ocf_to_profit')
    ocf_s = percentile_rank(ocf, ocf_pool) if ocf is not None else 0.0
    ocf_rank = sorted(ocf_pool).index(ocf) + 1 if ocf in ocf_pool else -1
    print(f"\n  OCF/利润={ocf} 池大小={len(ocf_pool)} 排名={ocf_rank}/{len(ocf_pool)} 百分位={ocf_s:.2f}")

    # 负债率（reverse=True，越低越好）
    debt_pool = pv(pool, 'debt_ratio')
    debt_s = percentile_rank(debt, debt_pool, reverse=True) if debt is not None else 0.0
    debt_rank_desc = sorted(debt_pool, reverse=True).index(debt) + 1 if debt in debt_pool else -1
    print(f"  负债率={debt} 池大小={len(debt_pool)} 降序排名={debt_rank_desc}/{len(debt_pool)} 百分位={debt_s:.2f}")

    cfsafe = ocf_s * 0.4 + debt_s * 0.6
    print(f"  现金流(无折扣) = {ocf_s:.2f}x0.4 + {debt_s:.2f}x0.6 = {cfsafe:.2f}")
    print(f"  现金流(折扣0.95) = {cfsafe * 0.95:.2f}")
    print(f"  现金流(折扣1.0) = {cfsafe * 1.0:.2f}")
    print(f"  Excel现金流 = {target['cfsafe_score']}")

    # 总分
    for d in [1.0, 0.95]:
        total = profit * 0.35 * d + growth * 0.3 * d + cfsafe * 0.35 * d
        # 不对，应该是先算带折扣的子分项再加权
        total2 = (profit * d) * 0.35 + (growth * d) * 0.3 + (cfsafe * d) * 0.35
        print(f"\n  总分(折扣{d}) = {profit*d:.2f}x0.35 + {growth*d:.2f}x0.3 + {cfsafe*d:.2f}x0.35 = {total2:.2f}")
    print(f"  Excel总分 = {target['total_score']}")
