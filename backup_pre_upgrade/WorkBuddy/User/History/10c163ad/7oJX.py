#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re

MOCK_NEODATA_RESPONSE = """
统计截止日期为20230331的季报
营业收入4182651234.56元
归母净利润同比增长12.34%

统计截止日期为20241231的年报
加权净资产收益率ROE15.67%
销售毛利率42.35%
销售净利率18.22%
营业收入同比增长28.45%
归母净利润同比增长35.67%
资产负债率38.92%
营业总收入18654321098.76元
净利润1642130865.33元
扣非净利润1523456789.01元
经营活动产生的现金流量净额2156789012.34元
净利润现金含量160.44%
净利润增长率25.80%
总资产周转率0.85次
应收账款周转率6.78次
经营现金流/净利润145.67%

统计截止日期为20240930的季报
营业收入1234567890.12元
归母净利润同比增长15.67%
"""

def _extract_annual_block(text, year=None):
    """精确提取年报段落，锚点：统计截止日期为YYYY1231的年报"""
    if year:
        target = f"统计截止日期为{year}1231的年报"
    else:
        matches = list(re.finditer(r"统计截止日期为(\d{4})1231的年报", text))
        if not matches:
            return ""
        last = matches[-1]
        target = last.group(0)
    start = text.find(target)
    if start == -1:
        return ""
    start += len(target)
    next_anchor = text.find("统计截止日期为", start + 1)
    if next_anchor == -1:
        block = text[start:]
    else:
        block = text[start:next_anchor]
    return block.strip()

def _extract_metric_line(block, keywords):
    """在年报段落内按关键词逐行搜索"""
    for line in block.split("\n"):
        line = line.strip()
        if not line:
            continue
        for kw in keywords:
            if kw in line:
                print(f"    [MATCH] '{kw}' found in line: '{line}'")
                return line
    print(f"    [NO_MATCH] No keyword from {keywords} found in any line")
    return None

block = _extract_annual_block(MOCK_NEODATA_RESPONSE)
print(f"Extracted block:\n{block}\n")

line = _extract_metric_line(block, ["营业总收入", "营业收入"])
if line:
    print(f"Found line: {line}")
else:
    print("No line found!")