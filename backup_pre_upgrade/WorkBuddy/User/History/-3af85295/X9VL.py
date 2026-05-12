# -*- coding: utf-8 -*-
"""用数据库中的19只股票数据，完全模拟主脚本逻辑进行验算"""
import sys, io, sqlite3
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

DB_FILE = r'd:\Project\QAScorer\stock_cache.db'

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

conn = sqlite3.connect(DB_FILE)
conn.row_factory = sqlite3.Row

# 加载年报数据（与主脚本完全一致）
annual_data_db = {}
cur = conn.execute("SELECT * FROM financial_reports WHERE report_type='annual' AND fetch_success=1 ORDER BY ts_code, report_date DESC")
for row in cur.fetchall():
    code = row["ts_code"]
    if code not in annual_data_db:
        annual_data_db[code] = dict(row)

# 加载季报数据
quarterly_data = {}
cur = conn.execute("SELECT * FROM financial_reports WHERE report_type='quarterly' AND fetch_success=1 ORDER BY ts_code, report_date DESC")
for row in cur.fetchall():
    code = row["ts_code"]
    if code not in quarterly_data:
        quarterly_data[code] = dict(row)

# 加载股票名称和行业
stock_info = {}
cur = conn.execute("SELECT ts_code, name FROM stocks")
for row in cur.fetchall():
    stock_info[row["ts_code"]] = {"name": row["name"], "industry_l1": ""}

print(f"年报数据: {len(annual_data_db)} 只")
print(f"季报数据: {len(quarterly_data)} 只")

# 构建 all_stocks_for_rank（与主脚本完全一致）
# codes 来自 annual_data（所有股票），但只有数据库中有记录的非None
all_codes = set(annual_data_db.keys()) | set(quarterly_data.keys())
# 实际上主脚本中 codes = list(set([r["ts_code"] for r in annual_data]))
# annual_data 包含所有436只股票，但只有19只fetch_success=True
# 对于fetch_success=False的股票，arow=None（因为annual_data_db中无记录）
# 但 all_stocks_for_rank 仍然包含它们（所有字段为None）

# 为简化，只构建有数据的股票（None股票不影响pv结果）
all_stocks = []
for code in all_codes:
    arow = annual_data_db.get(code)
    qrow = quarterly_data.get(code)
    entry = {"ts_code": code}
    entry["roe"] = arow["roe"] if arow else None
    entry["gross_margin"] = qrow["gross_margin"] if qrow else (arow["gross_margin"] if arow else None)
    entry["net_margin"] = qrow["net_margin"] if qrow else (arow["net_margin"] if arow else None)
    entry["revenue_yoy"] = qrow["revenue_yoy"] if qrow else None
    entry["profit_yoy"] = qrow["profit_yoy"] if qrow else None
    entry["ocf_to_profit"] = arow["ocf_to_profit"] if arow else None
    entry["debt_ratio"] = arow["debt_ratio"] if arow else None
    all_stocks.append(entry)

# 添加 stocks 表中有但数据库中没有的股票（全None，不影响pv）
for code in stock_info:
    if code not in all_codes:
        entry = {"ts_code": code, "roe": None, "gross_margin": None, "net_margin": None,
                 "revenue_yoy": None, "profit_yoy": None, "ocf_to_profit": None, "debt_ratio": None}
        all_stocks.append(entry)

print(f"评分池: {len(all_stocks)} 只（含全None股票）")

# 行业分组（全部为空行业）
industry_groups = {}
for s in all_stocks:
    ind = ""  # 简化：全部空行业
    industry_groups.setdefault(ind, []).append(s)

def pv(pool, key):
    return [s[key] for s in pool if s.get(key) is not None]

# 计算两只目标股票
for target_code in ['301377.SZ', '603061.SH']:
    target = next(s for s in all_stocks if s['ts_code'] == target_code)
    name = stock_info.get(target_code, {}).get('name', '')
    
    # 行业池（全部空行业，8只>=5，不触发备选）
    ind = ""
    pool = industry_groups.get(ind, [])
    use_fallback = len(pool) < 5
    discount = 0.95 if use_fallback else 1.0
    
    print(f"\n{'='*60}")
    print(f"{name} ({target_code}): 行业池={len(pool)}只, use_fallback={use_fallback}, discount={discount}")
    
    roe = target['roe']
    gross = target['gross_margin']
    net = target['net_margin']
    rev_yoy = target['revenue_yoy']
    prof_yoy = target['profit_yoy']
    ocf = target['ocf_to_profit']
    debt = target['debt_ratio']
    
    print(f"  数据: ROE={roe} 毛利率={gross} 净利率={net} 营收同比={rev_yoy} 利润同比={prof_yoy} OCF={ocf} 负债率={debt}")

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
    print(f"    = ({roe_s:.2f}x0.4 + {gross_s:.2f}x0.3 + {net_s:.2f}x0.3) x {discount} = {profit_score:.2f}")
    print(f"  成长: 营收同比={rev_yoy}->{rev_s:.2f} 利润同比={prof_yoy}->{prof_s:.2f}")
    print(f"    = ({rev_s:.2f}x0.4 + {prof_s:.2f}x0.6) x {discount} = {growth_score:.2f}")
    print(f"  现金流: OCF={ocf}->{ocf_s:.2f} 负债率={debt}->{debt_s:.2f}")
    print(f"    = ({ocf_s:.2f}x0.4 + {debt_s:.2f}x0.6) x {discount} = {cfsafe_score:.2f}")
    print(f"\n  计算总分 = {profit_score:.2f}x0.35 + {growth_score:.2f}x0.3 + {cfsafe_score:.2f}x0.35 = {total:.2f}")

    # Excel 对比
    excel = {
        '301377.SZ': (73, 94.29, 60, 62.86),
        '603061.SH': (70.5, 72.86, 60, 77.14),
    }
    if target_code in excel:
        e = excel[target_code]
        print(f"\n  Excel: 总{e[0]} 盈{e[1]} 成{e[2]} 现{e[3]}")
        print(f"  差异: 总{total-e[0]:+.2f} 盈{profit_score-e[1]:+.2f} 成{growth_score-e[2]:+.2f} 现{cfsafe_score-e[3]:+.2f}")

conn.close()
