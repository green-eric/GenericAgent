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
    print(f"DEBUG: Input text length: {len(text)}")
    print(f"First 200 chars: {repr(text[:200])}")

    # 匹配格式：统计截止日期为YYYYMMDD的Q1单季报/Q3单季报
    pattern = r"统计截止日期为(\d{4}(?:0331|0630|0930))的Q[123]单季报"
    matches = list(re.finditer(pattern, text))
    print(f"Pattern matches: {len(matches)}")
    for i, m in enumerate(matches):
        print(f"  Match {i}: '{m.group(0)}', date={m.group(1)}, pos={m.start()}-{m.end()}")

    if not matches:
        # 兜底：匹配任何季度段落（排除年报）
        pattern2 = r"统计截止日期为(\d{4}(?:0331|0630|0930))的(?:单?季报)"
        matches = list(re.finditer(pattern2, text))
        print(f"Pattern2 matches: {len(matches)}")
        for i, m in enumerate(matches):
            print(f"  Match {i}: '{m.group(0)}', date={m.group(1)}, pos={m.start()}-{m.end()}")
        # 过滤掉年报（1231）
        matches = [m for m in matches if m.group(1) != "20251231"]

    if not matches:
        print("No quarterly matches found!")
        return "", ""

    # 取最新的季度（按日期倒序，取第一个）
    latest = sorted(matches, key=lambda x: x.group(1), reverse=True)[0]
    report_date = latest.group(1)
    anchor = "统计截止日期为" + report_date + "的"
    print(f"Anchor: '{anchor}'")
    start = text.find(anchor) + len(anchor)
    print(f"Start at: {start}")
    next_a = text.find("统计截止日期为", start + 1)
    block = text[start:] if next_a == -1 else text[start:next_a]
    print(f"Next anchor at: {next_a}")
    print(f"Block length: {len(block)}")
    print(f"Block first 100: {repr(block[:100])}")
    return block.strip(), report_date

block, date = _extract_quarterly_block(MOCK_RESPONSE)
print(f"\nFinal result:")
print(f"Date: {date}")
print(f"Block: {repr(block)}")