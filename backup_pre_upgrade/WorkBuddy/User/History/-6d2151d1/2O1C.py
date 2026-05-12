"""
宏和科技（603256.SH）完整评分追踪
直接调用 calc_score，同时打印每步中间值
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from annual_scorer import (
    parse_financial_all, fetch_financial_data, calc_completeness,
    percentile_rank, calc_score, Config
)

TARGET = "603256.SH"

# 获取宏和科技数据
raw = fetch_financial_data(TARGET)
parsed = parse_financial_all(raw)

print("=" * 60)
print("【宏和科技 603256.SH】完整评分计算过程")
print("=" * 60)

# ========== Step 1: 核心指标 ==========
print("\n📋 Step 1：解析核心指标")
print("-" * 45)
core_keys = ["roe", "gross_margin", "net_margin", "revenue_yoy",
             "profit_yoy", "debt_ratio", "net_profit", "ocf_abs"]
key_names = {
    "roe": "ROE(%)",
    "gross_margin": "毛利率(%)",
    "net_margin": "净利率(%)",
    "revenue_yoy": "营收同比(%)",
    "profit_yoy": "归母净利润同比(%)",
    "debt_ratio": "资产负债率(%)",
    "net_profit": "归母净利润(元)",
    "ocf_abs": "经营现金流净额(元)"
}
for k in core_keys:
    v = parsed.get(k)
    status = "✅" if v is not None else "❌缺失"
    print(f"  {status} {key_names[k]}: {v}")

# ========== Step 2: 置信度 ==========
print(f"\n📊 Step 2：置信度（数据完整度）")
print("-" * 45)
completeness, level = calc_completeness(parsed)
non_null = sum(1 for m in core_keys if parsed.get(m) is not None)
print(f"  核心指标: {non_null}/8 = {completeness*100:.1f}%")
print(f"  等级: {level}")
conf_map = {"high": "高", "medium": "中", "low": "低", "ultra_low": "低"}
print(f"  → 置信度: 【{conf_map[level]}】")

# ========== Step 3: 手动复现 calc_score 逻辑 ==========
# 我们需要同行业数据。先读取行业映射
import json as j
industry_map_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "industry_map.json")
industry_l1 = None
if os.path.exists(industry_map_file):
    with open(industry_map_file, encoding="utf-8") as f:
        imap = j.load(f)
    # 查找宏和科技的行业
    for code_str, info in imap.items():
        if code_str == TARGET or code_str.replace(".SH","").replace(".SZ","") == "603256":
            industry_l1 = info.get("industry_l1") or info.get("industry")
            break

print(f"\n🏭 Step 3：行业判定")
print("-" * 45)
print(f"  行业映射文件: {industry_map_file}")
print(f"  宏和科技行业: {industry_l1}")

# 读取同行业股票列表
industry_stocks = {}
all_stocks_parsed = {}

# 尝试从行业映射获取同行业股票
peer_codes = []
if industry_l1 and os.path.exists(industry_map_file):
    for code_str, info in imap.items():
        if (info.get("industry_l1") or info.get("industry")) == industry_l1 and code_str != TARGET:
            peer_codes.append(code_str)

print(f"  同行业股票: {len(peer_codes)}只")

# 解析同行业数据
peer_parsed = {}
for code in peer_codes:
    try:
        r = fetch_financial_data(code)
        if r:
            peer_parsed[code] = parse_financial_all(r)
    except:
        pass

print(f"  成功解析: {len(peer_parsed)}只")

# 确定评分池
use_market_fallback = len(peer_parsed) < Config.MIN_INDUSTRY_SAMPLES
if use_market_fallback:
    print(f"  同行业{len(peer_parsed)}只 < {Config.MIN_INDUSTRY_SAMPLES} → 全市场池 × {Config.MARKET_FALLBACK_DISCOUNT}")
    discount = Config.MARKET_FALLBACK_DISCOUNT
else:
    print(f"  同行业{len(peer_parsed)}只 ≥ {Config.MIN_INDUSTRY_SAMPLES} → 同行业池 × 1.0")
    discount = 1.0

pool = list(peer_parsed.values())

def pool_values(key):
    return [s[key] for s in pool if s.get(key) is not None]

# ========== Step 4: 盈利能力 ==========
print(f"\n💪 Step 4：盈利能力（权重40%）")
print("-" * 45)
print(f"  公式: ROE×0.4 + 毛利率×0.3 + 净利率×0.3")

roe_v = parsed.get("roe")
gm_v = parsed.get("gross_margin")
nm_v = parsed.get("net_margin")

# ROE: 只有≥0才计分
roe_score = 0.0
if roe_v is not None and roe_v >= 0:
    vals = pool_values("roe")
    count_leq = sum(1 for v in vals if v <= roe_v)
    roe_score = (count_leq / len(vals)) * 100 if vals else 50.0
    print(f"\n  ROE = {roe_v}%")
    print(f"    对比池: {len(vals)}只, count_leq={count_leq}")
    print(f"    百分位 = {count_leq}/{len(vals)} × 100 = {roe_score:.2f}")
else:
    print(f"\n  ROE = {roe_v} → 0分" + ("(负值)" if roe_v is not None and roe_v < 0 else "(缺失)"))

# 毛利率
gm_score = 0.0
if gm_v is not None:
    vals = pool_values("gm_margin")
    # 注意代码里用的是 gross_margin
    vals = pool_values("gross_margin")
    count_leq = sum(1 for v in vals if v <= gm_v)
    gm_score = (count_leq / len(vals)) * 100 if vals else 50.0
    print(f"\n  毛利率 = {gm_v}%")
    print(f"    对比池: {len(vals)}只, count_leq={count_leq}")
    print(f"    百分位 = {count_leq}/{len(vals)} × 100 = {gm_score:.2f}")
else:
    print(f"\n  毛利率 = 缺失 → 0分")

# 净利率
nm_score = 0.0
if nm_v is not None:
    vals = pool_values("net_margin")
    count_leq = sum(1 for v in vals if v <= nm_v)
    nm_score = (count_leq / len(vals)) * 100 if vals else 50.0
    print(f"\n  净利率 = {nm_v}%")
    print(f"    对比池: {len(vals)}只, count_leq={count_leq}")
    print(f"    百分位 = {count_leq}/{len(vals)} × 100 = {nm_score:.2f}")
else:
    print(f"\n  净利率 = 缺失 → 0分")

profit_raw = roe_score * 0.4 + gm_score * 0.3 + nm_score * 0.3
profit_score = profit_raw * discount
print(f"\n  盈利能力 = {roe_score:.2f}×0.4 + {gm_score:.2f}×0.3 + {nm_score:.2f}×0.3 = {profit_raw:.2f}")
if discount < 1.0:
    print(f"  × {discount} = {profit_score:.2f}")
print(f"  → 【{profit_score:.0f}】")

# ========== Step 5: 成长性 ==========
print(f"\n📈 Step 5：成长性（权重30%）")
print("-" * 45)
print(f"  公式: 营收同比×0.4 + 净利同比×0.6")

rev_v = parsed.get("revenue_yoy")
prof_v = parsed.get("profit_yoy")

rev_score = 0.0
if rev_v is not None:
    vals = pool_values("revenue_yoy")
    count_leq = sum(1 for v in vals if v <= rev_v)
    rev_score = (count_leq / len(vals)) * 100 if vals else 50.0
    print(f"\n  营收同比 = {rev_v}%")
    print(f"    对比池: {len(vals)}只, count_leq={count_leq}")
    print(f"    百分位 = {rev_score:.2f}")
else:
    print(f"\n  营收同比 = 缺失 → 0分")

prof_score = 0.0
if prof_v is not None:
    vals = pool_values("profit_yoy")
    count_leq = sum(1 for v in vals if v <= prof_v)
    prof_score = (count_leq / len(vals)) * 100 if vals else 50.0
    print(f"\n  净利同比 = {prof_v}%")
    print(f"    对比池: {len(vals)}只, count_leq={count_leq}")
    print(f"    百分位 = {prof_score:.2f}")
else:
    print(f"\n  净利同比 = 缺失 → 0分")

growth_raw = rev_score * 0.4 + prof_score * 0.6
growth_score = growth_raw * discount
print(f"\n  成长性 = {rev_score:.2f}×0.4 + {prof_score:.2f}×0.6 = {growth_raw:.2f}")
if discount < 1.0:
    print(f"  × {discount} = {growth_score:.2f}")
print(f"  → 【{growth_score:.0f}】")

# ========== Step 6: 现金流质量 ==========
print(f"\n💰 Step 6：现金流质量（权重20%）")
print("-" * 45)
print(f"  公式: OCF/净利润 × 100% → 百分位排名")

np_val = parsed.get("net_profit")
ocf_abs_val = parsed.get("ocf_abs")

ocf_ratio = None
if np_val and ocf_abs_val and np_val != 0:
    ocf_ratio = round(ocf_abs_val / np_val * 100, 2)
    print(f"  归母净利润 = {np_val:,.0f} 元")
    print(f"  经营现金流 = {ocf_abs_val:,.0f} 元")
    print(f"  OCF/净利润 = {ocf_abs_val:,.0f}/{np_val:,.0f}×100% = {ocf_ratio}%")
else:
    print(f"  数据不足")

pool_ocf_vals = []
for s in pool:
    s_np = s.get("net_profit")
    s_ocf = s.get("ocf_abs")
    if s_np and s_ocf and s_np != 0:
        pool_ocf_vals.append(round(s_ocf / s_np * 100, 2))

ocf_pct_score = 0.0
if ocf_ratio is not None and pool_ocf_vals:
    count_leq = sum(1 for v in pool_ocf_vals if v <= ocf_ratio)
    ocf_pct_score = (count_leq / len(pool_ocf_vals)) * 100
    print(f"  对比池: {len(pool_ocf_vals)}只, count_leq={count_leq}")
    print(f"  百分位 = {ocf_pct_score:.2f}")
elif ocf_ratio is not None:
    ocf_pct_score = 50.0
    print(f"  无对比数据 → 50分")
else:
    print(f"  → 0分")

ocf_score = ocf_pct_score * discount
if discount < 1.0:
    print(f"  × {discount} = {ocf_score:.2f}")
print(f"  → 【{ocf_score:.0f}】")

# ========== Step 7: 偿债风险 ==========
print(f"\n🛡️ Step 7：偿债风险（权重10%）")
print("-" * 45)
print(f"  公式: 资产负债率 → 反向百分位（越低越好）")

debt_v = parsed.get("debt_ratio")
debt_score_val = 0.0
if debt_v is not None:
    vals = pool_values("debt_ratio")
    count_leq = sum(1 for v in vals if v <= debt_v)
    # reverse: (len - count_leq) / len * 100
    debt_score_val = ((len(vals) - count_leq) / len(vals)) * 100 if vals else 50.0
    print(f"  资产负债率 = {debt_v}%")
    print(f"  对比池: {len(vals)}只, count_leq={count_leq}")
    print(f"  反向百分位 = ({len(vals)}-{count_leq})/{len(vals)}×100 = {debt_score_val:.2f}")
else:
    print(f"  资产负债率 = 缺失 → 0分")

debt_score = debt_score_val * discount
if discount < 1.0:
    print(f"  × {discount} = {debt_score:.2f}")
print(f"  → 【{debt_score:.0f}】")

# ========== Step 8: 总分 ==========
print(f"\n" + "=" * 60)
print(f"📊 Step 8：汇总")
print("=" * 60)
print(f"  盈利能力:   {profit_score:.2f} × 40% = {profit_score*0.4:.2f}")
print(f"  成长性:     {growth_score:.2f} × 30% = {growth_score*0.3:.2f}")
print(f"  现金流质量: {ocf_score:.2f} × 20% = {ocf_score*0.2:.2f}")
print(f"  偿债风险:   {debt_score:.2f} × 10% = {debt_score*0.1:.2f}")

total = profit_score*0.4 + growth_score*0.3 + ocf_score*0.2 + debt_score*0.1
print(f"\n  原始总分 = {total:.2f}")

# 完整度折扣
if level == "low":
    total *= Config.LOW_COMPLETENESS_PENALTY
    print(f"  完整度折扣(low): ×{Config.LOW_COMPLETENESS_PENALTY} = {total:.2f}")
elif level == "ultra_low":
    total *= Config.LOW_COMPLETENESS_PENALTY * Config.ULTRA_LOW_COMPLETENESS_PENALTY
    print(f"  完整度折扣: ×{Config.LOW_COMPLETENESS_PENALTY * Config.ULTRA_LOW_COMPLETENESS_PENALTY} = {total:.2f}")

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

print(f"\n📋 与Excel对比:")
print(f"  盈利能力: 计算={profit_score:.0f}, Excel=77")
print(f"  成长性:   计算={growth_score:.0f}, Excel=92")
print(f"  现金流:   计算={ocf_score:.0f}, Excel=80")
print(f"  偿债风险: 计算={debt_score:.0f}, Excel=30")
