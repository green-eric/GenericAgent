#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试新的提取逻辑：按"根据...发布的财报数据"拆分子段落
"""
import os, sys, re

sys.path.insert(0, r'D:\Project\QAScorer')

import importlib
import qa_scorer
importlib.reload(qa_scorer)

from qa_scorer import run_neodata, load_token

token = load_token()

# 新的提取逻辑
def extract_report_sections(text):
    """
    从API返回中提取所有独立的财报子段落
    每个子段落格式: "根据...在A股市场YYYYMMDD发布的财报数据，统计截止日期为YYYYMMDD的Qx单季报/年报"
    返回: [(report_date, report_type, section_text), ...] 按时间降序
    """
    if not text:
        return []

    # 匹配每个子段落的起始: "根据...发布的财报数据，统计截止日期为YYYYMMDD的Qx单季报/年报"
    pattern = r"根据.+?在A股市场\d+发布的财报数据[，,]\s*统计截止日期为(\d{4})(0331|0630|0930|1231)的(Q[1-4]单?季报|年报)"
    matches = list(re.finditer(pattern, text))

    if not matches:
        return []

    sections = []
    for i, m in enumerate(matches):
        year = m.group(1)
        q_date = m.group(2)
        report_type = m.group(3)
        report_date = f"{year}{q_date}"

        # 从当前匹配的结束位置开始，到下一个匹配的开始位置
        start = m.end()
        if i + 1 < len(matches):
            end = matches[i + 1].start()
        else:
            end = len(text)
        section_text = text[start:end].strip()
        sections.append((report_date, report_type, section_text))

    # 按时间降序排列
    sections.sort(key=lambda x: x[0], reverse=True)
    return sections


def parse_section_growth(section_text):
    """从单个子段落中提取营收同比和净利润同比"""
    revenue_yoy = None
    profit_yoy = None

    for line in section_text.split("\n"):
        line = line.strip()
        if not line:
            continue

        # 营业收入同比增长
        if "营业收入同比增长" in line:
            m = re.search(r'营业收入同比增长\s*([-+]?\d+\.?\d*)%', line)
            if m:
                revenue_yoy = float(m.group(1))

        # 归母净利润同比增长
        if "归母净利润同比增长" in line:
            m = re.search(r'归母净利润同比增长\s*([-+]?\d+\.?\d*)%', line)
            if m:
                profit_yoy = float(m.group(1))

    return revenue_yoy, profit_yoy


# 测试多只股票
test_stocks = [
    ("300189.SZ", "神农种业", "59.18", "444.78"),   # 预期值
    ("000001.SZ", "平安银行", None, None),
    ("600519.SH", "贵州茅台", None, None),
    ("300750.SZ", "宁德时代", None, None),
    ("002594.SZ", "比亚迪", None, None),
]

print("=" * 80)
print("新提取逻辑测试")
print("=" * 80)

for ts_code, name, expected_rev, expected_prof in test_stocks:
    print(f"\n{'='*60}")
    print(f"股票: {ts_code} {name}")
    if expected_rev:
        print(f"预期: 营收同比={expected_rev}%, 净利润同比={expected_prof}%")
    print(f"{'='*60}")

    query = f"{ts_code} {name} 最新季报"
    text = run_neodata(query, token)
    sections = extract_report_sections(text)

    print(f"  子段落数: {len(sections)}")

    # 打印所有子段落的类型和同比增长
    for i, (report_date, report_type, section_text) in enumerate(sections):
        rev_yoy, prof_yoy = parse_section_growth(section_text)
        print(f"  段落{i}: {report_date} {report_type} → 营收同比={rev_yoy}, 净利润同比={prof_yoy}")

    # 取最新年报的营收同比 + 最新单季的净利润同比
    # 策略：
    # - revenue_yoy: 取最新的"年报"段落的营收同比
    # - profit_yoy: 取最新的"Q1/Q2/Q3/Q4单季报"段落的净利润同比
    #   如果没有单季报，取年报的

    latest_annual_rev_yoy = None
    latest_quarterly_prof_yoy = None
    latest_any_prof_yoy = None

    for report_date, report_type, section_text in sections:
        rev_yoy, prof_yoy = parse_section_growth(section_text)

        if latest_any_prof_yoy is None and prof_yoy is not None:
            latest_any_prof_yoy = prof_yoy

        if "年报" in report_type and latest_annual_rev_yoy is None and rev_yoy is not None:
            latest_annual_rev_yoy = rev_yoy

        if "季报" in report_type and latest_quarterly_prof_yoy is None and prof_yoy is not None:
            latest_quarterly_prof_yoy = prof_yoy

    print(f"\n  >>> 提取结果:")
    print(f"  >>> 营收同比(最新年报): {latest_annual_rev_yoy}")
    print(f"  >>> 净利润同比(最新季报): {latest_quarterly_prof_yoy}")
    print(f"  >>> 净利润同比(最新任意): {latest_any_prof_yoy}")

    if expected_rev:
        match_rev = "✓" if str(latest_annual_rev_yoy) == expected_rev else "✗"
        match_prof = "✓" if str(latest_quarterly_prof_yoy) == expected_prof else "✗"
        print(f"  >>> 验证: 营收同比{match_rev} 净利润同比{match_prof}")
