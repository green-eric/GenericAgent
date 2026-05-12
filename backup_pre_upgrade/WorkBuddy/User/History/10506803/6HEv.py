# -*- coding: utf-8 -*-
MOCK_RESPONSE = """
统计截止日期为20260331的Q1单季报
销售毛利率45.23%
销售净利率22.15%
归母净利润同比增长18.67%

统计截止日期为20251231的年报
加权净资产收益率ROE18.52%
销售毛利率43.21%
销售净利率20.88%
营业收入同比增长25.30%
归母净利润同比增长32.15%
资产负债率35.60%
营业总收入12500000000.00元
净利润2560000000.00元
扣非净利润2380000000.00元
经营活动产生的现金流量净额2890000000.00元
净利润现金含量112.89%
总资产周转率0.92次
应收账款周转率7.45次

统计截止日期为20250930的Q3单季报
销售毛利率44.10%
销售净利率21.50%
营业收入同比增长22.80%
归母净利润同比增长28.90%
"""

import re

def _extract_quarterly_block(text):
    # 匹配格式：统计截止日期为YYYYMMDD的Q1单季报/Q3单季报
    pattern = r"统计截止日期为(\d{4}(?:0331|0630|0930))的Q[123]单季报"
    matches = list(re.finditer(pattern, text))

    if not matches:
        # 兜底：匹配任何季度段落（排除年报）
        pattern2 = r"统计截止日期为(\d{4}(?:0331|0630|0930))的(?:单?季报)"
        matches = list(re.finditer(pattern2, text))
        # 过滤掉年报（1231）
        matches = [m for m in matches if m.group(1) != "20251231"]

    if not matches:
        return "", ""

    # 取最新的季度（按日期倒序，取第一个）
    latest = sorted(matches, key=lambda x: x.group(1), reverse=True)[0]
    report_date = latest.group(1)
    anchor = "统计截止日期为" + report_date + "的"
    start = text.find(anchor) + len(anchor)
    # 跳过可能的 "Q1单季报"/"Q3单季报" 标识
    q_prefix = ["Q1单季报", "Q2单季报", "Q3单季报"]
    for p in q_prefix:
        if text[start:start+len(p)] == p:
            start += len(p)
            break
    next_a = text.find("统计截止日期为", start + 1)
    block = text[start:] if next_a == -1 else text[start:next_a]
    return block.strip(), report_date

block, date = _extract_quarterly_block(MOCK_RESPONSE)
print(f"Date: {date}")
print(f"Block length: {len(block)}")
print(f"Block: {repr(block)}")

# 解析测试
import re as regex

def parse_num(text):
    if not text: return None
    m = regex.search(r"([-+]?\d+\.?\d*)%", text)
    if m: return float(m.group(1))
    m = regex.search(r"([-+]?\d+\.?\d*)", text)
    if m: return float(m.group(1))
    return None

def _extract_metric_line(block, keywords):
    for line in block.split("\n"):
        line = line.strip()
        if not line: continue
        for kw in keywords:
            if kw in line: return line
    return None

def parse_quarterly_finance(block):
    r = {}
    line = _extract_metric_line(block, ["销售毛利率"])
    r["gross_margin"] = parse_num(line[line.find("毛利率"):]) if line and "毛利率" in line else None
    line = _extract_metric_line(block, ["销售净利率"])
    r["net_margin"] = parse_num(line[line.find("净利率"):]) if line and "净利率" in line else None
    line = _extract_metric_line(block, ["营业收入同比增长", "营收同比增长", "营业总收入同比增长"])
    r["revenue_yoy"] = parse_num(line) if line else None
    line = _extract_metric_line(block, ["归母净利润同比增长"])
    r["profit_yoy"] = parse_num(line) if line else None
    return r

qm = parse_quarterly_finance(block)
print(f"\nParsed metrics: {qm}")