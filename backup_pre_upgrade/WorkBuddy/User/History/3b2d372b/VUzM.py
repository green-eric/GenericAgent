"""
从缓存数据库读取宏和科技及同行业数据，完整展示评分计算过程
"""
import sys, os, sqlite3, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from annual_scorer import (
    parse_financial_all, calc_completeness, percentile_rank, Config
)

TARGET = "603256.SH"
DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stock_cache.db")

# 读取缓存
conn = sqlite3.connect(DB_FILE)
conn.row_factory = sqlite3.Row

# 获取宏和科技的最新年报数据
row = conn.execute(
    "SELECT * FROM annual_reports WHERE ts_code = ? ORDER BY report_date DESC LIMIT 1",
    (TARGET,)
).fetchone()

if not row:
    print(f"❌ 数据库中没有 {TARGET} 的数据")
    conn.close()
    sys.exit(1)

# 解析指标
metrics = json.loads(row["metrics"]) if row["metrics"] else {}
report_date = row["report_date"]
fetch_success = row["success"]

print("=" * 60)
print(f"【宏和科技 603256.SH】完整评分计算过程")
print(f"数据来源: 缓存数据库 | 年报日期: {report_date}")
print("=" * 60)

# 核心指标
core_keys = ["roe", "gross_margin", "net_margin", "revenue_yoy",
             "profit_yoy", "debt_ratio", "net_profit", "ocf_abs"]
key_names = {
    "roe": "ROE(%)", "gross_margin": "毛利率(%)", "net_margin": "净利率(%)",
    "revenue_yoy": "营收同比(%)", "profit_yoy": "归母净利润同比(%)",
    "debt_ratio": "资产负债率(%)", "net_profit": "归母净利润(元)", "ocf_abs": "经营现金流(元)"
}

print("\n📋 Step 1：核心指标（从缓存读取）")
print("-" * 45)
for k in core_keys:
    v = metrics.get(k)
    status = "✅" if v is not None else "❌缺失"
    print(f"  {status} {key_names[k]}: {v}")

# 置信度
completeness, level = calc_completeness(metrics)
non_null = sum(1 for m in core_keys if metrics.get(m) is not None)
print(f"\n📊 Step 2：置信度")
print("-" * 45)
print(f"  8个核心指标: {non_null}个有值, {8-non_null}个缺失")
print(f"  完整度 = {non_null}/8 = {completeness:.3f} = {completeness*100:.1f}%")
print(f"  判定规则:")
print(f"    ≥85.7% (≥7/8) → high (高置信度)")
print(f"    ≥57.1% (≥4/8) → medium (中置信度)")
print(f"    ≤1个指标     → ultra_low (极低)")
print(f"    其他         → low (低置信度)")
conf_map = {"high": "高", "medium": "中", "low": "低", "ultra_low": "低"}
print(f"  → 等级: {level} → 置信度: 【{conf_map[level]}】")

# 获取行业
ind_row = conn.execute(
    "SELECT industry_l1 FROM stock_industries WHERE ts_code = ?", (TARGET,)
).fetchone()
industry = ind_row["industry_l1"] if ind_row else None

print(f"\n🏭 Step 3：行业判定")
print("-" * 45)
print(f"  宏和科技行业: {industry}")

# 获取同行业所有股票的最新年报
peer_rows = []
if industry:
    peer_rows = conn.execute("""
        SELECT r.ts_code, r.metrics, r.report_date, r.success, s.name
        FROM annual_reports r
        JOIN stock_industries si ON r.ts_code = si.ts_code
        LEFT JOIN (
            SELECT ts_code, name FROM annual_reports WHERE success=1 GROUP BY ts_code HAVING MAX(report_date)
        ) s ON r.ts_code = s.ts_code
        WHERE si.industry_l1 = ? AND r.success = 1 AND r.ts_code != ?
        GROUP BY r.ts_code
        HAVING r.report_date = MAX(r.report_date)
    """, (industry, TARGET)).fetchall()

print(f"  同行业股票池: {len(peer_rows)}只（不含自身）")

# 解析同行业数据
pool = []
for pr in peer_rows:
    m = json.loads(pr["metrics"]) if pr["metrics"] else {}
    m["ts_code"] = pr["ts_code"]
    pool.append(m)

use_market_fallback = len(pool) < Config.MIN_INDUSTRY_SAMPLES
discount = Config.MARKET_FALLBACK_DISCOUNT if use_market_fallback else 1.0

if use_market_fallback:
    print(f"  同行业{len(pool)}只 < {Config.MIN_INDUSTRY_SAMPLES} → 全市场池 × {Config.MARKET_FALLBACK_DISCOUNT}")
    # 获取全市场数据
    all_rows = conn.execute("""
        SELECT r.ts_code, r.metrics, r.report_date, r.success
        FROM annual_reports r
        WHERE r.success = 1 AND r.ts_code != ?
        GROUP BY r.ts_code
        HAVING r.report_date = MAX(r.report_date)
    """, (TARGET,)).fetchall()
    pool = []
    for pr in all_rows:
        m = json.loads(pr["metrics"]) if pr["metrics"] else {}
        m["ts_code"] = pr["ts_code"]
        pool.append(m)
    print(f"  全市场池: {len(pool)}只")
else:
    print(f"  同行业{len(pool)}只 ≥ {Config.MIN_INDUSTRY_SAMPLES} → 同行业池 × 1.0")

def pool_values(key):
    return [s[key] for s in pool if s.get("ts_code") != TARGET and s.get(key) is not None]

# ========== 盈利能力 ==========
print(f"\n💪 Step 4：盈利能力（权重40%）")
print("-" * 45)
print(f"  公式: ROE×0.4 + 毛利率×0.3 + 净利率×0.3")

roe_v = metrics.get("roe")
gm_v = metrics.get("gross_margin")
nm_v = metrics.get("net_margin")

roe_score = 0.0
if roe_v is not None and roe_v >= 0:
    vals = pool_values("roe")
    roe_score = percentile_rank(roe_v, vals)
    print(f"\n  ① ROE = {roe_v}%")
    print(f"    对比池: {len(vals)}只")
    count_leq = sum(1 for v in vals if v <= roe_v)
    print(f"    count_leq(≤{roe_v}) = {count_leq}")
    print(f"    百分位 = {count_leq}/{len(vals)}×100 = {roe_score:.2f}")
else:
    print(f"\n  ① ROE = {roe_v} → 0分" + ("(负值不计分)" if roe_v is not None and roe_v < 0 else "(缺失)"))

gm_score = 0.0
if gm_v is not None:
    vals = pool_values("gross_margin")
    gm_score = percentile_rank(gm_v, vals)
    count_leq = sum(1 for v in vals if v <= gm_v)
    print(f"\n  ② 毛利率 = {gm_v}%")
    print(f"    对比池: {len(vals)}只, count_leq={count_leq}")
    print(f"    百分位 = {gm_score:.2f}")
else:
    print(f"\n  ② 毛利率 = 缺失 → 0分")

nm_score = 0.0
if nm_v is not None:
    vals = pool_values("net_margin")
    nm_score = percentile_rank(nm_v, vals)
    count_leq = sum(1 for v in vals if v <= nm_v)
    print(f"\n  ③ 净利率 = {nm_v}%")
    print(f"    对比池: {len(vals)}只, count_leq={count_leq}")
    print(f"    百分位 = {nm_score:.2f}")
else:
    print(f"\n  ③ 净利率 = 缺失 → 0分")

profit_raw = roe_score * 0.4 + gm_score * 0.3 + nm_score * 0.3
profit_score = profit_raw * discount
print(f"\n  盈利能力 = {roe_score:.2f}×0.4 + {gm_score:.2f}×0.3 + {nm_score:.2f}×0.3")
print(f"           = {roe_score*0.4:.2f} + {gm_score*0.3:.2f} + {nm_score*0.3:.2f}")
print(f"           = {profit_raw:.2f}")
if discount < 1.0:
    print(f"  × 折扣{discount} = {profit_score:.2f}")
print(f"  → 盈利能力 = 【{profit_score:.2f}】")

# ========== 成长性 ==========
print(f"\n📈 Step 5：成长性（权重30%）")
print("-" * 45)
print(f"  公式: 营收同比×0.4 + 净利同比×0.6")

rev_v = metrics.get("revenue_yoy")
prof_v = metrics.get("profit_yoy")

rev_score = 0.0
if rev_v is not None:
    vals = pool_values("revenue_yoy")
    rev_score = percentile_rank(rev_v, vals)
    count_leq = sum(1 for v in vals if v <= rev_v)
    print(f"\n  ① 营收同比 = {rev_v}%")
    print(f"    对比池: {len(vals)}只, count_leq={count_leq}")
    print(f"    百分位 = {rev_score:.2f}")
else:
    print(f"\n  ① 营收同比 = 缺失 → 0分")

prof_score = 0.0
if prof_v is not None:
    vals = pool_values("profit_yoy")
    prof_score = percentile_rank(prof_v, vals)
    count_leq = sum(1 for v in vals if v <= prof_v)
    print(f"\n  ② 净利同比 = {prof_v}%")
    print(f"    对比池: {len(vals)}只, count_leq={count_leq}")
    print(f"    百分位 = {prof_score:.2f}")
else:
    print(f"\n  ② 净利同比 = 缺失 → 0分")

growth_raw = rev_score * 0.4 + prof_score * 0.6
growth_score = growth_raw * discount
print(f"\n  成长性 = {rev_score:.2f}×0.4 + {prof_score:.2f}×0.6")
print(f"         = {rev_score*0.4:.2f} + {prof_score*0.6:.2f}")
print(f"         = {growth_raw:.2f}")
if discount < 1.0:
    print(f"  × 折扣{discount} = {growth_score:.2f}")
print(f"  → 成长性 = 【{growth_score:.2f}】")

# ========== 现金流质量 ==========
print(f"\n💰 Step 6：现金流质量（权重20%）")
print("-" * 45)
print(f"  公式: OCF/净利润 × 100% → 百分位排名")

np_val = metrics.get("net_profit")
ocf_abs_val = metrics.get("ocf_abs")

ocf_ratio = None
if np_val and ocf_abs_val and np_val != 0:
    ocf_ratio = round(ocf_abs_val / np_val * 100, 2)
    print(f"  归母净利润 = {np_val:,.0f} 元")
    print(f"  经营现金流 = {ocf_abs_val:,.0f} 元")
    print(f"  OCF/净利润 = {ocf_abs_val:,.0f} / {np_val:,.0f} × 100% = {ocf_ratio}%")
else:
    print(f"  ❌ 数据不足 (净利润={np_val}, OCF={ocf_abs_val})")

pool_ocf_vals = []
for s in pool:
    s_np = s.get("net_profit")
    s_ocf = s.get("ocf_abs")
    if s_np and s_ocf and s_np != 0:
        pool_ocf_vals.append(round(s_ocf / s_np * 100, 2))

ocf_pct_score = 0.0
if ocf_ratio is not None and pool_ocf_vals:
    ocf_pct_score = percentile_rank(ocf_ratio, pool_ocf_vals)
    count_leq = sum(1 for v in pool_ocf_vals if v <= ocf_ratio)
    print(f"  对比池: {len(pool_ocf_vals)}只")
    print(f"  count_leq(≤{ocf_ratio}) = {count_leq}")
    print(f"  百分位 = {ocf_pct_score:.2f}")
elif ocf_ratio is not None:
    ocf_pct_score = 50.0
    print(f"  无对比数据 → 默认50分")
else:
    print(f"  → 0分")

ocf_score = ocf_pct_score * discount
if discount < 1.0:
    print(f"  × 折扣{discount} = {ocf_score:.2f}")
print(f"  → 现金流质量 = 【{ocf_score:.2f}】")

# ========== 偿债风险 ==========
print(f"\n🛡️ Step 7：偿债风险（权重10%）")
print("-" * 45)
print(f"  公式: 资产负债率 → 反向百分位（越低越好）")

debt_v = metrics.get("debt_ratio")
debt_score_val = 0.0
if debt_v is not None:
    vals = pool_values("debt_ratio")
    debt_score_val = percentile_rank(debt_v, vals, reverse=True)
    count_leq = sum(1 for v in vals if v <= debt_v)
    print(f"  资产负债率 = {debt_v}%")
    print(f"  对比池: {len(vals)}只")
    print(f"  count_leq(≤{debt_v}) = {count_leq}")
    print(f"  反向百分位 = ({len(vals)}-{count_leq})/{len(vals)}×100 = {debt_score_val:.2f}")
else:
    print(f"  资产负债率 = 缺失 → 0分")

debt_score = debt_score_val * discount
if discount < 1.0:
    print(f"  × 折扣{discount} = {debt_score:.2f}")
print(f"  → 偿债风险 = 【{debt_score:.2f}】")

# ========== 总分 ==========
print(f"\n" + "=" * 60)
print(f"📊 Step 8：汇总总分")
print("=" * 60)
print(f"  盈利能力:   {profit_score:.2f} × 40% = {profit_score*0.4:.2f}")
print(f"  成长性:     {growth_score:.2f} × 30% = {growth_score*0.3:.2f}")
print(f"  现金流质量: {ocf_score:.2f} × 20% = {ocf_score*0.2:.2f}")
print(f"  偿债风险:   {debt_score:.2f} × 10% = {debt_score*0.1:.2f}")

total = profit_score*0.4 + growth_score*0.3 + ocf_score*0.2 + debt_score*0.1
print(f"\n  原始总分 = {profit_score*0.4:.2f} + {growth_score*0.3:.2f} + {ocf_score*0.2:.2f} + {debt_score*0.1:.2f}")
print(f"          = {total:.2f}")

# 完整度折扣
if level == "low":
    total *= Config.LOW_COMPLETENESS_PENALTY
    print(f"  完整度折扣(low): ×{Config.LOW_COMPLETENESS_PENALTY} = {total:.2f}")
elif level == "ultra_low":
    total *= Config.LOW_COMPLETENESS_PENALTY * Config.ULTRA_LOW_COMPLETENESS_PENALTY
    print(f"  完整度折扣(ultra_low): ×{Config.LOW_COMPLETENESS_PENALTY * Config.ULTRA_LOW_COMPLETENESS_PENALTY} = {total:.2f}")

# 连续亏损惩罚
if np_val is not None and ocf_abs_val is not None and np_val < 0 and ocf_abs_val < 0:
    total = min(total, Config.NEGATIVE_PROFIT_PENALTY)
    print(f"  连续亏损惩罚 = {total:.2f}")

total = round(total, 2)
if total >= 75: grade = "A"
elif total >= 55: grade = "B"
elif total >= 40: grade = "C"
elif total >= 25: grade = "D"
else: grade = "E"

print(f"\n  ★ 最终得分: 【{total}】")
print(f"  ★ 评级: 【{grade}】")
print(f"  ★ 置信度: 【{conf_map[level]}】({non_null}/8 = {completeness*100:.1f}%)")
print("=" * 60)

# 与Excel对比
print(f"\n📋 与Excel输出对比:")
print(f"  {'维度':<10} {'计算值':>8} {'Excel值':>8} {'一致?':>6}")
print(f"  {'-'*36}")
for name, calc, excel in [
    ("盈利能力", profit_score, 77),
    ("成长性", growth_score, 92),
    ("现金流质量", ocf_score, 80),
    ("偿债风险", debt_score, 30),
]:
    match = "✅" if round(calc) == excel else "❌"
    print(f"  {name:<10} {round(calc):>8} {excel:>8} {match:>6}")

conn.close()
