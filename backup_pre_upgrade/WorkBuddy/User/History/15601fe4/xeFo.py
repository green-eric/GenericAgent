#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
离线验证9个核心字段 — 使用已保存的API原始文本
"""
import sys, os, re
sys.path.insert(0, r'D:\Project\QAScorer')
os.chdir(r'D:\Project\QAScorer')

from qa_scorer import (
    _extract_all_report_sections,
    _parse_single_block,
    _compute_ttm,
)

output = []

# 使用已保存的300189原始文本
with open(r'D:\Project\QAScorer\debug_300189_raw.txt', 'r', encoding='utf-8') as f:
    text = f.read()

ts_code, name = "300189.SZ", "神农种业"

output.append(f"{'='*80}")
output.append(f"股票: {ts_code} {name}")
output.append(f"{'='*80}")

sections = _extract_all_report_sections(text)
quarterly = [(d, t, txt) for d, t, txt in sections if "季报" in t]
annual = [(d, t, txt) for d, t, txt in sections if "年报" in t]

output.append(f"\n段落拆分: {len(quarterly)}个单季报, {len(annual)}个年报")

# 打印每个单季报的关键字段
output.append(f"\n{'─'*60}")
output.append("各单季报段落提取详情:")
output.append(f"{'─'*60}")
for i, (d, t, txt) in enumerate(quarterly):
    p = _parse_single_block(txt)
    output.append(f"\n  [{i+1}] {d} {t}:")
    output.append(f"    revenue={p.get('revenue')}, net_profit={p.get('net_profit')}")
    output.append(f"    revenue_yoy={p.get('revenue_yoy')}, profit_yoy={p.get('profit_yoy')}")
    output.append(f"    debt_ratio={p.get('debt_ratio')}, ocf_abs={p.get('ocf_abs')}, ocf_ratio={p.get('ocf_ratio')}")
    output.append(f"    total_assets={p.get('total_assets')}, total_liab={p.get('total_liabilities')}, net_assets={p.get('net_assets')}")

# 打印年报的关键字段
output.append(f"\n{'─'*60}")
output.append("各年报段落提取详情:")
output.append(f"{'─'*60}")
for i, (d, t, txt) in enumerate(annual):
    p = _parse_single_block(txt)
    output.append(f"\n  [{i+1}] {d} {t}:")
    output.append(f"    revenue={p.get('revenue')}, net_profit={p.get('net_profit')}")
    output.append(f"    revenue_yoy={p.get('revenue_yoy')}, profit_yoy={p.get('profit_yoy')}")
    output.append(f"    debt_ratio={p.get('debt_ratio')}, ocf_abs={p.get('ocf_abs')}, ocf_ratio={p.get('ocf_ratio')}")
    output.append(f"    gross_margin={p.get('gross_margin')}, net_margin={p.get('net_margin')}")
    output.append(f"    total_assets={p.get('total_assets')}, total_liab={p.get('total_liabilities')}, net_assets={p.get('net_assets')}")

# 最新单季报
latest_q_date, latest_q_type, latest_q_text = quarterly[0]
latest = _parse_single_block(latest_q_text)

# TTM计算
ttm_blocks = [(d[:4], d[4:], txt) for d, _, txt in quarterly]
ttm = _compute_ttm(ttm_blocks)

# 最终9个字段
revenue_yoy = latest.get("revenue_yoy")
profit_yoy = latest.get("profit_yoy")
debt_ratio = latest.get("debt_ratio")

if revenue_yoy is None and annual:
    annual_parsed = _parse_single_block(annual[0][2])
    revenue_yoy = annual_parsed.get("revenue_yoy")

if profit_yoy is None and annual:
    annual_parsed = _parse_single_block(annual[0][2])
    profit_yoy = annual_parsed.get("profit_yoy")

if debt_ratio is None:
    ta = latest.get("total_assets")
    tl = latest.get("total_liabilities")
    if ta and tl and ta > 0:
        debt_ratio = round(tl / ta * 100, 2)

output.append(f"\n{'='*80}")
output.append("最终9个字段取值:")
output.append(f"{'='*80}")
output.append(f"  1. ROE(%)(TTM):         {ttm.get('roe_ttm')}")
output.append(f"  2. 毛利率(%)(TTM):      {ttm.get('gross_margin_ttm')}")
output.append(f"  3. 净利率(%)(TTM):      {ttm.get('net_margin_ttm')}")
output.append(f"  4. 营收同比(%)(单季):   {revenue_yoy}")
output.append(f"  5. 净利润同比(%)(单季): {profit_yoy}")
output.append(f"  6. 资产负债率(%)(单季): {debt_ratio}")
output.append(f"  7. OCF/净利润(%)(TTM):  {ttm.get('ocf_ratio_ttm')}")
output.append(f"  8. 净利润(元)(TTM):     {ttm.get('net_profit_ttm')}")
output.append(f"  9. 经营现金流(元)(TTM): {ttm.get('ocf_abs_ttm')}")

# 检查异常
output.append(f"\n{'='*80}")
output.append("异常检查:")
output.append(f"{'='*80}")

issues = []

# 检查1: ROE_TTM 是否为None
if ttm.get('roe_ttm') is None:
    # 检查是否有净资产
    na = latest.get('net_assets')
    np_ttm = ttm.get('net_profit_ttm')
    issues.append(f"  ⚠️ ROE_TTM=None (net_assets={na}, net_profit_ttm={np_ttm})")
    if na is None:
        issues.append(f"    → 最新单季报没有净资产数据，尝试从年报获取...")
        if annual:
            ann_p = _parse_single_block(annual[0][2])
            issues.append(f"    → 年报净资产: {ann_p.get('net_assets')}")

# 检查2: 营收同比是否为None
if revenue_yoy is None:
    issues.append(f"  ⚠️ 营收同比=None (单季报和年报都没有)")

# 检查3: 净利润同比是否为None
if profit_yoy is None:
    issues.append(f"  ⚠️ 净利润同比=None")

# 检查4: 资产负债率是否为None
if debt_ratio is None:
    issues.append(f"  ⚠️ 资产负债率=None (total_assets={latest.get('total_assets')}, total_liab={latest.get('total_liabilities')})")

# 检查5: OCF/净利润_TTM是否为None
if ttm.get('ocf_ratio_ttm') is None:
    issues.append(f"  ⚠️ OCF/净利润_TTM=None (ocf_abs_ttm={ttm.get('ocf_abs_ttm')}, net_profit_ttm={ttm.get('net_profit_ttm')})")

# 检查6: 经营现金流_TTM是否为None
if ttm.get('ocf_abs_ttm') is None:
    issues.append(f"  ⚠️ 经营现金流_TTM=None")

if issues:
    for issue in issues:
        output.append(issue)
else:
    output.append("  ✅ 所有字段均有值，无异常")

result = '\n'.join(output)
with open(r'D:\Project\QAScorer\verify_9fields_output.txt', 'w', encoding='utf-8') as f:
    f.write(result)
print(result)
