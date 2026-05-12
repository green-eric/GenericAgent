"""
宏和科技（603256.SH）完整评分追踪
通过 monkey-patch calc_score 打印所有中间计算值
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from annual_scorer import (
    parse_financial_all, fetch_financial_data, calc_completeness,
    percentile_rank, Config
)
import annual_scorer as scorer

TARGET = "603256.SH"

# 获取宏和科技数据
raw = fetch_financial_data(TARGET)
parsed = parse_financial_all(raw)

# 全局打印开关
_print = True

# 保存原始 calc_score
_orig_calc_score = scorer.calc_score

def traced_calc_score(stock, industry_stocks, all_stocks):
    """带追踪的 calc_score"""
    ts_code = stock["ts_code"]
    if ts_code != TARGET:
        return _orig_calc_score(stock, industry_stocks, all_stocks)
    
    industry = stock.get("industry_l1", "未知")
    metrics = stock
    
    # 确定参考池
    pool = industry_stocks.get(industry, [])
    use_market_fallback = len(pool) < Config.MIN_INDUSTRY_SAMPLES
    if use_market_fallback:
        pool = all_stocks
    discount = Config.MARKET_FALLBACK_DISCOUNT if use_market_fallback else 1.0
    
    def pool_values(key):
        return [s[key] for s in pool if s.get("ts_code") != ts_code and s.get(key) is not None]
    
    print("=" * 60)
    print(f"【宏和科技 603256.SH】完整评分计算过程")
    print("=" * 60)
    
    # 核心指标
    core_keys = ["roe", "gross_margin", "net_margin", "revenue_yoy",
                 "profit_yoy", "debt_ratio", "net_profit", "ocf_abs"]
    key_names = {
        "roe": "ROE(%)", "gross_margin": "毛利率(%)", "net_margin": "净利率(%)",
        "revenue_yoy": "营收同比(%)", "profit_yoy": "归母净利润同比(%)",
        "debt_ratio": "资产负债率(%)", "net_profit": "归母净利润(元)", "ocf_abs": "经营现金流(元)"
    }
    
    print("\n📋 Step 1：核心指标")
    print("-" * 45)
    for k in core_keys:
        v = metrics.get(k)
        status = "✅" if v is not None else "❌"
        print(f"  {status} {key_names[k]}: {v}")
    
    # 置信度
    completeness, level = calc_completeness(metrics)
    non_null = sum(1 for m in core_keys if metrics.get(m) is not None)
    print(f"\n📊 Step 2：置信度")
    print("-" * 45)
    print(f"  完整度: {non_null}/8 = {completeness*100:.1f}%")
    print(f"  等级: {level} → { {'high':'高','medium':'中','low':'低','ultra_low':'低'}[level] }")
    
    # 评分池
    print(f"\n🏭 Step 3：评分池")
    print("-" * 45)
    print(f"  行业: {industry}")
    print(f"  同行业池: {len(industry_stocks.get(industry, []))}只")
    print(f"  是否全市场回退: {use_market_fallback}")
    print(f"  折扣系数: {discount}")
    print(f"  实际对比池大小: {len(pool)}只")
    
    # 1. 盈利能力
    print(f"\n💪 Step 4：盈利能力（权重40%）")
    print("-" * 45)
    print(f"  公式: ROE×0.4 + 毛利率×0.3 + 净利率×0.3")
    
    roe_score = 0.0
    if metrics.get("roe") is not None and metrics["roe"] >= 0:
        roe_score = percentile_rank(metrics["roe"], pool_values("roe"))
    print(f"  ROE={metrics.get('roe')}% → 百分位={roe_score:.2f}")
    
    gross_score = percentile_rank(metrics["gross_margin"], pool_values("gross_margin")) if metrics.get("gross_margin") is not None else 0.0
    print(f"  毛利率={metrics.get('gross_margin')}% → 百分位={gross_score:.2f}")
    
    net_score = percentile_rank(metrics["net_margin"], pool_values("net_margin")) if metrics.get("net_margin") is not None else 0.0
    print(f"  净利率={metrics.get('net_margin')}% → 百分位={net_score:.2f}")
    
    profit_score = (roe_score * 0.4 + gross_score * 0.3 + net_score * 0.3) * discount
    print(f"  计算: {roe_score:.2f}×0.4 + {gross_score:.2f}×0.3 + {net_score:.2f}×0.3 = {roe_score*0.4+gross_score*0.3+net_score*0.3:.2f}")
    if discount < 1.0:
        print(f"  ×{discount} = {profit_score:.2f}")
    print(f"  → 盈利能力 = 【{profit_score:.2f}】")
    
    # 2. 成长性
    print(f"\n📈 Step 5：成长性（权重30%）")
    print("-" * 45)
    print(f"  公式: 营收同比×0.4 + 净利同比×0.6")
    
    rev_score = percentile_rank(metrics["revenue_yoy"], pool_values("revenue_yoy")) if metrics.get("revenue_yoy") is not None else 0.0
    print(f"  营收同比={metrics.get('revenue_yoy')}% → 百分位={rev_score:.2f}")
    
    prof_score = percentile_rank(metrics["profit_yoy"], pool_values("profit_yoy")) if metrics.get("profit_yoy") is not None else 0.0
    print(f"  净利同比={metrics.get('profit_yoy')}% → 百分位={prof_score:.2f}")
    
    growth_score = (rev_score * 0.4 + prof_score * 0.6) * discount
    print(f"  计算: {rev_score:.2f}×0.4 + {prof_score:.2f}×0.6 = {rev_score*0.4+prof_score*0.6:.2f}")
    if discount < 1.0:
        print(f"  ×{discount} = {growth_score:.2f}")
    print(f"  → 成长性 = 【{growth_score:.2f}】")
    
    # 3. 现金流质量
    print(f"\n💰 Step 6：现金流质量（权重20%）")
    print("-" * 45)
    
    np_val = metrics.get("net_profit")
    ocf_abs_val = metrics.get("ocf_abs")
    ocf_val = None
    ocf_score = 0.0
    
    if np_val and ocf_abs_val and np_val != 0:
        ocf_val = round(ocf_abs_val / np_val * 100, 2)
        print(f"  OCF/净利润 = {ocf_abs_val:,.0f}/{np_val:,.0f}×100% = {ocf_val}%")
        
        pool_ocf_vals = []
        for s in pool:
            if s.get("ts_code") == ts_code:
                continue
            s_np = s.get("net_profit")
            s_ocf = s.get("ocf_abs")
            if s_np and s_ocf and s_np != 0:
                pool_ocf_vals.append(round(s_ocf / s_np * 100, 2))
        
        if ocf_val is not None:
            ocf_score = percentile_rank(ocf_val, pool_ocf_vals)
            print(f"  同行业OCF/净利润对比池: {len(pool_ocf_vals)}只")
            print(f"  百分位 = {ocf_score:.2f}")
    
    ocf_score *= discount
    if discount < 1.0:
        print(f"  ×{discount} = {ocf_score:.2f}")
    print(f"  → 现金流质量 = 【{ocf_score:.2f}】")
    
    # 4. 偿债风险
    print(f"\n🛡️ Step 7：偿债风险（权重10%）")
    print("-" * 45)
    print(f"  公式: 资产负债率 → 反向百分位（越低越好）")
    
    debt_score = 0.0
    if metrics.get("debt_ratio") is not None:
        debt_score = percentile_rank(metrics["debt_ratio"], pool_values("debt_ratio"), reverse=True)
    print(f"  资产负债率={metrics.get('debt_ratio')}% → 反向百分位={debt_score:.2f}")
    
    debt_score *= discount
    if discount < 1.0:
        print(f"  ×{discount} = {debt_score:.2f}")
    print(f"  → 偿债风险 = 【{debt_score:.2f}】")
    
    # 总分
    total_score = profit_score * 0.4 + growth_score * 0.3 + ocf_score * 0.2 + debt_score * 0.1
    
    print(f"\n" + "=" * 60)
    print(f"📊 Step 8：汇总总分")
    print("=" * 60)
    print(f"  盈利能力:   {profit_score:.2f} × 40% = {profit_score*0.4:.2f}")
    print(f"  成长性:     {growth_score:.2f} × 30% = {growth_score*0.3:.2f}")
    print(f"  现金流质量: {ocf_score:.2f} × 20% = {ocf_score*0.2:.2f}")
    print(f"  偿债风险:   {debt_score:.2f} × 10% = {debt_score*0.1:.2f}")
    print(f"  原始总分 = {total_score:.2f}")
    
    # 完整度折扣
    if level == "low":
        total_score *= Config.LOW_COMPLETENESS_PENALTY
        print(f"  完整度折扣(low): ×{Config.LOW_COMPLETENESS_PENALTY} = {total_score:.2f}")
    elif level == "ultra_low":
        total_score *= Config.LOW_COMPLETENESS_PENALTY * Config.ULTRA_LOW_COMPLETENESS_PENALTY
        print(f"  完整度折扣(ultra_low): ×{Config.LOW_COMPLETENESS_PENALTY * Config.ULTRA_LOW_COMPLETENESS_PENALTY} = {total_score:.2f}")
    
    # 连续亏损惩罚
    if np_val is not None and ocf_abs_val is not None and np_val < 0 and ocf_abs_val < 0:
        total_score = min(total_score, Config.NEGATIVE_PROFIT_PENALTY)
        print(f"  连续亏损惩罚 = {total_score:.2f}")
    
    total_score = round(total_score, 2)
    
    if total_score >= 75: grade = "A"
    elif total_score >= 55: grade = "B"
    elif total_score >= 40: grade = "C"
    elif total_score >= 25: grade = "D"
    else: grade = "E"
    
    conf_map = {"high": "高", "medium": "中", "low": "低", "ultra_low": "低"}
    
    print(f"\n  ★ 最终得分: 【{total_score}】")
    print(f"  ★ 评级: 【{grade}】")
    print(f"  ★ 置信度: 【{conf_map[level]}】({non_null}/8 = {completeness*100:.1f}%)")
    print("=" * 60)
    
    # 调用原始函数返回正确结果
    return _orig_calc_score(stock, industry_stocks, all_stocks)

# 替换
scorer.calc_score = traced_calc_score

# 运行主程序
scorer.main()
