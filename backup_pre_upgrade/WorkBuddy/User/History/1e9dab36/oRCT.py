MOCK_RESPONSE = """
统计截止日期为20260331的Q1单季报
销售毛利率45.23%
销售净利率22.15%
归母净利润同比增长18.67%
营业总收入3250000000.00元

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
    # 先找 Q1/Q2/Q3 单季报（排除年报）
    pattern = r"统计截止日期为(\d{4}(?:0331|0630|0930))的(Q[123]|单季报)"
    matches = list(re.finditer(pattern, text))
    print(f"Pattern 1 matches: {len(matches)}")
    for i, m in enumerate(matches):
        print(f"  Match {i}: '{m.group(0)}', date={m.group(1)}, type={m.group(2)}")

    if not matches:
        # 再尝试宽松匹配（允许没有 Q 前缀）
        pattern2 = r"统计截止日期为(\d{4}(?:0331|0630|0930))的(?:单?季报)"
        matches = list(re.finditer(pattern2, text))
        print(f"Pattern 2 matches: {len(matches)}")
        for i, m in enumerate(matches):
            print(f"  Match {i}: '{m.group(0)}', date={m.group(1)}")

    if not matches:
        return "", ""

    last = matches[-1]
    report_date = last.group(1)
    start = last.end()
    next_a = text.find("统计截止日期为", start + 1)
    block = text[start:] if next_a == -1 else text[start:next_a]
    return block.strip(), report_date

block, date = _extract_quarterly_block(MOCK_RESPONSE)
print(f"\nExtracted block:\n{repr(block[:200])}")
print(f"Report date: {date}")