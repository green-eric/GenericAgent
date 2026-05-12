"""
完整展示置信度 + 四维评分计算过程
以宏和科技（603256.SH）为例
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from annual_scorer import (
    parse_financial_all, score_stocks, fetch_financial_data,
    INDUSTRIES, calc_percentile_rank, _parse_num_from_line
)

TARGET = "603256.SH"

# ========== 第一步：获取原始数据 ==========
print("=" * 70)
print(f"【宏和科技 603256.SH】完整评分计算过程")
print("=" * 70)

raw = fetch_financial_data(TARGET)
if not raw:
    print("❌ 数据获取失败")
    sys.exit(1)

# ========== 第二步：解析财务指标 ==========
print("\n📋 第一步：解析核心指标")
print("-" * 50)

parsed = parse_financial_all(raw)
core_keys = ["roe", "gross_margin", "net_margin", "rev_yoy", "np_yoy",
             "debt_ratio", "net_profit", "ocf"]
key_names = {
    "roe": "ROE(%)",
    "gross_margin": "毛利率(%)",
    "net_margin": "净利率(%)",
    "rev_yoy": "营收同比(%)",
    "np_yoy": "净利同比(%)",
    "debt_ratio": "负债率(%)",
    "net_profit": "归母净利润(元)",
    "ocf": "经营现金流(元)"
}

core_values = {}
for k in core_keys:
    v = parsed.get(k)
    core_values[k] = v
    status = "✅" if v is not None else "❌"
    print(f"  {status} {key_names[k]}: {v}")

# ========== 第三步：置信度 ==========
print("\n📊 第二步：置信度计算")
print("-" * 50)

valid_count = sum(1 for k in core_keys if core_values[k] is not None)
total_count = len(core_keys)
ratio = valid_count / total_count * 100

print(f"  核心指标完整度: {valid_count}/{total_count} = {ratio:.1f}%")
print(f"  判定规则:")
print(f"    ≥85.7% (≥7/8) → 高置信度")
print(f"    ≥57.1% (≥4/8) → 中置信度")
print(f"    ≤1个指标    → 极低置信度")
print(f"    其他        → 低置信度")

if ratio >= 85.7:
    confidence = "高"
elif ratio >= 57.1:
    confidence = "中"
elif valid_count <= 1:
    confidence = "极低"
else:
    confidence = "低"
print(f"  → 置信度: 【{confidence}】")

# ========== 第四步：确定行业池 ==========
print("\n🏭 第三步：确定评分池")
print("-" * 50)

industry = None
for ind, codes in INDUSTRIES.items():
    if TARGET in codes:
        industry = ind
        break

if industry:
    pool_codes = [c for c in INDUSTRIES[industry] if c != TARGET]
    print(f"  所属行业: {industry}")
    print(f"  同行业股票数: {len(INDUSTRIES[industry])}只（含自身）")
    print(f"  评分池大小: {len(pool_codes)}只（排除自身）")
    use_pool = "同行业"
    discount = 1.0
else:
    pool_codes = []
    print(f"  未匹配行业，使用全市场池")
    use_pool = "全市场"
    discount = 0.9

# ========== 第五步：解析全市场/同行业数据 ==========
print(f"\n📥 第四步：获取{use_pool}对比数据")
print("-" * 50)

all_parsed = {TARGET: parsed}
failed = []
for code in pool_codes:
    try:
        r = fetch_financial_data(code)
        if r:
            all_parsed[code] = parse_financial_all(r)
        else:
            failed.append(code)
    except Exception as e:
        failed.append(code)

if industry and len(pool_codes) < 4:
    print(f"  同行业仅{len(pool_codes)}只(<5)，扩大到全市场")
    use_pool = "全市场"
    discount = 0.9

print(f"  成功获取: {len(all_parsed)}只（含自身）")
if failed:
    print(f"  获取失败: {len(failed)}只")

# ========== 第六步：百分位排名辅助函数 ==========
def pct_rank(value, values):
    """百分位排名：值越大排名越高"""
    if value is None:
        return None
    all_v = [v for v in values if v is not None]
    if not all_v:
        return 50.0
    below = sum(1 for v in all_v if v < value)
    equal = sum(1 for v in all_v if v == value)
    return (below + 0.5 * equal) / len(all_v) * 100

def pct_rank_inv(value, values):
    """反向百分位排名：值越小排名越高（用于负债率）"""
    if value is None:
        return None
    all_v = [v for v in values if v is not None]
    if not all_v:
        return 50.0
    above = sum(1 for v in all_v if v > value)
    equal = sum(1 for v in all_v if v == value)
    return (above + 0.5 * equal) / len(all_v) * 100

# ========== 第七步：盈利能力 ==========
print(f"\n💪 第五步：盈利能力评分（权重40%）")
print("-" * 50)
print(f"  子指标权重: ROE×0.4 + 毛利率×0.3 + 净利率×0.3")

roe_v = core_values["roe"]
gm_v = core_values["gross_margin"]
nm_v = core_values["net_margin"]

all_roe = [all_parsed[c].get("roe") for c in all_parsed if c != TARGET]
all_gm = [all_parsed[c].get("gross_margin") for c in all_parsed if c != TARGET]
all_nm = [all_parsed[c].get("net_margin") for c in all_parsed if c != TARGET]

roe_pct = pct_rank(roe_v, all_roe)
gm_pct = pct_rank(gm_v, all_gm)
nm_pct = pct_rank(nm_v, all_nm)

print(f"\n  ROE: {roe_v}%")
print(f"    在同业中百分位: {roe_pct:.1f}分")
print(f"  毛利率: {gm_v}%")
print(f"    在同业中百分位: {gm_pct:.1f}分")
print(f"  净利率: {nm_v}%")
print(f"    在同业中百分位: {nm_pct:.1f}分")

if roe_pct is not None and gm_pct is not None and nm_pct is not None:
    profit_score = roe_pct * 0.4 + gm_pct * 0.3 + nm_pct * 0.3
elif roe_pct is not None and nm_pct is not None:
    profit_score = roe_pct * 0.5 + nm_pct * 0.5
elif roe_pct is not None:
    profit_score = roe_pct
else:
    profit_score = 50.0

profit_score = profit_score * discount
print(f"\n  盈利能力 = {roe_pct:.1f}×0.4 + {gm_pct:.1f}×0.3 + {nm_pct:.1f}×0.3")
print(f"           = {roe_pct*0.4:.1f} + {gm_pct*0.3:.1f} + {nm_pct*0.3:.1f}")
print(f"           = {roe_pct*0.4 + gm_pct*0.3 + nm_pct*0.3:.1f}")
if discount < 1.0:
    print(f"  × 全市场折扣0.9 = {profit_score:.1f}")
print(f"  → 盈利能力得分: 【{profit_score:.0f}】")

# ========== 第八步：成长性 ==========
print(f"\n📈 第六步：成长性评分（权重30%）")
print("-" * 50)
print(f"  子指标权重: 营收同比×0.4 + 净利同比×0.6")

rev_v = core_values["rev_yoy"]
np_v = core_values["np_yoy"]

all_rev = [all_parsed[c].get("rev_yoy") for c in all_parsed if c != TARGET]
all_np = [all_parsed[c].get("np_yoy") for c in all_parsed if c != TARGET]

rev_pct = pct_rank(rev_v, all_rev)
np_pct = pct_rank(np_v, all_np)

print(f"\n  营收同比: {rev_v}%")
print(f"    在同业中百分位: {rev_pct:.1f}分")
print(f"  净利同比: {np_v}%")
print(f"    在同业中百分位: {np_pct:.1f}分")

if rev_pct is not None and np_pct is not None:
    growth_score = rev_pct * 0.4 + np_pct * 0.6
elif np_pct is not None:
    growth_score = np_pct
elif rev_pct is not None:
    growth_score = rev_pct
else:
    growth_score = 50.0

growth_score = growth_score * discount
print(f"\n  成长性 = {rev_pct:.1f}×0.4 + {np_pct:.1f}×0.6")
print(f"         = {rev_pct*0.4:.1f} + {np_pct*0.6:.1f}")
print(f"         = {rev_pct*0.4 + np_pct*0.6:.1f}")
if discount < 1.0:
    print(f"  × 全市场折扣0.9 = {growth_score:.1f}")
print(f"  → 成长性得分: 【{growth_score:.0f}】")

# ========== 第九步：现金流质量 ==========
print(f"\n💰 第七步：现金流质量评分（权重20%）")
print("-" * 50)
print(f"  指标: OCF/净利润 × 100%")

ocf_v = core_values["ocf"]
np_val = core_values["net_profit"]

if ocf_v is not None and np_val is not None and np_val != 0:
    ocf_ratio = ocf_v / np_val * 100
    print(f"\n  经营现金流: {ocf_v:,.0f} 元")
    print(f"  归母净利润: {np_val:,.0f} 元")
    print(f"  OCF/净利润 = {ocf_v:,.0f} / {np_val:,.0f} × 100% = {ocf_ratio:.1f}%")
else:
    ocf_ratio = None
    print(f"\n  ❌ 数据不足，OCF={ocf_v}, 净利润={np_val}")

all_ocf_ratio = []
for c in all_parsed:
    if c == TARGET:
        continue
    o = all_parsed[c].get("ocf")
    n = all_parsed[c].get("net_profit")
    if o is not None and n is not None and n != 0:
        all_ocf_ratio.append(o / n * 100)

if ocf_ratio is not None:
    ocf_pct = pct_rank(ocf_ratio, all_ocf_ratio)
    print(f"  OCF/净利润={ocf_ratio:.1f}% 在同业中百分位: {ocf_pct:.1f}分")
else:
    ocf_pct = 50.0
    print(f"  默认50分")

ocf_score = ocf_pct * discount
if discount < 1.0:
    print(f"  × 全市场折扣0.9 = {ocf_score:.1f}")
print(f"  → 现金流质量得分: 【{ocf_score:.0f}】")

# ========== 第十步：偿债风险 ==========
print(f"\n🛡️ 第八步：偿债风险评分（权重10%）")
print("-" * 50)
print(f"  指标: 负债率(%) → 越低越好（反向排名）")

debt_v = core_values["debt_ratio"]
all_debt = [all_parsed[c].get("debt_ratio") for c in all_parsed if c != TARGET]

debt_pct = pct_rank_inv(debt_v, all_debt)

print(f"\n  负债率: {debt_v}%")
print(f"    反向百分位（越低越好）: {debt_pct:.1f}分")

debt_score = debt_pct * discount
if discount < 1.0:
    print(f"  × 全市场折扣0.9 = {debt_score:.1f}")
print(f"  → 偿债风险得分: 【{debt_score:.0f}】")

# ========== 第十一步：总分 ==========
print(f"\n" + "=" * 70)
print(f"📊 第九步：汇总总分")
print("=" * 70)
print(f"  盈利能力:   {profit_score:.1f} × 40% = {profit_score*0.4:.1f}")
print(f"  成长性:     {growth_score:.1f} × 30% = {growth_score*0.3:.1f}")
print(f"  现金流质量: {ocf_score:.1f} × 20% = {ocf_score*0.2:.1f}")
print(f"  偿债风险:   {debt_score:.1f} × 10% = {debt_score*0.1:.1f}")

total = profit_score * 0.4 + growth_score * 0.3 + ocf_score * 0.2 + debt_score * 0.1
print(f"\n  总分 = {profit_score*0.4:.1f} + {growth_score*0.3:.1f} + {ocf_score*0.2:.1f} + {debt_score*0.1:.1f}")
print(f"       = {total:.1f}")
print(f"\n  ★ 最终得分: 【{total:.0f}】 置信度: 【{confidence}】")
print("=" * 70)
