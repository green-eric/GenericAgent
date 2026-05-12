#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证9个核心字段的取值准确性
直接用API返回的原始文本，逐步打印每个字段的提取过程
"""
import sys, os, re, io
sys.path.insert(0, r'D:\Project\QAScorer')
os.chdir(r'D:\Project\QAScorer')

from qa_scorer import (
    _extract_all_report_sections,
    _parse_single_block,
    _compute_ttm,
    load_token,
)

token = load_token()

# 测试股票
TEST_STOCKS = [
    ("300189.SZ", "神农种业"),
    ("600519.SH", "贵州茅台"),
    ("000001.SZ", "平安银行"),
    ("300750.SZ", "宁德时代"),
]

output = []

for ts_code, name in TEST_STOCKS:
    output.append(f"\n{'='*80}")
    output.append(f"股票: {ts_code} {name}")
    output.append(f"{'='*80}")

    # 获取API数据
    from qa_scorer import run_neodata
    query = f"{ts_code} {name} 最新季报"
    text = run_neodata(query, token)

    if not text:
        output.append("  API返回为空!")
        continue

    # 段落拆分
    sections = _extract_all_report_sections(text)
    quarterly = [(d, t, txt) for d, t, txt in sections if "季报" in t]
    annual = [(d, t, txt) for d, t, txt in sections if "年报" in t]

    output.append(f"\n段落拆分: {len(quarterly)}个单季报, {len(annual)}个年报")

    # 最新单季报
    if quarterly:
        latest_q_date, latest_q_type, latest_q_text = quarterly[0]
        output.append(f"\n最新单季报: {latest_q_date} {latest_q_type}")
        latest = _parse_single_block(latest_q_text)

        output.append(f"  _parse_single_block 提取结果:")
        output.append(f"    revenue:      {latest.get('revenue')}")
        output.append(f"    net_profit:   {latest.get('net_profit')}")
        output.append(f"    revenue_yoy:  {latest.get('revenue_yoy')}")
        output.append(f"    profit_yoy:   {latest.get('profit_yoy')}")
        output.append(f"    debt_ratio:   {latest.get('debt_ratio')}")
        output.append(f"    ocf_abs:      {latest.get('ocf_abs')}")
        output.append(f"    ocf_ratio:    {latest.get('ocf_ratio')}")
        output.append(f"    total_assets: {latest.get('total_assets')}")
        output.append(f"    total_liab:   {latest.get('total_liabilities')}")
        output.append(f"    net_assets:   {latest.get('net_assets')}")
    else:
        output.append("  没有单季报段落!")
        continue

    # TTM计算
    if quarterly:
        ttm_blocks = [(d[:4], d[4:], txt) for d, _, txt in quarterly]
        ttm = _compute_ttm(ttm_blocks)
    else:
        ttm = {}

    output.append(f"\nTTM计算结果:")
    output.append(f"  revenue_ttm:      {ttm.get('revenue_ttm')}")
    output.append(f"  net_profit_ttm:   {ttm.get('net_profit_ttm')}")
    output.append(f"  gross_margin_ttm: {ttm.get('gross_margin_ttm')}")
    output.append(f"  net_margin_ttm:   {ttm.get('net_margin_ttm')}")
    output.append(f"  roe_ttm:          {ttm.get('roe_ttm')}")
    output.append(f"  ocf_abs_ttm:      {ttm.get('ocf_abs_ttm')}")
    output.append(f"  ocf_ratio_ttm:    {ttm.get('ocf_ratio_ttm')}")

    # 最终9个字段
    revenue_yoy = latest.get("revenue_yoy")
    profit_yoy = latest.get("profit_yoy")
    debt_ratio = latest.get("debt_ratio")

    # 营收同比兜底
    if revenue_yoy is None and annual:
        annual_parsed = _parse_single_block(annual[0][2])
        revenue_yoy = annual_parsed.get("revenue_yoy")

    # 净利润同比兜底
    if profit_yoy is None and annual:
        annual_parsed = _parse_single_block(annual[0][2])
        profit_yoy = annual_parsed.get("profit_yoy")

    # 资产负债率兜底
    if debt_ratio is None:
        ta = latest.get("total_assets")
        tl = latest.get("total_liabilities")
        if ta and tl and ta > 0:
            debt_ratio = round(tl / ta * 100, 2)

    output.append(f"\n{'─'*60}")
    output.append(f"最终9个字段 (merge_annual_quarterly 之后):")
    output.append(f"{'─'*60}")
    output.append(f"  1. ROE(%)(TTM):         {ttm.get('roe_ttm')}")
    output.append(f"  2. 毛利率(%)(TTM):      {ttm.get('gross_margin_ttm')}")
    output.append(f"  3. 净利率(%)(TTM):      {ttm.get('net_margin_ttm')}")
    output.append(f"  4. 营收同比(%)(单季):   {revenue_yoy}")
    output.append(f"  5. 净利润同比(%)(单季): {profit_yoy}")
    output.append(f"  6. 资产负债率(%)(单季): {debt_ratio}")
    output.append(f"  7. OCF/净利润(%)(TTM):  {ttm.get('ocf_ratio_ttm')}")
    output.append(f"  8. 净利润(元)(TTM):     {ttm.get('net_profit_ttm')}")
    output.append(f"  9. 经营现金流(元)(TTM): {ttm.get('ocf_abs_ttm')}")

# 写文件
result = '\n'.join(output)
with open(r'D:\Project\QAScorer\verify_9fields_output.txt', 'w', encoding='utf-8') as f:
    f.write(result)
print(result)
