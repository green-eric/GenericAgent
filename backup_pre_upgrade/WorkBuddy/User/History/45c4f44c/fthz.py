"""手动验算鼎泰高科(301377)和金海通(603061)的评分"""
import openpyxl

wb = openpyxl.load_workbook(r'd:\Project\QAScorer\综合评分_20260426_202924.xlsx')
ws = wb.active

all_stocks = []
for row in ws.iter_rows(min_row=2, values_only=True):
    if row[0] is None:
        break
    stock = {
        'ts_code': row[0], 'name': row[1],
        'industry': row[2], 'total_score': row[3], 'grade': row[4],
        'profit_score': row[5], 'growth_score': row[6], 'cfsafe_score': row[7],
        'roe': row[8], 'gross_margin': row[9], 'net_margin': row[10],
        'revenue_yoy': row[11], 'profit_yoy': row[12],
        'ocf_to_profit': row[13], 'debt_ratio': row[14],
        'confidence': row[15], 'quarterly_date': row[16],
        'market_fallback': row[17],
    }
    all_stocks.append(stock)

# 打印全部股票的关键字段
print(f"{'代码':<12} {'名称':<8} {'行业':<10} {'总分':>6} {'等级':>4} {'盈利':>6} {'成长':>6} {'现金流':>6} {'ROE':>8} {'毛利率':>8} {'净利率':>8} {'营收同比':>8} {'利润同比':>8} {'OCF/利润':>8} {'负债率':>8} {'备选':>4}")
print("-" * 140)
for s in all_stocks:
    ind = str(s['industry']) if s['industry'] else 'None'
    print(f"{s['ts_code']:<12} {s['name']:<8} {ind:<10} {s['total_score']:>6} {s['grade']:>4} {s['profit_score']:>6} {s['growth_score']:>6} {s['cfsafe_score']:>6} {str(s['roe']):>8} {str(s['gross_margin']):>8} {str(s['net_margin']):>8} {str(s['revenue_yoy']):>8} {str(s['profit_yoy']):>8} {str(s['ocf_to_profit']):>8} {str(s['debt_ratio']):>8} {str(s['market_fallback']):>4}")

# ========== 手动验算 ==========
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
    return min((lo / (n - 1)) * 100.0, 100.0)

def pv(pool, key): return [s[key] for s in pool if s.get(key) is not None]

# 确定评分池：行业=None → 全市场备选
# 查看行业分布
industries = {}
for s in all_stocks:
    ind = s['industry'] if s['industry'] else 'None'
    industries.setdefault(ind, []).append(s['ts_code'])

print(f"\n行业分布:")
for ind, codes in sorted(industries.items()):
    print(f"  {ind}: {len(codes)} 只 → {codes}")

# 对两只目标股票分别计算
for target_code in ['301377.SZ', '603061.SH']:
    target = next(s for s in all_stocks if s['ts_code'] == target_code)
    ind = target['industry'] if target['industry'] else 'None'
    
    # 行业池
    if ind != 'None' and len(industries.get(ind, [])) >= 5:
        pool = [s for s in all_stocks if (s['industry'] or 'None') == ind]
        discount = 1.0
        print(f"\n{'='*60}")
        print(f"{target['name']} ({target_code}): 行业='{ind}', 池大小={len(pool)}, 折扣=1.0")
    else:
        pool = all_stocks
        discount = 0.95
        print(f"\n{'='*60}")
        print(f"{target['name']} ({target_code}): 行业='{ind}' → 全市场备选, 池大小={len(pool)}, 折扣=0.95")
    
    roe, gross, net = target['roe'], target['gross_margin'], target['net_margin']
    rev_yoy, prof_yoy = target['revenue_yoy'], target['profit_yoy']
    ocf, debt = target['ocf_to_profit'], target['debt_ratio']
    
    # 盈利
    roe_s = 0.0 if roe is None else (0.0 if roe < 0 else percentile_rank(roe, pv(pool, 'roe')))
    gross_s = percentile_rank(gross, pv(pool, 'gross_margin')) if gross is not None else 0.0
    net_s = percentile_rank(net, pv(pool, 'net_margin')) if net is not None else 0.0
    profit_score = (roe_s * ROE_SUB_W + gross_s * GROSS_SUB_W + net_s * NET_SUB_W) * discount
    
    # 成长
    rev_s = percentile_rank(rev_yoy, pv(pool, 'revenue_yoy')) if rev_yoy is not None else 0.0
    prof_s = percentile_rank(prof_yoy, pv(pool, 'profit_yoy')) if prof_yoy is not None else 0.0
    growth_score = (rev_s * REV_YOY_SUB_W + prof_s * PROF_YOY_SUB_W) * discount
    
    # 现金流安全
    ocf_s = percentile_rank(ocf, pv(pool, 'ocf_to_profit')) if ocf is not None else 0.0
    debt_s = percentile_rank(debt, pv(pool, 'debt_ratio'), reverse=True) if debt is not None else 0.0
    cfsafe_score = (ocf_s * OCF_SUB_W + debt_s * DEBT_SUB_W) * discount
    
    total = profit_score * PROFIT_W + growth_score * GROWTH_W + cfsafe_score * CFSAFE_W
    
    print(f"\n  盈利得分: ROE={roe}→{roe_s:.1f} 毛利率={gross}→{gross_s:.1f} 净利率={net}→{net_s:.1f}")
    print(f"    = ({roe_s:.1f}×{ROE_SUB_W} + {gross_s:.1f}×{GROSS_SUB_W} + {net_s:.1f}×{NET_SUB_W}) × {discount} = {profit_score:.2f}")
    print(f"  成长得分: 营收同比={rev_yoy}→{rev_s:.1f} 利润同比={prof_yoy}→{prof_s:.1f}")
    print(f"    = ({rev_s:.1f}×{REV_YOY_SUB_W} + {prof_s:.1f}×{PROF_YOY_SUB_W}) × {discount} = {growth_score:.2f}")
    print(f"  现金流安全: OCF/利润={ocf}→{ocf_s:.1f} 负债率={debt}→{debt_s:.1f}")
    print(f"    = ({ocf_s:.1f}×{OCF_SUB_W} + {debt_s:.1f}×{DEBT_SUB_W}) × {discount} = {cfsafe_score:.2f}")
    print(f"\n  计算总分 = {profit_score:.2f}×{PROFIT_W} + {growth_score:.2f}×{GROWTH_W} + {cfsafe_score:.2f}×{CFSAFE_W} = {total:.2f}")
    print(f"  Excel总分 = {target['total_score']}")
    match = abs(total - target['total_score']) < 0.1
    print(f"  差异 = {abs(total - target['total_score']):.4f} {'[OK] 一致' if match else '[FAIL] 不一致'}")
