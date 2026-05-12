# -*- coding: utf-8 -*-
"""精确模拟主脚本逻辑：all_stocks_for_rank 包含所有codes的股票（含全None）"""
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

# 加载 stocks 表（所有28只）
all_stock_codes = set()
cur = conn.execute("SELECT ts_code, name FROM stocks")
stock_names = {}
for row in cur.fetchall():
    all_stock_codes.add(row["ts_code"])
    stock_names[row["ts_code"]] = row["name"]

print(f"stocks 表: {len(all_stock_codes)} 只")

# 加载年报和季报数据
annual_db = {}
cur = conn.execute("SELECT * FROM financial_reports WHERE report_type='annual' AND fetch_success=1 ORDER BY ts_code, report_date DESC")
for row in cur.fetchall():
    code = row["ts_code"]
    if code not in annual_db:
        annual_db[code] = dict(row)

quarterly_db = {}
cur = conn.execute("SELECT * FROM financial_reports WHERE report_type='quarterly' AND fetch_success=1 ORDER BY ts_code, report_date DESC")
for row in cur.fetchall():
    code = row["ts_code"]
    if code not in quarterly_db:
        quarterly_db[code] = dict(row)

print(f"年报数据: {len(annual_db)} 只, 季报数据: {len(quarterly_db)} 只")

# 构建 all_stocks_for_rank（完全模拟主脚本）
# 主脚本中 codes = list(set([r["ts_code"] for r in annual_data]))
# annual_data 包含所有 stocks（436只），不只是有数据的
# 但为简化，这里用 stocks 表中的28只（因为xuan.txt中只有这28只在stocks表中）
# 实际上 xuan.txt 有436只，但 stocks 表只有28只被插入

# 让我检查 xuan.txt 有多少只
with open(r'd:\Project\QAScorer\xuan.txt', 'r', encoding='utf-8', errors='ignore') as f:
    xuan_codes = [line.strip().split()[0] for line in f if line.strip() and not line.startswith('#')]
print(f"xuan.txt: {len(xuan_codes)} 只")

# 主脚本中 annual_data 包含所有 xuan.txt 中的股票
# all_stocks_for_rank 包含所有 annual_data 中的 codes
# 所以评分池大小 = xuan.txt 中的股票数（436只）
# 但只有19只数据库中有数据，其余全为None

# 构建评分池
all_stocks = []
for code in xuan_codes:
    arow = annual_db.get(code)
    qrow = quarterly_db.get(code)
    entry = {"ts_code": code}
    entry["roe"] = arow["roe"] if arow else None
    entry["gross_margin"] = qrow["gross_margin"] if qrow else (arow["gross_margin"] if arow else None)
    entry["net_margin"] = qrow["net_margin"] if qrow else (arow["net_margin"] if arow else None)
    entry["revenue_yoy"] = qrow["revenue_yoy"] if qrow else None
    entry["profit_yoy"] = qrow["profit_yoy"] if qrow else None
    entry["ocf_to_profit"] = arow["ocf_to_profit"] if arow else None
    entry["debt_ratio"] = arow["debt_ratio"] if arow else None
    all_stocks.append(entry)

print(f"评分池: {len(all_stocks)} 只")

# 行业分组（全部空行业 -> 一个组）
industry_groups = {"": all_stocks}

def pv(pool, key):
    return [s[key] for s in pool if s.get(key) is not None]

# 检查各指标的池大小
print("\n各指标有效数据量:")
for key, name in [('roe', 'ROE'), ('gross_margin', '毛利率'), ('net_margin', '净利率'),
                   ('revenue_yoy', '营收同比'), ('profit_yoy', '利润同比'),
                   ('ocf_to_profit', 'OCF/利润'), ('debt_ratio', '负债率')]:
    vals = pv(all_stocks, key)
    print(f"  {name}: {len(vals)} 只")

# 计算两只目标股票
for target_code in ['301377.SZ', '603061.SH']:
    target = next(s for s in all_stocks if s['ts_code'] == target_code)
    name = stock_names.get(target_code, target_code)
    
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
    print(f"    = {profit_score:.2f}")
    print(f"  成长: 营收同比={rev_yoy}->{rev_s:.2f} 利润同比={prof_yoy}->{prof_s:.2f}")
    print(f"    = {growth_score:.2f}")
    print(f"  现金流: OCF={ocf}->{ocf_s:.2f} 负债率={debt}->{debt_s:.2f}")
    print(f"    = {cfsafe_score:.2f}")
    print(f"\n  计算总分 = {total:.2f}")

    excel = {
        '301377.SZ': (73, 94.29, 60, 62.86),
        '603061.SH': (70.5, 72.86, 60, 77.14),
    }
    if target_code in excel:
        e = excel[target_code]
        print(f"\n  Excel: 总{e[0]} 盈{e[1]} 成{e[2]} 现{e[3]}")
        print(f"  差异: 总{total-e[0]:+.2f} 盈{profit_score-e[1]:+.2f} 成{growth_score-e[2]:+.2f} 现{cfsafe_score-e[3]:+.2f}")

conn.close()
