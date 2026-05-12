#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对照用户给出的字段表格，逐一检查每个字段的提取关键词是否正确
"""
import os, re

# 用户给出的规范
SPEC = {
    "ROE": {
        "keywords": ["加权净资产收益率ROE", "净资产收益率ROE"],
        "unit": "%",
        "source": "TTM",
        "note": "TTM ROE = 净利润TTM / 最新净资产 × 100"
    },
    "毛利率": {
        "keywords": ["销售毛利率"],
        "unit": "%",
        "source": "TTM",
        "note": "TTM毛利率 = (营收TTM - 成本TTM) / 营收TTM × 100"
    },
    "净利率": {
        "keywords": ["销售净利率"],
        "unit": "%",
        "source": "TTM",
        "note": "TTM净利率 = 净利润TTM / 营收TTM × 100"
    },
    "营收同比": {
        "keywords": ["营业收入同比增长", "营收同比增长"],
        "unit": "%",
        "source": "最新单季",
        "note": "单季报无营收同比时从年报取"
    },
    "净利润同比": {
        "keywords": ["归母净利润同比增长"],
        "unit": "%",
        "source": "最新单季",
        "note": "严格匹配归母净利润同比增长"
    },
    "资产负债率": {
        "keywords": ["资产负债率"],
        "unit": "%",
        "source": "最新单季",
        "note": "从最新单季报取（或计算：负债合计/资产合计）"
    },
    "净利润(TTM)": {
        "keywords": ["归母净利润"],  # 严格行首匹配，排除同比/扣非
        "unit": "元",
        "source": "TTM",
        "note": "近4个季度归母净利润之和"
    },
    "经营现金流(TTM)": {
        "keywords": ["经营活动产生的现金流量净额"],
        "unit": "元",
        "source": "TTM",
        "note": "近4个季度经营现金流之和（或用净利润现金含量×净利润计算）"
    },
}

# 当前代码中的提取逻辑（从 _parse_single_block 和 _compute_ttm 中提取）
CURRENT_CODE = {
    "ROE": {
        "code_keywords": ["加权净资产收益率ROE", "净资产收益率ROE"],  # 在_parse_single_block中没有直接提取ROE
        "source": "_compute_ttm中计算: profit_sum / net_assets * 100",
        "actual_keywords_in_code": "ROE不在_parse_single_block中提取，而是在_compute_ttm中用净利润TTM/净资产计算"
    },
    "毛利率": {
        "code_keywords": ["销售毛利率"],
        "source": "_compute_ttm中计算: (revenue_sum - cost_sum) / revenue_sum * 100",
        "parse_keywords": "毛利率[：:\\s]*([-+]?\\d+\\.?\\d*)%"
    },
    "净利率": {
        "code_keywords": ["销售净利率"],
        "source": "_compute_ttm中计算: profit_sum / revenue_sum * 100",
        "parse_keywords": "净利率[：:\\s]*([-+]?\\d+\\.?\\d*)%"
    },
    "营收同比": {
        "code_keywords": ["营业收入同比增长", "营收同比增长", "营业总收入同比增长"],
        "source": "最新单季报段落，没有则从最新年报取"
    },
    "净利润同比": {
        "code_keywords": ["归母净利润同比增长"],
        "source": "最新单季报段落，没有则从最新年报取"
    },
    "资产负债率": {
        "code_keywords": ["资产负债率"],
        "source": "最新单季报，用负债合计/资产合计计算"
    },
    "净利润(TTM)": {
        "code_keywords": ["归母净利润"],
        "source": "_compute_ttm中累加近4个季度",
        "note": "行首匹配^归母净利润，排除同比/扣非"
    },
    "经营现金流(TTM)": {
        "code_keywords": ["经营活动产生的现金流量净额"],
        "source": "_compute_ttm中: ocf_ratio * profit 累加",
        "note": "用净利润现金含量×净利润计算，而非直接取经营活动现金流"
    },
}

print("=" * 80)
print("字段提取逻辑对照检查")
print("=" * 80)

# 读取源代码
with open(r'D:\Project\QAScorer\qa_scorer.py', 'r', encoding='utf-8') as f:
    source = f.read()

# 检查每个字段
issues = []

# 1. ROE - 检查代码中是否有直接提取ROE关键词
print("\n[ROE]")
print("  规范: 加权净资产收益率ROE / 净资产收益率ROE")
if "加权净资产收益率" in source:
    print("  ✅ 代码中包含'加权净资产收益率'")
else:
    print("  ❌ 代码中未找到'加权净资产收益率'")
    issues.append("ROE: 代码未提取'加权净资产收益率ROE'")
if "净资产收益率" in source:
    print("  ✅ 代码中包含'净资产收益率'")
else:
    print("  ❌ 代码中未找到'净资产收益率'")

# 检查ROE在_parse_single_block中是否被提取
if 'result["roe"]' in source or "result['roe']" in source:
    print("  ✅ _parse_single_block中有roe字段")
else:
    print("  ⚠️ _parse_single_block中无roe字段（ROE通过TTM计算）")

# 2. 毛利率
print("\n[毛利率]")
print("  规范: 销售毛利率")
if "销售毛利率" in source:
    print("  ✅ 代码中包含'销售毛利率'")
else:
    print("  ❌ 代码中未找到'销售毛利率'")
    issues.append("毛利率: 代码未提取'销售毛利率'")

# 3. 净利率
print("\n[净利率]")
print("  规范: 销售净利率")
if "销售净利率" in source:
    print("  ✅ 代码中包含'销售净利率'")
else:
    print("  ❌ 代码中未找到'销售净利率'")
    issues.append("净利率: 代码未提取'销售净利率'")

# 4. 营收同比
print("\n[营收同比]")
print("  规范: 营业收入同比增长 / 营收同比增长")
if "营业收入同比增长" in source:
    print("  ✅ 代码中包含'营业收入同比增长'")
else:
    print("  ❌ 代码中未找到'营业收入同比增长'")
    issues.append("营收同比: 代码未提取'营业收入同比增长'")
if "营收同比增长" in source:
    print("  ✅ 代码中包含'营收同比增长'（兜底）")

# 5. 净利润同比
print("\n[净利润同比]")
print("  规范: 归母净利润同比增长（严格匹配）")
if "归母净利润同比增长" in source:
    print("  ✅ 代码中包含'归母净利润同比增长'")
else:
    print("  ❌ 代码中未找到'归母净利润同比增长'")
    issues.append("净利润同比: 代码未提取'归母净利润同比增长'")

# 6. 资产负债率
print("\n[资产负债率]")
print("  规范: 资产负债率（从最新单季）")
if "资产负债率" in source:
    print("  ✅ 代码中包含'资产负债率'")
else:
    print("  ⚠️ 代码中未直接提取'资产负债率'（通过负债/资产计算）")

# 7. 净利润(TTM)
print("\n[净利润(TTM)]")
print("  规范: ^归母净利润（严格行首匹配，排除同比/扣非）")
# 检查代码中是否有行首匹配
if 'r"^归母净利润"' in source or "r'^归母净利润'" in source:
    print("  ✅ 代码中使用行首匹配^归母净利润")
else:
    print("  ⚠️ 代码中未使用行首匹配，使用包含匹配'归母净利润'")
    print("  当前代码: '归母净利润' in line and '同比' not in line and '环比' not in line")
    issues.append("净利润: 未使用严格行首匹配^归母净利润")

# 检查是否排除了扣非
if "扣非净利润" in source and "扣非" in source:
    print("  ✅ 代码中排除了'扣非净利润'")
else:
    print("  ⚠️ 代码中未明确排除扣非净利润")

# 8. 经营现金流(TTM)
print("\n[经营现金流(TTM)]")
print("  规范: 经营活动产生的现金流量净额")
if "经营活动产生的现金流量净额" in source:
    print("  ✅ 代码中包含'经营活动产生的现金流量净额'")
else:
    print("  ❌ 代码中未找到'经营活动产生的现金流量净额'")
    issues.append("经营现金流: 代码未提取'经营活动产生的现金流量净额'")

# 额外检查：净利润现金含量 vs 直接取经营活动现金流
print("\n[经营现金流计算方式检查]")
if "净利润现金含量" in source:
    print("  ⚠️ 代码使用'净利润现金含量×净利润'计算OCF，而非直接取'经营活动产生的现金流量净额'")
    issues.append("经营现金流: 使用净利润现金含量计算，而非直接取经营活动现金流绝对值")

print("\n" + "=" * 80)
print("问题汇总")
print("=" * 80)
if issues:
    for i, issue in enumerate(issues, 1):
        print(f"  {i}. {issue}")
else:
    print("  所有字段提取逻辑与规范一致 ✅")
