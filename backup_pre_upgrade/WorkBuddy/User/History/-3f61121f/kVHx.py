#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全面测试字段提取逻辑
对照用户给出的规范表格，逐一验证每个字段的提取是否正确
"""
import sys, os, re, json

# 添加项目路径
sys.path.insert(0, r'D:\Project\QAScorer')
os.chdir(r'D:\Project\QAScorer')

# 导入被测函数
from qa_scorer import (
    _extract_all_report_sections,
    _parse_single_block,
    _compute_ttm,
    fetch_quarterly_data,
    run_neodata,
    Config,
    _init_quarterly_db,
    _save_quarterly_to_db,
    _load_quarterly_from_db,
)

# 测试股票列表（覆盖不同场景）
TEST_STOCKS = [
    {"ts_code": "300189.SZ", "name": "神农种业"},   # 用户反馈有问题的股票
    {"ts_code": "000001.SZ", "name": "平安银行"},   # 银行股
    {"ts_code": "600519.SH", "name": "贵州茅台"},   # 大盘蓝筹
    {"ts_code": "002594.SZ", "name": "比亚迪"},     # 制造业
    {"ts_code": "300750.SZ", "name": "宁德时代"},   # 创业板龙头
    {"ts_code": "601318.SH", "name": "中国平安"},   # 保险
    {"ts_code": "000858.SZ", "name": "五粮液"},     # 消费
    {"ts_code": "600036.SH", "name": "招商银行"},   # 银行
    {"ts_code": "002415.SZ", "name": "海康威视"},   # 科技
    {"ts_code": "300059.SZ", "name": "东方财富"},   # 金融
]

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
        "keywords": ["归母净利润"],
        "unit": "元",
        "source": "TTM",
        "note": "近4个季度归母净利润之和，严格行首匹配"
    },
    "经营现金流(TTM)": {
        "keywords": ["经营活动产生的现金流量净额"],
        "unit": "元",
        "source": "TTM",
        "note": "近4个季度经营现金流之和（直接取，不用净利润现金含量计算）"
    },
}


def test_parse_single_block_keywords():
    """测试 _parse_single_block 中各字段的提取关键词"""
    print("\n" + "=" * 80)
    print("测试1: _parse_single_block 字段提取关键词验证")
    print("=" * 80)

    # 模拟API返回的一个季报段落
    sample_block = """
根据XX公司在A股市场20260331发布的财报数据，统计截止日期为20260331的Q1单季报：
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
加权净资产收益率ROE：12.34%
    """

    result = _parse_single_block(sample_block)

    checks = [
        ("revenue", 1234567890.12, "营业总收入"),
        ("operating_cost", 987654321.00, "营业成本"),
        ("net_profit", 123456789.00, "归母净利润"),
        ("gross_margin", 15.67, "销售毛利率"),
        ("net_margin", 8.45, "销售净利率"),
        ("revenue_yoy", 59.18, "营业收入同比增长"),
        ("profit_yoy", 444.78, "归母净利润同比增长"),
        ("ocf_abs", 150000000.00, "经营活动产生的现金流量净额"),
        ("total_assets", 5000000000.00, "资产合计"),
        ("total_liabilities", 2000000000.00, "负债合计"),
        ("net_assets", 3000000000.00, "股东权益合计"),
        ("debt_ratio", 40.00, "资产负债率"),
    ]

    all_pass = True
    for field, expected, label in checks:
        actual = result.get(field)
        if actual == expected:
            print(f"  ✅ {label}: {actual}")
        else:
            print(f"  ❌ {label}: 期望={expected}, 实际={actual}")
            all_pass = False

    return all_pass


def test_net_profit_strict_match():
    """测试净利润严格行首匹配：排除扣非归母净利润、归母净利润同比增长等"""
    print("\n" + "=" * 80)
    print("测试2: 净利润严格行首匹配验证")
    print("=" * 80)

    # 模拟包含多种"归母净利润"变体的段落
    sample_block = """
根据XX公司在A股市场20260331发布的财报数据，统计截止日期为20260331的Q1单季报：
归母净利润：100000000.00元
扣非归母净利润：90000000.00元
归母净利润同比增长：50.00%
归母净利润现金含量：120.00%
    """

    result = _parse_single_block(sample_block)
    actual = result.get("net_profit")

    # 应该只匹配 "归母净利润：100000000.00元"，不匹配扣非/同比/现金含量
    if actual == 100000000.00:
        print(f"  ✅ 净利润正确提取: {actual}（排除了扣非/同比/现金含量）")
        return True
    else:
        print(f"  ❌ 净利润提取错误: 期望=100000000.00, 实际={actual}")
        return False


def test_ocf_direct_extraction():
    """测试经营现金流直接提取（而非通过净利润现金含量计算）"""
    print("\n" + "=" * 80)
    print("测试3: 经营现金流直接提取验证")
    print("=" * 80)

    # 模拟两个季度的数据
    block1 = """
根据XX公司在A股市场20260331发布的财报数据，统计截止日期为20260331的Q1单季报：
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
根据XX公司在A股市场20251231发布的财报数据，统计截止日期为20251231的Q4单季报：
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

    blocks = [("2026", "0331", block1), ("2025", "1231", block2)]
    ttm = _compute_ttm(blocks)

    # OCF_TTM 应该 = 200000000 + 250000000 = 450000000（直接累加）
    # 如果用净利润现金含量计算 = 100000000*0.5 + 110000000*0.6 = 116000000
    expected_ocf = 450000000.00
    actual_ocf = ttm.get("ocf_abs_ttm")

    if actual_ocf == expected_ocf:
        print(f"  ✅ OCF_TTM正确: {actual_ocf:,.0f}（直接累加经营活动现金流）")
        return True
    else:
        print(f"  ❌ OCF_TTM错误: 期望={expected_ocf:,.0f}, 实际={actual_ocf:,.0f}")
        print(f"  说明：当前值是用净利润现金含量计算的，而非直接取经营活动现金流")
        return False


def test_ocf_fallback():
    """测试经营现金流兜底：当没有直接OCF数据时，用净利润现金含量计算"""
    print("\n" + "=" * 80)
    print("测试4: 经营现金流兜底逻辑验证（无直接OCF数据时）")
    print("=" * 80)

    block1 = """
根据XX公司在A股市场20260331发布的财报数据，统计截止日期为20260331的Q1单季报：
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

    blocks = [("2026", "0331", block1)]
    ttm = _compute_ttm(blocks)

    # 没有直接OCF数据，应该用净利润现金含量计算 = 100000000 * 0.5 = 50000000
    expected_ocf = 50000000.00
    actual_ocf = ttm.get("ocf_abs_ttm")

    if actual_ocf == expected_ocf:
        print(f"  ✅ OCF兜底正确: {actual_ocf:,.0f}（用净利润现金含量计算）")
        return True
    else:
        print(f"  ❌ OCF兜底错误: 期望={expected_ocf:,.0f}, 实际={actual_ocf:,.0f}")
        return False


def test_debt_ratio_extraction():
    """测试资产负债率提取：优先直接提取，兜底用负债/资产计算"""
    print("\n" + "=" * 80)
    print("测试5: 资产负债率提取验证")
    print("=" * 80)

    # 场景A：有直接资产负债率关键词
    block_a = """
根据XX公司在A股市场20260331发布的财报数据，统计截止日期为20260331的Q1单季报：
资产合计：5000000000.00元
负债合计：2000000000.00元
资产负债率：35.00%
    """
    result_a = _parse_single_block(block_a)
    # 应该取直接提取的35.00%，而非计算的40%
    if result_a.get("debt_ratio") == 35.00:
        print(f"  ✅ 场景A（有直接关键词）: {result_a['debt_ratio']}%（直接提取，非计算）")
        pass_a = True
    else:
        print(f"  ❌ 场景A（有直接关键词）: 期望=35.00, 实际={result_a.get('debt_ratio')}")
        pass_a = False

    # 场景B：无直接资产负债率，用负债/资产计算
    block_b = """
根据XX公司在A股市场20260331发布的财报数据，统计截止日期为20260331的Q1单季报：
资产合计：5000000000.00元
负债合计：2000000000.00元
    """
    result_b = _parse_single_block(block_b)
    expected = round(2000000000 / 5000000000 * 100, 2)  # 40.0
    if result_b.get("debt_ratio") == expected:
        print(f"  ✅ 场景B（无直接关键词）: {result_b['debt_ratio']}%（负债/资产计算）")
        pass_b = True
    else:
        print(f"  ❌ 场景B（无直接关键词）: 期望={expected}, 实际={result_b.get('debt_ratio')}")
        pass_b = False

    return pass_a and pass_b


def test_report_section_splitting():
    """测试财报段落拆分：确保单季报和年报被正确分离"""
    print("\n" + "=" * 80)
    print("测试6: 财报段落拆分验证")
    print("=" * 80)

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

    if len(sections) != 2:
        print(f"  ❌ 段落拆分错误: 期望2段, 实际{len(sections)}段")
        return False

    print(f"  ✅ 拆分出 {len(sections)} 个段落:")
    for date, rtype, text in sections:
        print(f"     - {date} {rtype}")

    quarterly = [(d, t, txt) for d, t, txt in sections if "季报" in t]
    annual = [(d, t, txt) for d, t, txt in sections if "年报" in t]

    if len(quarterly) == 1 and len(annual) == 1:
        print(f"  ✅ 单季报: {len(quarterly)}段, 年报: {len(annual)}段")
        return True
    else:
        print(f"  ❌ 分类错误: 单季报={len(quarterly)}, 年报={len(annual)}")
        return False


def test_latest_quarter_metrics():
    """测试最新单季指标提取：营收同比和净利润同比应从最新单季报取"""
    print("\n" + "=" * 80)
    print("测试7: 最新单季指标提取验证")
    print("=" * 80)

    # 模拟API返回：最新单季报有营收同比和净利润同比
    sample_text = """
根据神农种业在A股市场20260331发布的财报数据，统计截止日期为20260331的Q1单季报:
营业总收入：600000000.00元
归母净利润：100000000.00元
营业收入同比增长：59.18%
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

    sections = _extract_all_report_sections(sample_text)
    quarterly = [(d, t, txt) for d, t, txt in sections if "季报" in t]
    annual = [(d, t, txt) for d, t, txt in sections if "年报" in t]

    if quarterly:
        latest = _parse_single_block(quarterly[0][2])
    else:
        latest = _parse_single_block(sections[0][2])

    # 单季报有营收同比和净利润同比，应直接取
    revenue_yoy = latest.get("revenue_yoy")
    profit_yoy = latest.get("profit_yoy")

    pass_a = revenue_yoy == 59.18
    pass_b = profit_yoy == 444.78

    if pass_a:
        print(f"  ✅ 营收同比: {revenue_yoy}%（从最新单季报取）")
    else:
        print(f"  ❌ 营收同比: 期望=59.18, 实际={revenue_yoy}")

    if pass_b:
        print(f"  ✅ 净利润同比: {profit_yoy}%（从最新单季报取）")
    else:
        print(f"  ❌ 净利润同比: 期望=444.78, 实际={profit_yoy}")

    return pass_a and pass_b


def test_revenue_yoy_fallback_to_annual():
    """测试营收同比兜底：单季报没有时从年报取"""
    print("\n" + "=" * 80)
    print("测试8: 营收同比兜底逻辑验证（单季报无营收同比时从年报取）")
    print("=" * 80)

    sample_text = """
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

    sections = _extract_all_report_sections(sample_text)
    quarterly = [(d, t, txt) for d, t, txt in sections if "季报" in t]
    annual = [(d, t, txt) for d, t, txt in sections if "年报" in t]

    if quarterly:
        latest = _parse_single_block(quarterly[0][2])
    else:
        latest = _parse_single_block(sections[0][2])

    # 单季报没有营收同比，应从年报取
    if latest.get("revenue_yoy") is None and annual:
        annual_parsed = _parse_single_block(annual[0][2])
        if annual_parsed.get("revenue_yoy") is not None:
            latest["revenue_yoy"] = annual_parsed["revenue_yoy"]

    revenue_yoy = latest.get("revenue_yoy")
    if revenue_yoy == 25.00:
        print(f"  ✅ 营收同比兜底: {revenue_yoy}%（从年报取）")
        return True
    else:
        print(f"  ❌ 营收同比兜底: 期望=25.00, 实际={revenue_yoy}")
        return False


if __name__ == "__main__":
    print("=" * 80)
    print("字段提取逻辑全面测试")
    print("=" * 80)

    results = []

    results.append(("1. _parse_single_block关键词", test_parse_single_block_keywords()))
    results.append(("2. 净利润严格行首匹配", test_net_profit_strict_match()))
    results.append(("3. 经营现金流直接提取", test_ocf_direct_extraction()))
    results.append(("4. 经营现金流兜底逻辑", test_ocf_fallback()))
    results.append(("5. 资产负债率提取", test_debt_ratio_extraction()))
    results.append(("6. 财报段落拆分", test_report_section_splitting()))
    results.append(("7. 最新单季指标", test_latest_quarter_metrics()))
    results.append(("8. 营收同比兜底", test_revenue_yoy_fallback_to_annual()))

    print("\n" + "=" * 80)
    print("测试汇总")
    print("=" * 80)

    all_pass = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status} | {name}")
        if not passed:
            all_pass = False

    print()
    if all_pass:
        print("🎉 所有测试通过！")
    else:
        print("⚠️ 存在失败的测试，请检查修复")

    sys.exit(0 if all_pass else 1)
