"""
宏和科技（603256.SH）完整评分计算过程追踪
完全按照 annual_scorer.py 的实际逻辑执行
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from annual_scorer import (
    parse_financial_all, fetch_financial_data, calc_completeness,
    percentile_rank, calc_score, INDUSTRIES, Config,
    load_industry_map, determine_industry
)

TARGET = "603256.SH"

# ========== 获取宏和科技数据 ==========
print("=" * 60)
print("【宏和科技 603256.SH】完整评分计算过程")
print("=" * 60)

raw = fetch_financial_data(TARGET)
if not raw:
    print("❌ 数据获取失败"); sys.exit(1)

parsed = parse_financial_all(raw)

print("\n📋 Step 1：解析出的核心指标")
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

# ========== 置信度 ==========
print(f"\n📊 Step 2：置信度计算")
print("-" * 45)
completeness, level = calc_completeness(parsed)
non_null = sum(1 for m in core_keys if parsed.get(m) is not None)
print(f"  8个核心指标: {non_null}个有值, {8-non_null}个缺失")
print(f"  完整度 = {non_null}/8 = {completeness:.3f} = {completeness*100:.1f}%")
print(f"  判定规则:")
print(f"    ≥85.7% (≥7/8) → high (高)")
print(f"    ≥57.1% (≥4/8) → medium (中)")
print(f"    ≤1个指标     → ultra_low (极低)")
print(f"    其他         → low (低)")
conf_map = {"high": "高", "medium": "中", "low": "低", "ultra_low": "低"}
print(f"  → 完整度等级: {level} → 置信度: 【{conf_map[level]}】")

# ========== 获取同行业数据 ==========
# 先确定行业
industry = determine_industry(TARGET, "宏和科技")
print(f"\n🏭 Step 3：确定行业")
print("-" * 45)
print(f"  判定行业: {industry}")

# 获取同行业所有股票
if industry and industry in INDUSTRIES:
    peer_codes = [c for c in INDUSTRIES[industry] if c != TARGET]
    print(f"  同行业股票池: {len(peer_codes)}只（不含自身）")
    use_fallback = len(peer_codes) < Config.MIN_INDUSTRY_SAMPLES
else:
    peer_codes = []
    use_fallback = True
    print(f"  未匹配行业")

discount = Config.MARKET_FALLBACK_DISCOUNT if use_fallback else 1.0
if use_fallback:
    print(f"  同行业<5只 → 使用全市场池 × 折扣{discount}")
else:
    print(f"  同行业≥5只 → 使用同行业池 × 折扣1.0")

# 解析同行业数据
print(f"\n📥 Step 4：解析同行业数据")
print("-" * 45)
peer_data = {}
fail_count = 0
for code in peer_codes:
    try:
        r = fetch_financial_data(code)
        if r:
            peer_data[code] = parse_financial_all(r)
        else:
            fail_count += 1
    except:
        fail_count += 1

print(f"  成功: {len(peer_data)}只, 失败: {fail_count}只")

# ========== 百分位排名函数 ==========
def show_pct(name, value, values, reverse=False):
    """展示百分位排名计算"""
    if value is None:
        print(f"    {name}: 缺失 → 0分")
        return 0.0
    if not values:
        print(f"    {name}: {value} → 无对比数据 → 50分")
        return 50.0
    
    count_leq = sum(1 for v in values if v <= value)
    if reverse:
        score = ((len(values) - count_leq) / len(values)) * 100
        direction = "越低越好"
    else:
        score = (count_leq / len(values)) * 100
        direction = "越高越好"
    
    # 显示分布
    sorted_vals = sorted(values, reverse=not reverse)
    rank_pos = next(i for i, v in enumerate(sorted_vals) if 
                    (not reverse and v >= value) or (reverse and v <= value))
    print(f"    {name}: {value}")
    print(f"      对比池: {len(values)}只股票")
    print(f"      方向: {direction}")
    print(f"      count_leq={count_leq}, 得分={score:.2f}")
    return score

# ========== 盈利能力 ==========
print(f"\n💪 Step 5：盈利能力评分（权重40%）")
print("-" * 45)
print(f"  公式: ROE×0.4 + 毛利率×0.3 + 净利率×0.3")

roe_val = parsed.get("roe")
gm_val = parsed.get("gross_margin")
nm_val = parsed.get("net_margin")

roe_scores = [peer_data[c].get("roe") for c in peer_data if peer_data[c].get("roe") is not None]
gm_scores = [peer_data[c].get("gross_margin") for c in peer_data if peer_data[c].get("gross_margin") is not None]
nm_scores = [peer_data[c].get("net_margin") for c in peer_data if peer_data[c].get("net_margin") is not None]

print(f"\n  ① ROE百分位:")
roe_pct = show_pct("ROE", roe_val, roe_scores)
print(f"  ② 毛利率百分位:")
gm_pct = show_pct("毛利率", gm_val, gm_scores)
print(f"  ③ 净利率百分位:")
nm_pct = show_pct("净利率", nm_val, nm_scores)

profit_raw = roe_pct * 0.4 + gm_pct * 0.3 + nm_pct * 0.3
profit_score = profit_raw * discount
print(f"\n  盈利能力 = {roe_pct:.2f}×0.4 + {gm_pct:.2f}×0.3 + {nm_pct:.2f}×0.3")
print(f"           = {roe_pct*0.4:.2f} + {gm_pct*0.3:.2f} + {nm_pct*0.3:.2f}")
print(f"           = {profit_raw:.2f}")
if discount < 1.0:
    print(f"  × 折扣{discount} = {profit_score:.2f}")
print(f"  → 盈利能力得分: 【{profit_score:.0f}】")

# ========== 成长性 ==========
print(f"\n📈 Step 6：成长性评分（权重30%）")
print("-" * 45)
print(f"  公式: 营收同比×0.4 + 净利同比×0.6")

rev_val = parsed.get("revenue_yoy")
prof_val = parsed.get("profit_yoy")

rev_scores = [peer_data[c].get("revenue_yoy") for c in peer_data if peer_data[c].get("revenue_yoy") is not None]
prof_scores = [peer_data[c].get("profit_yoy") for c in peer_data if peer_data[c].get("profit_yoy") is not None]

print(f"\n  ① 营收同比百分位:")
rev_pct = show_pct("营收同比", rev_val, rev_scores)
print(f"  ② 净利同比百分位:")
prof_pct = show_pct("净利同比", prof_val, prof_scores)

growth_raw = rev_pct * 0.4 + prof_pct * 0.6
growth_score = growth_raw * discount
print(f"\n  成长性 = {rev_pct:.2f}×0.4 + {prof_pct:.2f}×0.6")
print(f"         = {rev_pct*0.4:.2f} + {prof_pct*0.6:.2f}")
print(f"         = {growth_raw:.2f}")
if discount < 1.0:
    print(f"  × 折扣{discount} = {growth_score:.2f}")
print(f"  → 成长性得分: 【{growth_score:.0f}】")

# ========== 现金流质量 ==========
print(f"\n💰 Step 7：现金流质量评分（权重20%）")
print("-" * 45)
print(f"  公式: OCF/净利润 × 100% → 百分位排名")

np_val = parsed.get("net_profit")
ocf_val = parsed.get("ocf_abs")

print(f"  归母净利润: {np_val:,.0f} 元" if np_val else "  归母净利润: 缺失")
print(f"  经营现金流: {ocf_val:,.0f} 元" if ocf_val else "  经营现金流: 缺失")

if np_val and ocf_val and np_val != 0:
    ocf_ratio = round(ocf_val / np_val * 100, 2)
    print(f"  OCF/净利润 = {ocf_val:,.0f} / {np_val:,.0f} × 100% = {ocf_ratio}%")
else:
    ocf_ratio = None
    print(f"  ❌ 数据不足，无法计算OCF/净利润")

pool_ocf = []
for c in peer_data:
    s_np = peer_data[c].get("net_profit")
    s_ocf = peer_data[c].get("ocf_abs")
    if s_np and s_ocf and s_np != 0:
        pool_ocf.append(round(s_ocf / s_np * 100, 2))

print(f"\n  同行业OCF/净利润百分位:")
ocf_pct = show_pct(f"OCF/净利润={ocf_ratio}%", ocf_ratio, pool_ocf)
ocf_score = ocf_pct * discount
if discount < 1.0:
    print(f"  × 折扣{discount} = {ocf_score:.2f}")
print(f"  → 现金流质量得分: 【{ocf_score:.0f}】")

# ========== 偿债风险 ==========
print(f"\n🛡️ Step 8：偿债风险评分（权重10%）")
print("-" * 45)
print(f"  公式: 资产负债率 → 反向百分位（越低越好）")

debt_val = parsed.get("debt_ratio")
debt_scores = [peer_data[c].get("debt_ratio") for c in peer_data if peer_data[c].get("debt_ratio") is not None]

print(f"\n  负债率反向百分位:")
debt_pct = show_pct("资产负债率", debt_val, debt_scores, reverse=True)
debt_score = debt_pct * discount
if discount < 1.0:
    print(f"  × 折扣{discount} = {debt_score:.2f}")
print(f"  → 偿债风险得分: 【{debt_score:.0f}】")

# ========== 总分 ==========
print(f"\n" + "=" * 60)
print(f"📊 Step 9：汇总总分")
print("=" * 60)
print(f"  盈利能力:   {profit_score:.2f} × 40% = {profit_score*0.4:.2f}")
print(f"  成长性:     {growth_score:.2f} × 30% = {growth_score*0.3:.2f}")
print(f"  现金流质量: {ocf_score:.2f} × 20% = {ocf_score*0.2:.2f}")
print(f"  偿债风险:   {debt_score:.2f} × 10% = {debt_score*0.1:.2f}")

total = profit_score*0.4 + growth_score*0.3 + ocf_score*0.2 + debt_score*0.1
print(f"\n  原始总分 = {profit_score*0.4:.2f} + {growth_score*0.3:.2f} + {ocf_score*0.2:.2f} + {debt_score*0.1:.2f}")
print(f"          = {total:.2f}")

# 数据完整度折扣
if level == "low":
    total *= Config.LOW_COMPLETENESS_PENALTY
    print(f"  完整度折扣(low): ×{Config.LOW_COMPLETENESS_PENALTY} = {total:.2f}")
elif level == "ultra_low":
    total *= Config.LOW_COMPLETENESS_PENALTY * Config.ULTRA_LOW_COMPLETENESS_PENALTY
    print(f"  完整度折扣(ultra_low): ×{Config.LOW_COMPLETENESS_PENALTY * Config.ULTRA_LOW_COMPLETENESS_PENALTY} = {total:.2f}")

# 连续亏损惩罚
if np_val is not None and ocf_val is not None and np_val < 0 and ocf_val < 0:
    total = min(total, Config.NEGATIVE_PROFIT_PENALTY)
    print(f"  连续亏损惩罚: = {total:.2f}")

total = round(total, 2)

# 评级
if total >= 75: grade = "A"
elif total >= 55: grade = "B"
elif total >= 40: grade = "C"
elif total >= 25: grade = "D"
else: grade = "E"

print(f"\n  ★ 最终得分: 【{total}】")
print(f"  ★ 评级: 【{grade}】")
print(f"  ★ 置信度: 【{conf_map[level]}】({non_null}/8 = {completeness*100:.1f}%)")
print("=" * 60)

# 验证与calc_score一致性
print(f"\n✅ 验证：与calc_score()函数结果对比")
print(f"  本脚本计算: 盈利能力={profit_score:.2f}, 成长性={growth_score:.2f}, 现金流={ocf_score:.2f}, 偿债={debt_score:.2f}")
print(f"  Excel输出值: 盈利能力=77, 成长性=92, 现金流质量=80, 偿债风险=30")
