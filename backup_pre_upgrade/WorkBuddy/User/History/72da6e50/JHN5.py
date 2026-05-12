# -*- coding: utf-8 -*-
"""直接从数据库读取评分池，验算鼎泰高科和金海通的评分"""
import sys, io, sqlite3, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

DB_FILE = r'd:\Project\QAScorer\stock_cache.db'

PROFIT_W, GROWTH_W, CFSAFE_W = 0.35, 0.30, 0.35
ROE_SUB_W, GROSS_SUB_W, NET_SUB_W = 0.40, 0.30, 0.30
REV_YOY_SUB_W, PROF_YOY_SUB_W = 0.40, 0.60
OCF_SUB_W, DEBT_SUB_W = 0.40, 0.60
MARKET_FALLBACK_DISC = 0.95
MIN_INDUSTRY_SAMPLES = 5

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

# 读取数据库
conn = sqlite3.connect(DB_FILE)
conn.row_factory = sqlite3.Row

# 加载所有年报数据（fetch_success=1）
annual_rows = {}
cur = conn.execute("SELECT * FROM financial_reports WHERE report_type='annual' AND fetch_success=1 ORDER BY ts_code, report_date DESC")
for row in cur.fetchall():
    code = row["ts_code"]
    if code not in annual_rows:
        annual_rows[code] = dict(row)

# 加载所有季报数据（fetch_success=1）
quarterly_rows = {}
cur = conn.execute("SELECT * FROM financial_reports WHERE report_type='quarterly' AND fetch_success=1 ORDER BY ts_code, report_date DESC")
for row in cur.fetchall():
    code = row["ts_code"]
    if code not in quarterly_rows:
        quarterly_rows[code] = dict(row)

# 加载股票名称
stock_names = {}
cur = conn.execute("SELECT ts_code, name FROM stocks")
for row in cur.fetchall():
    stock_names[row["ts_code"]] = row["name"]

print(f"数据库中有效年报: {len(annual_rows)} 只")
print(f"数据库中有效季报: {len(quarterly_rows)} 只")

# 构建 all_stocks_for_rank（与主脚本逻辑一致）
all_codes = set(annual_rows.keys())
all_stocks = []
for code in all_codes:
    arow = annual_rows.get(code)
    qrow = quarterly_rows.get(code)
    entry = {"ts_code": code}
    entry["roe"] = arow["roe"] if arow else None
    entry["gross_margin"] = qrow["gross_margin"] if qrow else (arow["gross_margin"] if arow else None)
    entry["net_margin"] = qrow["net_margin"] if qrow else (arow["net_margin"] if arow else None)
    entry["revenue_yoy"] = qrow["revenue_yoy"] if qrow else None
    entry["profit_yoy"] = qrow["profit_yoy"] if qrow else None
    entry["ocf_to_profit"] = arow["ocf_to_profit"] if arow else None
    entry["debt_ratio"] = arow["debt_ratio"] if arow else None
    all_stocks.append(entry)

print(f"评分池大小: {len(all_stocks)} 只")

# 打印评分池中所有股票的关键字段
print(f"\n{'代码':<12} {'名称':<8} {'ROE':>8} {'毛利率':>8} {'净利率':>8} {'营收同比':>8} {'利润同比':>8} {'OCF/利润':>8} {'负债率':>8}")
print("-" * 100)
for s in all_stocks:
    name = stock_names.get(s['ts_code'], '')
    print(f"{s['ts_code']:<12} {name:<8} {str(s['roe']):>8} {str(s['gross_margin']):>8} {str(s['net_margin']):>8} {str(s['revenue_yoy']):>8} {str(s['profit_yoy']):>8} {str(s['ocf_to_profit']):>8} {str(s['debt_ratio']):>8}")

# 行业分组（简化：全部用全市场备选）
industry_groups = {}
for s in all_stocks:
    ind = ""  # 简化：全部用空行业
    industry_groups.setdefault(ind, []).append(s)

def pv(pool, key):
    return [s[key] for s in pool if s.get(key) is not None]

# 对两只目标股票分别计算
for target_code in ['301377.SZ', '603061.SH']:
    target = next((s for s in all_stocks if s['ts_code'] == target_code), None)
    if target is None:
        print(f"\n{target_code} 不在评分池中！")
        continue

    name = stock_names.get(target_code, '')
    pool = all_stocks  # 全市场备选
    discount = MARKET_FALLBACK_DISC

    roe = target['roe']
    gross = target['gross_margin']
    net = target['net_margin']
    rev_yoy = target['revenue_yoy']
    prof_yoy = target['profit_yoy']
    ocf = target['ocf_to_profit']
    debt = target['debt_ratio']

    print(f"\n{'='*60}")
    print(f"{name} ({target_code}): 评分池={len(pool)}只, 折扣={discount}")
    print(f"  原始数据: ROE={roe} 毛利率={gross} 净利率={net} 营收同比={rev_yoy} 利润同比={prof_yoy} OCF/利润={ocf} 负债率={debt}")

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

    print(f"\n  盈利: ROE={roe}->{roe_s:.1f} 毛利率={gross}->{gross_s:.1f} 净利率={net}->{net_s:.1f}")
    print(f"    = ({roe_s:.1f}x{ROE_SUB_W} + {gross_s:.1f}x{GROSS_SUB_W} + {net_s:.1f}x{NET_SUB_W}) x {discount} = {profit_score:.2f}")
    print(f"  成长: 营收同比={rev_yoy}->{rev_s:.1f} 利润同比={prof_yoy}->{prof_s:.1f}")
    print(f"    = ({rev_s:.1f}x{REV_YOY_SUB_W} + {prof_s:.1f}x{PROF_YOY_SUB_W}) x {discount} = {growth_score:.2f}")
    print(f"  现金流: OCF/利润={ocf}->{ocf_s:.1f} 负债率={debt}->{debt_s:.1f}")
    print(f"    = ({ocf_s:.1f}x{OCF_SUB_W} + {debt_s:.1f}x{DEBT_SUB_W}) x {discount} = {cfsafe_score:.2f}")
    print(f"\n  计算总分 = {profit_score:.2f}x{PROFIT_W} + {growth_score:.2f}x{GROWTH_W} + {cfsafe_score:.2f}x{CFSAFE_W} = {total:.2f}")

    # Excel 数据
    excel_scores = {
        '301377.SZ': {'total': 73, 'profit': 94.29, 'growth': 60, 'cfsafe': 62.86},
        '603061.SH': {'total': 70.5, 'profit': 72.86, 'growth': 60, 'cfsafe': 77.14},
    }
    if target_code in excel_scores:
        e = excel_scores[target_code]
        print(f"\n  Excel总分 = {e['total']}, 盈利={e['profit']}, 成长={e['growth']}, 现金流={e['cfsafe']}")
        print(f"  总分差异 = {abs(total - e['total']):.2f}")
        print(f"  盈利差异 = {abs(profit_score - e['profit']):.2f}")
        print(f"  成长差异 = {abs(growth_score - e['growth']):.2f}")
        print(f"  现金流差异 = {abs(cfsafe_score - e['cfsafe']):.2f}")

conn.close()
