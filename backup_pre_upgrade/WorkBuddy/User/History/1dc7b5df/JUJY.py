#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""逻辑单元测试 - 验证核心函数边界条件"""

import sys, os

def eprint(*args, **kwargs):
    kwargs['file'] = sys.stderr
    print(*args, **kwargs)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from quarterly_scorer import (
    parse_num, _extract_quarterly_block, _extract_annual_block,
    parse_quarterly_finance, calc_completeness, percentile_rank,
    calc_quarterly_score, calc_annual_score, Config, CORE_METRICS
)

passed = 0
failed = 0

def check(label, cond):
    global passed, failed
    if cond:
        eprint(f"[PASS] {label}")
        passed += 1
    else:
        eprint(f"[FAIL] {label}")
        failed += 1

# ===== parse_num =====
eprint("=" * 60)
eprint("parse_num 边界测试")
eprint("=" * 60)
check("None输入", parse_num(None) is None)
check("空字符串", parse_num("") is None)
check("纯文本", parse_num("N/A") is None)
check("百分比", parse_num("45.23%") == 45.23)
check("负数百分比", parse_num("-12.5%") == -12.5)
check("整数", parse_num("125") == 125.0)
check("小数", parse_num("3.14") == 3.14)
check("负小数", parse_num("-0.5") == -0.5)
check("带单位", parse_num("12500000000.00") == 12500000000.0)
check("混合文本", parse_num("同比增长18.67%") == 18.67)

# ===== _extract_quarterly_block =====
eprint("")
eprint("=" * 60)
eprint("_extract_quarterly_block 边界测试")
eprint("=" * 60)

MOCK_MULTI = """
统计截止日期为20260331的Q1单季报
销售毛利率45.23%
销售净利率22.15%
归母净利润同比增长18.67%

统计截止日期为20251231的年报
加权净资产收益率ROE18.52%
销售毛利率43.21%

统计截止日期为20250930的Q3单季报
销售毛利率44.10%
营业收入同比增长22.80%
"""

block, date = _extract_quarterly_block(MOCK_MULTI)
check("最新季度日期=20260331", date == "20260331")
check("最新季度含45.23", "45.23" in block)
check("最新季度不含ROE", "ROE" not in block)
check("最新季度不含资产负债率", "资产负债率" not in block)

block2, date2 = _extract_quarterly_block("")
check("空文本返回空", block2 == "" and date2 == "")

block3, date3 = _extract_quarterly_block("统计截止日期为20251231的年报\nROE15%")
check("只有年报时返回空", block3 == "" and date3 == "")

block4, date4 = _extract_quarterly_block("统计截止日期为20250930的Q3单季报\n销售毛利率40%")
check("只有Q3时正确提取", date4 == "20250930" and "40" in block4)

# ===== parse_quarterly_finance =====
eprint("")
eprint("=" * 60)
eprint("parse_quarterly_finance 边界测试")
eprint("=" * 60)
qm = parse_quarterly_finance(block)
check("毛利率=45.23", qm.get("gross_margin") == 45.23)
check("净利率=22.15", qm.get("net_margin") == 22.15)
check("利润同比=18.67", qm.get("profit_yoy") == 18.67)
check("营收同比=None(Q1)", qm.get("revenue_yoy") is None)

# ===== _extract_annual_block =====
eprint("")
eprint("=" * 60)
eprint("_extract_annual_block 边界测试")
eprint("=" * 60)
ab = _extract_annual_block(MOCK_MULTI)
check("年报段落含ROE", "ROE18.52" in ab)
check("年报段落不含Q1", "Q1" not in ab)

# ===== percentile_rank =====
eprint("")
eprint("=" * 60)
eprint("percentile_rank 边界测试")
eprint("=" * 60)
check("空列表返回50", percentile_rank(10, []) == 50.0)
check("单元素返回50", percentile_rank(10, [5]) == 50.0)
check("最大值=100", percentile_rank(100, [10, 20, 30, 100]) == 100.0)
check("最小值=0", percentile_rank(10, [10, 20, 30, 100]) == 0.0)
check("中间值", percentile_rank(20, [10, 20, 30]) == 50.0)
check("逆序-最小变最大", percentile_rank(10, [100, 50, 10], reverse=True) == 100.0)

# ===== calc_completeness =====
eprint("")
eprint("=" * 60)
eprint("calc_completeness 边界测试")
eprint("=" * 60)
all_present = {m: 1.0 for m in CORE_METRICS}
r, l = calc_completeness(all_present)
check("全部存在=high", l == "high" and r == 1.0)

half = {"roe": 1.0, "gross_margin": 2.0, "net_margin": 3.0, "revenue_yoy": None,
        "profit_yoy": None, "ocf_to_profit": None, "debt_ratio": None}
r2, l2 = calc_completeness(half)
check("3/7=medium", l2 == "medium")

one = {"roe": 1.0, "gross_margin": None, "net_margin": None, "revenue_yoy": None,
       "profit_yoy": None, "ocf_to_profit": None, "debt_ratio": None}
r3, l3 = calc_completeness(one)
check("1/7=ultra_low", l3 == "ultra_low")

none_dict = {m: None for m in CORE_METRICS}
r4, l4 = calc_completeness(none_dict)
check("0/7=ultra_low", l4 == "ultra_low")

# ===== 评分集成测试 =====
eprint("")
eprint("=" * 60)
eprint("评分集成测试")
eprint("=" * 60)

stocks = [
    {"ts_code": "000001.SZ", "name": "测试1", "industry_l1": "银行",
     "roe": 15.0, "gross_margin": 50.0, "net_margin": 30.0,
     "revenue_yoy": 10.0, "profit_yoy": 15.0, "debt_ratio": 40.0,
     "ocf_to_profit": 120.0, "net_profit": 1e9, "ocf_abs": 1e9,
     "fetch_success": True, "annual_report_date": "20251231"},
    {"ts_code": "000002.SZ", "name": "测试2", "industry_l1": "银行",
     "roe": 10.0, "gross_margin": 40.0, "net_margin": 20.0,
     "revenue_yoy": 5.0, "profit_yoy": 8.0, "debt_ratio": 50.0,
     "ocf_to_profit": 100.0, "net_profit": 5e8, "ocf_abs": 5e8,
     "fetch_success": True, "annual_report_date": "20251231"},
    {"ts_code": "000003.SZ", "name": "测试3", "industry_l1": "银行",
     "roe": 5.0, "gross_margin": 30.0, "net_margin": 10.0,
     "revenue_yoy": -5.0, "profit_yoy": -10.0, "debt_ratio": 60.0,
     "ocf_to_profit": 80.0, "net_profit": 1e8, "ocf_abs": 1e8,
     "fetch_success": True, "annual_report_date": "20251231"},
]

ig = {"银行": stocks}
all_s = stocks

s1 = calc_annual_score(stocks[0], ig, all_s)
check("年报评分-高分股票有分数", s1["total_score"] > 0)
check("年报评分-ROE高的分高", s1["profit_score"] > 0)

neg_stock = {
    "ts_code": "000004.SZ", "name": "负ROE测试", "industry_l1": "银行",
    "roe": -5.0, "gross_margin": 30.0, "net_margin": 10.0,
    "revenue_yoy": -5.0, "profit_yoy": -10.0, "debt_ratio": 60.0,
    "ocf_to_profit": 80.0, "net_profit": -1e8, "ocf_abs": -1e8,
    "fetch_success": True, "annual_report_date": "20251231"
}
s_neg = calc_annual_score(neg_stock, ig, all_s)
check("负ROE的profit_score有值(其他指标非零)", s_neg["profit_score"] >= 0.0)
check("负利润+负OCF有上限", s_neg["total_score"] <= Config.NEG_PROF_PENALTY)

qm_test = {"gross_margin": 55.0, "net_margin": 35.0, "revenue_yoy": 12.0, "profit_yoy": 20.0}
sq = calc_quarterly_score(stocks[0], qm_test, ig, all_s, "20260331")
check("季度评分有分数", sq["total_score"] > 0)
check("季度日期正确", sq["quarterly_report_date"] == "20260331")

sq_empty = calc_quarterly_score(stocks[0], {}, ig, all_s, "")
check("空季度指标仍可用年报数据评分", sq_empty["total_score"] > 0)

small_ig = {"小众": stocks[:2]}
s_fallback = calc_annual_score(stocks[0], small_ig, all_s)
check("小行业触发fallback", s_fallback["market_fallback"] == True)

eprint("")
eprint("=" * 60)
eprint(f"测试结果: {passed} 通过, {failed} 失败")
eprint("=" * 60)
if failed > 0:
    raise SystemExit(1)
