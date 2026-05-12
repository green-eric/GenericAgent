#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""完整计算过程演示 - 宏和科技 603256.SH"""
import sqlite3, os, sys
sys.path.insert(0, r'D:\Project\AnnualScorer')
from annual_scorer import *

Config.BASE_DIR = r'D:\Project\AnnualScorer'
Config.DB_FILE = os.path.join(Config.BASE_DIR, 'stock_cache.db')
conn = sqlite3.connect(Config.DB_FILE)

# ============================================================
# 第一步：加载全部股票数据
# ============================================================
print("=" * 70)
print("第一步：加载全部股票年报数据")
print("=" * 70)

all_stocks_data = conn.execute(
    'SELECT s.ts_code, s.name, s.industry_l1, f.roe, f.gross_margin, f.net_margin, '
    'f.revenue_yoy, f.profit_yoy, f.debt_ratio, f.net_profit, f.ocf_abs '
    'FROM stocks s JOIN financial_reports f ON s.ts_code=f.ts_code '
    'WHERE f.report_type="annual" AND f.fetch_success=1 '
    'AND f.report_date = (SELECT MAX(report_date) FROM financial_reports WHERE ts_code=s.ts_code AND report_type="annual" AND fetch_success=1)'
).fetchall()

all_stocks = []
for r in all_stocks_data:
    all_stocks.append({
        'ts_code': r[0], 'name': r[1], 'industry_l1': r[2],
        'roe': r[3], 'gross_margin': r[4], 'net_margin': r[5],
        'revenue_yoy': r[6], 'profit_yoy': r[7], 'debt_ratio': r[8],
        'net_profit': r[9], 'ocf_abs': r[10], 'fetch_success': True,
    })

print(f"共加载 {len(all_stocks)} 只股票")

# 行业分组
industry_groups = {}
for s in all_stocks:
    ind = s.get('industry_l1', '未知')
    industry_groups.setdefault(ind, []).append(s)

for ind, grp in sorted(industry_groups.items()):
    print(f"  {ind}: {len(grp)}只")

# ============================================================
# 第二步：找到目标股票
# ============================================================
target = None
for s in all_stocks:
    if s['ts_code'] == '603256.SH':
        target = s
        break

print("\n" + "=" * 70)
print(f"第二步：目标股票 - {target['name']} ({target['ts_code']})")
print("=" * 70)
print(f"  行业: {target['industry_l1']}")
print(f"  ROE: {target['roe']}%")
print(f"  毛利率: {target['gross_margin']}%")
print(f"  净利率: {target['net_margin']}%")
print(f"  营收同比: {target['revenue_yoy']}%")
print(f"  净利同比: {target['profit_yoy']}%")
print(f"  负债率: {target['debt_ratio']}%")
print(f"  归母净利润: {target['net_profit']}")
print(f"  经营现金流: {target['ocf_abs']}")

# ============================================================
# 第三步：确定参考池
# ============================================================
print("\n" + "=" * 70)
print("第三步：确定评分参考池")
print("=" * 70)

industry = target['industry_l1']
pool = industry_groups.get(industry, [])
use_market_fallback = len(pool) < Config.MIN_INDUSTRY_SAMPLES
discount = Config.MARKET_FALLBACK_DISCOUNT if use_market_fallback else 1.0

print(f"  同行业({industry}): {len(pool)}只")
print(f"  全市场: {len(all_stocks)}只")
print(f"  同行业样本数 {len(pool)} < {Config.MIN_INDUSTRY_SAMPLES} -> 使用全市场对比: {use_market_fallback}")
if use_market_fallback:
    print(f"  市场折扣系数: {discount}")
    pool = all_stocks

# ============================================================
# 第四步：置信度计算
# ============================================================
print("\n" + "=" * 70)
print("第四步：置信度计算")
print("=" * 70)

core_metrics = ["roe", "gross_margin", "net_margin", "revenue_yoy",
                "profit_yoy", "debt_ratio", "net_profit", "ocf_abs"]
non_null = 0
for m in core_metrics:
    val = target.get(m)
    has = val is not None
    if has:
        non_null += 1
    print(f"  {m}: {val}  -> {'有值' if has else '缺失'}")

completeness = non_null / len(core_metrics)
if completeness >= 0.857:
    level = "high"
    confidence = "高"
elif completeness >= 0.571:
    level = "medium"
    confidence = "中"
elif non_null <= 1:
    level = "ultra_low"
    confidence = "低"
else:
    level = "low"
    confidence = "低"

print(f"\n  完整度: {non_null}/{len(core_metrics)} = {completeness:.1%}")
print(f"  完整度级别: {level}")
print(f"  置信度: {confidence}")

# ============================================================
# 第五步：盈利能力评分（权重40%）
# ============================================================
print("\n" + "=" * 70)
print("第五步：盈利能力评分（权重40%）")
print("=" * 70)

def pool_values(key):
    return [s[key] for s in pool if s.get('ts_code') != target['ts_code'] and s.get(key) is not None]

# ROE
pool_roe = pool_values("roe")
roe_score = 0.0
if target.get("roe") is not None and target["roe"] >= 0:
    roe_score = percentile_rank(target["roe"], pool_roe)
print(f"\n  [ROE] 目标值: {target['roe']}%")
print(f"    行业池ROE值: {sorted(pool_roe, reverse=True)}")
    # 显示排名
sorted_roe = sorted(pool_roe + [target["roe"]], reverse=True)
rank_roe = sorted_roe.index(target["roe"]) + 1
print(f"    排名: {rank_roe}/{len(pool_roe)+1}")
print(f"    ROE得分: {roe_score:.2f}")

# 毛利率
pool_gross = pool_values("gross_margin")
gross_score = 0.0
if target.get("gross_margin") is not None:
    gross_score = percentile_rank(target["gross_margin"], pool_gross)
    sorted_gross = sorted(pool_gross + [target["gross_margin"]], reverse=True)
    rank_gross = sorted_gross.index(target["gross_margin"]) + 1
    print(f"\n  [毛利率] 目标值: {target['gross_margin']}%")
    print(f"    行业池毛利率值: {sorted(pool_gross, reverse=True)}")
    print(f"    排名: {rank_gross}/{len(pool_gross)+1}")
    print(f"    毛利率得分: {gross_score:.2f}")

# 净利率
pool_net = pool_values("net_margin")
net_score = 0.0
if target.get("net_margin") is not None:
    net_score = percentile_rank(target["net_margin"], pool_net)
    sorted_net = sorted(pool_net + [target["net_margin"]], reverse=True)
    rank_net = sorted_net.index(target["net_margin"]) + 1
    print(f"\n  [净利率] 目标值: {target['net_margin']}%")
    print(f"    行业池净利率值: {sorted(pool_net, reverse=True)}")
    print(f"    排名: {rank_net}/{len(pool_net)+1}")
    print(f"    净利率得分: {net_score:.2f}")

profit_score = (roe_score * 0.4 + gross_score * 0.3 + net_score * 0.3) * discount
print(f"\n  >>> 盈利能力 = ROE×0.4 + 毛利率×0.3 + 净利率×0.3")
print(f"      = {roe_score:.2f}×0.4 + {gross_score:.2f}×0.3 + {net_score:.2f}×0.3")
print(f"      = {roe_score * 0.4 + gross_score * 0.3 + net_score * 0.3:.2f}")
if use_market_fallback:
    print(f"      × 折扣{discount} = {profit_score:.2f}")
print(f"  >>> 盈利能力得分: {profit_score:.2f}")

# ============================================================
# 第六步：成长性评分（权重30%）
# ============================================================
print("\n" + "=" * 70)
print("第六步：成长性评分（权重30%）")
print("=" * 70)

pool_rev = pool_values("revenue_yoy")
rev_score = 0.0
if target.get("revenue_yoy") is not None:
    rev_score = percentile_rank(target["revenue_yoy"], pool_rev)
    sorted_rev = sorted(pool_rev + [target["revenue_yoy"]], reverse=True)
    rank_rev = sorted_rev.index(target["revenue_yoy"]) + 1
    print(f"  [营收同比] 目标值: {target['revenue_yoy']}%")
    print(f"    行业池营收同比值: {sorted(pool_rev, reverse=True)}")
    print(f"    排名: {rank_rev}/{len(pool_rev)+1}")
    print(f"    营收同比得分: {rev_score:.2f}")

pool_prof = pool_values("profit_yoy")
prof_score = 0.0
if target.get("profit_yoy") is not None:
    prof_score = percentile_rank(target["profit_yoy"], pool_prof)
    sorted_prof = sorted(pool_prof + [target["profit_yoy"]], reverse=True)
    rank_prof = sorted_prof.index(target["profit_yoy"]) + 1
    print(f"\n  [净利同比] 目标值: {target['profit_yoy']}%")
    print(f"    行业池净利同比值: {sorted(pool_prof, reverse=True)}")
    print(f"    排名: {rank_prof}/{len(pool_prof)+1}")
    print(f"    净利同比得分: {prof_score:.2f}")

growth_score = (rev_score * 0.4 + prof_score * 0.6) * discount
print(f"\n  >>> 成长性 = 营收同比×0.4 + 净利同比×0.6")
print(f"      = {rev_score:.2f}×0.4 + {prof_score:.2f}×0.6")
print(f"      = {rev_score * 0.4 + prof_score * 0.6:.2f}")
if use_market_fallback:
    print(f"      × 折扣{discount} = {growth_score:.2f}")
print(f"  >>> 成长性得分: {growth_score:.2f}")

# ============================================================
# 第七步：现金流质量评分（权重20%）
# ============================================================
print("\n" + "=" * 70)
print("第七步：现金流质量评分（权重20%）")
print("=" * 70)

np_val = target.get("net_profit")
ocf_abs_val = target.get("ocf_abs")
ocf_val = None
ocf_score = 0.0

if np_val and ocf_abs_val and np_val != 0:
    ocf_val = round(ocf_abs_val / np_val * 100, 2)
    print(f"  归母净利润: {np_val}")
    print(f"  经营现金流: {ocf_abs_val}")
    print(f"  OCF/净利润 = {ocf_abs_val}/{np_val}×100 = {ocf_val}%")
    
    pool_ocf_vals = []
    for s in pool:
        if s.get("ts_code") == target["ts_code"]:
            continue
        s_np = s.get("net_profit")
        s_ocf = s.get("ocf_abs")
        if s_np and s_ocf and s_np != 0:
            pool_ocf_vals.append(round(s_ocf / s_np * 100, 2))
    
    print(f"  行业池OCF/净利润值: {sorted(pool_ocf_vals, reverse=True)}")
    if ocf_val is not None:
        ocf_score = percentile_rank(ocf_val, pool_ocf_vals)
        sorted_ocf = sorted(pool_ocf_vals + [ocf_val], reverse=True)
        rank_ocf = sorted_ocf.index(ocf_val) + 1
        print(f"  排名: {rank_ocf}/{len(pool_ocf_vals)+1}")
else:
    print(f"  无法计算OCF比 (净利润={np_val}, 经营现金流={ocf_abs_val})")

ocf_score *= discount
if use_market_fallback:
    print(f"  × 折扣{discount} = {ocf_score:.2f}")
print(f"  >>> 现金流质量得分: {ocf_score:.2f}")

# ============================================================
# 第八步：偿债风险评分（权重10%）
# ============================================================
print("\n" + "=" * 70)
print("第八步：偿债风险评分（权重10%）")
print("=" * 70)

pool_debt = pool_values("debt_ratio")
debt_score = 0.0
if target.get("debt_ratio") is not None:
    debt_score = percentile_rank(target["debt_ratio"], pool_debt, reverse=True)
    print(f"  [负债率] 目标值: {target['debt_ratio']}% (越低越好)")
    print(f"  行业池负债率值: {sorted(pool_debt)}")
    sorted_debt = sorted(pool_debt + [target["debt_ratio"]])
    rank_debt = sorted_debt.index(target["debt_ratio"]) + 1
    print(f"  排名(低到高): {rank_debt}/{len(pool_debt)+1}")
    print(f"  负债率原始得分: {debt_score:.2f}")

debt_score *= discount
if use_market_fallback:
    print(f"  × 折扣{discount} = {debt_score:.2f}")
print(f"  >>> 偿债风险得分: {debt_score:.2f}")

# ============================================================
# 第九步：汇总总分
# ============================================================
print("\n" + "=" * 70)
print("第九步：汇总总分")
print("=" * 70)

total_score = (
    profit_score * 0.4 +
    growth_score * 0.3 +
    ocf_score * 0.2 +
    debt_score * 0.1
)

print(f"  总分 = 盈利能力×0.4 + 成长性×0.3 + 现金流×0.2 + 偿债×0.1")
print(f"      = {profit_score:.2f}×0.4 + {growth_score:.2f}×0.3 + {ocf_score:.2f}×0.2 + {debt_score:.2f}×0.1")
print(f"      = {profit_score * 0.4:.2f} + {growth_score * 0.3:.2f} + {ocf_score * 0.2:.2f} + {debt_score * 0.1:.2f}")
print(f"      = {total_score:.2f}")

# 完整度折扣
if level == "low":
    total_score *= Config.LOW_COMPLETENESS_PENALTY
    print(f"  完整度低，×{Config.LOW_COMPLETENESS_PENALTY} = {total_score:.2f}")
elif level == "ultra_low":
    total_score *= Config.LOW_COMPLETENESS_PENALTY * Config.ULTRA_LOW_COMPLETENESS_PENALTY
    print(f"  完整度极低，×{Config.LOW_COMPLETENESS_PENALTY * Config.ULTRA_LOW_COMPLETENESS_PENALTY} = {total_score:.2f}")

# 连续亏损惩罚
if np_val is not None and ocf_abs_val is not None and np_val < 0 and ocf_abs_val < 0:
    total_score = min(total_score, Config.NEGATIVE_PROFIT_PENALTY)
    print(f"  连续亏损惩罚，总分限制为: {total_score:.2f}")

# 评级
if total_score >= 75:
    grade = "A"
elif total_score >= 55:
    grade = "B"
elif total_score >= 40:
    grade = "C"
elif total_score >= 25:
    grade = "D"
else:
    grade = "E"

print(f"\n  >>> 最终总分: {round(total_score, 2)}")
print(f"  >>> 评级: {grade}")
print(f"  >>> 置信度: {confidence}")

print("\n" + "=" * 70)
print("汇总对比")
print("=" * 70)
print(f"  {'维度':<12} {'得分':>8} {'权重':>6} {'加权后':>8}")
print(f"  {'-'*40}")
print(f"  {'盈利能力':<12} {profit_score:>8.2f} {'40%':>6} {profit_score*0.4:>8.2f}")
print(f"  {'成长性':<12} {growth_score:>8.2f} {'30%':>6} {growth_score*0.3:>8.2f}")
print(f"  {'现金流质量':<12} {ocf_score:>8.2f} {'20%':>6} {ocf_score*0.2:>8.2f}")
print(f"  {'偿债风险':<12} {debt_score:>8.2f} {'10%':>6} {debt_score*0.1:>8.2f}")
print(f"  {'-'*40}")
print(f"  {'总分':<12} {'':>8} {'':>6} {round(total_score, 2):>8}")
print(f"  {'评级':<12} {grade:>8}")
print(f"  {'置信度':<12} {confidence:>8}")
print("=" * 70)

conn.close()
