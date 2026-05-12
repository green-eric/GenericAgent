#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
搞清楚每个字段的正确取值来源
核心问题：revenue_yoy和profit_yoy是否存在于最新单季报中？
"""
import os, sys, re

sys.path.insert(0, r'D:\Project\QAScorer')

import importlib
import qa_scorer
importlib.reload(qa_scorer)

from qa_scorer import run_neodata, load_token

token = load_token()

# 按"根据...发布的财报数据"拆分子段落
def extract_report_sections(text):
    if not text:
        return []
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
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        section_text = text[start:end].strip()
        sections.append((report_date, report_type, section_text))
    sections.sort(key=lambda x: x[0], reverse=True)
    return sections


# 测试多只股票，看最新单季报里到底有没有营收同比和净利润同比
test_stocks = [
    ("300189.SZ", "神农种业"),
    ("000001.SZ", "平安银行"),
    ("600519.SH", "贵州茅台"),
    ("300750.SZ", "宁德时代"),
    ("002594.SZ", "比亚迪"),
    ("600036.SH", "招商银行"),
    ("000858.SZ", "五粮液"),
    ("601318.SH", "中国平安"),
    ("000333.SZ", "美的集团"),
    ("002415.SZ", "海康威视"),
]

print("=" * 80)
print("检查每只股票最新单季报中的字段")
print("=" * 80)

for ts_code, name in test_stocks:
    query = f"{ts_code} {name} 最新季报"
    text = run_neodata(query, token)
    sections = extract_report_sections(text)

    if not sections:
        print(f"\n{ts_code} {name}: 无数据")
        continue

    # 最新段落
    latest_date, latest_type, latest_text = sections[0]

    # 检查最新段落中有哪些字段
    has_rev_yoy = "营业收入同比增长" in latest_text
    has_prof_yoy = "归母净利润同比增长" in latest_text
    has_revenue = "营业总收入" in latest_text or "营业收入" in latest_text
    has_net_profit = "归母净利润" in latest_text
    has_gross_margin = "销售毛利率" in latest_text
    has_net_margin = "销售净利率" in latest_text
    has_total_assets = "资产合计" in latest_text
    has_total_liab = "负债合计" in latest_text
    has_ocf = "经营活动产生的现金流量净额" in latest_text
    has_ocf_ratio = "净利润现金含量" in latest_text

    # 提取具体值
    rev_yoy_val = None
    prof_yoy_val = None
    for line in latest_text.split("\n"):
        if "营业收入同比增长" in line:
            m = re.search(r'营业收入同比增长\s*([-+]?\d+\.?\d*)%', line)
            if m:
                rev_yoy_val = m.group(1)
        if "归母净利润同比增长" in line:
            m = re.search(r'归母净利润同比增长\s*([-+]?\d+\.?\d*)%', line)
            if m:
                prof_yoy_val = m.group(1)

    print(f"\n{ts_code} {name} | 最新: {latest_date} {latest_type}")
    print(f"  营收同比: {'有=' + rev_yoy_val if has_rev_yoy else '无'} | 净利润同比: {'有=' + prof_yoy_val if has_prof_yoy else '无'}")
    print(f"  营收={has_revenue}, 净利润={has_net_profit}, 毛利率={has_gross_margin}, 净利率={has_net_margin}")
    print(f"  资产={has_total_assets}, 负债={has_total_liab}, OCF={has_ocf}, OCF比率={has_ocf_ratio}")

    # 如果是年报，也看看最新单季报
    quarterly_sections = [(d, t, txt) for d, t, txt in sections if "季报" in t]
    if quarterly_sections:
        q_date, q_type, q_text = quarterly_sections[0]
        q_has_rev = "营业收入同比增长" in q_text
        q_has_prof = "归母净利润同比增长" in q_text
        q_rev_val = None
        q_prof_val = None
        for line in q_text.split("\n"):
            if "营业收入同比增长" in line:
                m = re.search(r'营业收入同比增长\s*([-+]?\d+\.?\d*)%', line)
                if m:
                    q_rev_val = m.group(1)
            if "归母净利润同比增长" in line:
                m = re.search(r'归母净利润同比增长\s*([-+]?\d+\.?\d*)%', line)
                if m:
                    q_prof_val = m.group(1)
        print(f"  最新单季: {q_date} {q_type} | 营收同比: {'有=' + q_rev_val if q_has_rev else '无'} | 净利润同比: {'有=' + q_prof_val if q_has_prof else '无'}")
