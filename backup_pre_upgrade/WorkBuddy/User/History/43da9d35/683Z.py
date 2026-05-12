#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
搞清楚：用户期望的取值逻辑
用户说300189的正确值：营收同比59.18%、净利润同比444.78%
这两个值分别来自：
- 59.18%: 20251231 年报的"营业收入同比增长"
- 444.78%: 20251231 Q4单季报的"归母净利润同比增长"

但最新单季报(20260331 Q1)中没有营收同比增长字段！

所以正确的取值逻辑应该是：
- revenue_yoy: 优先从最新单季报取，如果没有则从最新年报取
- profit_yoy: 优先从最新单季报取，如果没有则从最新年报取

让我验证这个逻辑对其他股票是否也正确
"""
import os, sys, re

sys.path.insert(0, r'D:\Project\QAScorer')

import importlib
import qa_scorer
importlib.reload(qa_scorer)

from qa_scorer import run_neodata, load_token

token = load_token()

def extract_report_sections(text):
    if not text:
        return []
    pattern = r"根据.+?在A股市场\d+发布的财报数据[，,]\s*统计截止日期为(\d{4})(0331|0630|0930|1231)的(Q[1-4]单?季报|年报)"
    matches = list(re.finditer(pattern, text))
    if not matches:
        return []
    sections = []
    for i, m in enumerate(matches):
        report_date = f"{m.group(1)}{m.group(2)}"
        report_type = m.group(3)
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        section_text = text[start:end].strip()
        sections.append((report_date, report_type, section_text))
    sections.sort(key=lambda x: x[0], reverse=True)
    return sections


def parse_growth_from_section(section_text):
    rev_yoy = None
    prof_yoy = None
    for line in section_text.split("\n"):
        line = line.strip()
        if "营业收入同比增长" in line:
            m = re.search(r'营业收入同比增长\s*([-+]?\d+\.?\d*)%', line)
            if m:
                rev_yoy = float(m.group(1))
        if "归母净利润同比增长" in line:
            m = re.search(r'归母净利润同比增长\s*([-+]?\d+\.?\d*)%', line)
            if m:
                prof_yoy = float(m.group(1))
    return rev_yoy, prof_yoy


# 测试：对每只股票，列出所有段落中的营收同比和净利润同比
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
print("所有段落中的营收同比和净利润同比")
print("=" * 80)

for ts_code, name in test_stocks:
    query = f"{ts_code} {name} 最新季报"
    text = run_neodata(query, token)
    sections = extract_report_sections(text)

    print(f"\n{ts_code} {name} ({len(sections)}个段落):")

    # 收集所有单季报和年报的yoy
    all_quarterly = []  # [(date, rev_yoy, prof_yoy)]
    all_annual = []

    for report_date, report_type, section_text in sections:
        rev_yoy, prof_yoy = parse_growth_from_section(section_text)
        marker = ""
        if rev_yoy is not None or prof_yoy is not None:
            marker = " <-- 有数据"
        print(f"  {report_date} {report_type}: 营收同比={rev_yoy}, 净利润同比={prof_yoy}{marker}")

        if "季报" in report_type:
            all_quarterly.append((report_date, rev_yoy, prof_yoy))
        if "年报" in report_type:
            all_annual.append((report_date, rev_yoy, prof_yoy))

    # 按用户逻辑：最新单季报优先，没有则用年报
    # revenue_yoy: 最新单季报有就用，没有就用最新年报
    # profit_yoy: 最新单季报有就用，没有就用最新年报

    # 找最新单季报（有数据的）
    latest_q_rev = None
    latest_q_prof = None
    for date, rev, prof in all_quarterly:
        if latest_q_rev is None and rev is not None:
            latest_q_rev = rev
        if latest_q_prof is None and prof is not None:
            latest_q_prof = prof

    # 找最新年报（有数据的）
    latest_a_rev = None
    latest_a_prof = None
    for date, rev, prof in all_annual:
        if latest_a_rev is None and rev is not None:
            latest_a_rev = rev
        if latest_a_prof is None and prof is not None:
            latest_a_prof = prof

    # 最终取值
    final_rev_yoy = latest_q_rev if latest_q_rev is not None else latest_a_rev
    final_prof_yoy = latest_q_prof if latest_q_prof is not None else latest_a_prof

    print(f"  >>> 最终: 营收同比={final_rev_yoy}, 净利润同比={final_prof_yoy}")
