#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, os, re
sys.path.insert(0, r'D:\Project\QAScorer')
from qa_scorer import _parse_single_block, _compute_ttm, _extract_all_report_sections

output = []

def check(name, actual, expected):
    passed = actual == expected
    status = "PASS" if passed else "FAIL"
    line = f"  [{status}] {name}: expected={expected}, actual={actual}"
    output.append(line)
    if not passed:
        output.append(f"    *** MISMATCH ***")
    return passed

all_pass = True

# 测试1: 基本关键词提取
output.append("=== 测试1: _parse_single_block 基本关键词 ===")
sample = """
营业总收入：1234567890.12元
营业成本：987654321.00元
归母净利润：123456789.00元
扣非归母净利润：111111111.00元
归母净利润同比增长：444.78%
营业收入同比增长：59.18%
销售毛利率：15.67%
销售净利率：8.45%
净利润现金含量：120.50%
经营活动产生的现金流量净额：150000000.00元
资产合计：5000000000.00元
负债合计：2000000000.00元
股东权益合计：3000000000.00元
资产负债率：40.00%
"""
r = _parse_single_block(sample)
for field, expected, label in [
    ('revenue', 1234567890.12, '营业总收入'),
    ('operating_cost', 987654321.00, '营业成本'),
    ('net_profit', 123456789.00, '归母净利润'),
    ('gross_margin', 15.67, '销售毛利率'),
    ('net_margin', 8.45, '销售净利率'),
    ('revenue_yoy', 59.18, '营业收入同比增长'),
    ('profit_yoy', 444.78, '归母净利润同比增长'),
    ('ocf_abs', 150000000.00, '经营活动现金流'),
    ('total_assets', 5000000000.00, '资产合计'),
    ('total_liabilities', 2000000000.00, '负债合计'),
    ('net_assets', 3000000000.00, '股东权益合计'),
    ('debt_ratio', 40.00, '资产负债率'),
]:
    if not check(label, r.get(field), expected):
        all_pass = False

# 测试2: 净利润严格行首匹配
output.append("\n=== 测试2: 净利润严格行首匹配 ===")
sample2 = """
归母净利润：100000000.00元
扣非归母净利润：90000000.00元
归母净利润同比增长：50.00%
归母净利润现金含量：120.00%
"""
r2 = _parse_single_block(sample2)
if not check('净利润(应排除扣非/同比/现金)', r2.get('net_profit'), 100000000.00):
    all_pass = False

# 测试3: 经营现金流直接提取
output.append("\n=== 测试3: 经营现金流直接提取 ===")
block1 = """
营业总收入：1000000000.00元
营业成本：800000000.00元
归母净利润：100000000.00元
销售毛利率：20.00%
销售净利率：10.00%
净利润现金含量：50.00%
经营活动产生的现金流量净额：200000000.00元
资产合计：5000000000.00元
负债合计：2000000000.00元
股东权益合计：3000000000.00元
"""
block2 = """
营业总收入：1100000000.00元
营业成本：880000000.00元
归母净利润：110000000.00元
销售毛利率：20.00%
销售净利率：10.00%
净利润现金含量：60.00%
经营活动产生的现金流量净额：250000000.00元
资产合计：5100000000.00元
负债合计：2100000000.00元
股东权益合计：3000000000.00元
"""
ttm = _compute_ttm([('2026','0331',block1), ('2025','1231',block2)])
if not check('OCF_TTM(直接累加)', ttm.get('ocf_abs_ttm'), 450000000.00):
    all_pass = False

# 测试4: 经营现金流兜底
output.append("\n=== 测试4: 经营现金流兜底(无直接OCF时) ===")
block3 = """
营业总收入：1000000000.00元
营业成本：800000000.00元
归母净利润：100000000.00元
销售毛利率：20.00%
销售净利率：10.00%
净利润现金含量：50.00%
资产合计：5000000000.00元
负债合计：2000000000.00元
股东权益合计：3000000000.00元
"""
ttm2 = _compute_ttm([('2026','0331',block3)])
if not check('OCF兜底(净利润现金含量)', ttm2.get('ocf_abs_ttm'), 50000000.00):
    all_pass = False

# 测试5: 资产负债率
output.append("\n=== 测试5: 资产负债率 ===")
block_a = """
资产合计：5000000000.00元
负债合计：2000000000.00元
资产负债率：35.00%
"""
r_a = _parse_single_block(block_a)
if not check('场景A(直接提取35%)', r_a.get('debt_ratio'), 35.00):
    all_pass = False

block_b = """
资产合计：5000000000.00元
负债合计：2000000000.00元
"""
r_b = _parse_single_block(block_b)
if not check('场景B(负债/资产=40%)', r_b.get('debt_ratio'), 40.0):
    all_pass = False

# 测试6: 财报段落拆分
output.append("\n=== 测试6: 财报段落拆分 ===")
sample_text = """
根据神农种业在A股市场20251231发布的财报数据，统计截止日期为20251231的Q4单季报:
营业总收入：500000000.00元
归母净利润：50000000.00元
营业收入同比增长：30.00%
归母净利润同比增长：200.00%
资产合计：3000000000.00元
负债合计：1000000000.00元

根据神农种业在A股市场20251231发布的财报数据，统计截止日期为20251231的年报:
营业总收入：2000000000.00元
归母净利润：200000000.00元
营业收入同比增长：25.00%
归母净利润同比增长：150.00%
加权净资产收益率ROE：15.00%
资产合计：3000000000.00元
负债合计：1000000000.00元
"""
sections = _extract_all_report_sections(sample_text)
if not check('拆分段落数', len(sections), 2):
    all_pass = False

quarterly = [(d, t, txt) for d, t, txt in sections if "季报" in t]
annual = [(d, t, txt) for d, t, txt in sections if "年报" in t]
if not check('单季报段落数', len(quarterly), 1):
    all_pass = False
if not check('年报段落数', len(annual), 1):
    all_pass = False

# 测试7: 最新单季指标
output.append("\n=== 测试7: 最新单季指标(营收同比/净利润同比) ===")
if quarterly:
    latest = _parse_single_block(quarterly[0][2])
else:
    latest = _parse_single_block(sections[0][2])
if not check('营收同比(从单季报)', latest.get('revenue_yoy'), 30.00):
    all_pass = False
if not check('净利润同比(从单季报)', latest.get('profit_yoy'), 200.00):
    all_pass = False

# 测试8: 营收同比兜底到年报
output.append("\n=== 测试8: 营收同比兜底(单季报无时从年报取) ===")
sample_text2 = """
根据神农种业在A股市场20260331发布的财报数据，统计截止日期为20260331的Q1单季报:
营业总收入：600000000.00元
归母净利润：100000000.00元
归母净利润同比增长：444.78%
资产合计：3500000000.00元
负债合计：1200000000.00元
股东权益合计：2300000000.00元

根据神农种业在A股市场20251231发布的财报数据，统计截止日期为20251231的年报:
营业总收入：2000000000.00元
归母净利润：200000000.00元
营业收入同比增长：25.00%
归母净利润同比增长：150.00%
资产合计：3000000000.00元
负债合计：1000000000.00元
"""
sections2 = _extract_all_report_sections(sample_text2)
quarterly2 = [(d, t, txt) for d, t, txt in sections2 if "季报" in t]
annual2 = [(d, t, txt) for d, t, txt in sections2 if "年报" in t]
if quarterly2:
    latest2 = _parse_single_block(quarterly2[0][2])
else:
    latest2 = _parse_single_block(sections2[0][2])
# 单季报没有营收同比，应从年报取
if latest2.get('revenue_yoy') is None and annual2:
    annual_parsed = _parse_single_block(annual2[0][2])
    if annual_parsed.get('revenue_yoy') is not None:
        latest2['revenue_yoy'] = annual_parsed['revenue_yoy']
if not check('营收同比(从年报兜底)', latest2.get('revenue_yoy'), 25.00):
    all_pass = False

# 汇总
output.append("\n" + "=" * 60)
output.append("测试汇总")
output.append("=" * 60)
if all_pass:
    output.append("ALL PASS")
else:
    output.append("SOME FAILED")

# 写文件
with open(r'D:\Project\QAScorer\test_results.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(output))

# 同时打印
for line in output:
    print(line)

sys.exit(0 if all_pass else 1)
