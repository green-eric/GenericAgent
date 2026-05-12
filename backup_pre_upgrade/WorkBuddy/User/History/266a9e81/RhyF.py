#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Simulate the parsing logic from stock_analyzer.py lines 448-458
def _parse_num_from_line(line):
    if not line:
        return None
    m = re.search(r'([-+]?\d+\.?\d*)\s*(万亿元|亿元|万元|千元|元)', line)
    if not m:
        return None
    num, unit = float(m.group(1)), m.group(2)
    if unit == '万亿元': return num * 1e12
    if unit == '亿元':   return num * 1e8
    if unit == '万元':   return num * 1e4
    if unit == '千元':   return num * 1e3
    return num

# Test lines from actual API response
test_lines = [
    "净利润1642130865.33元，",
    "净利润1197197445.8元，",
    "归母净利润1672149337.87元，",
    "扣非净利润1598214741.80元，",
]

print("=== Testing line matching ===")
for line in test_lines:
    matched = line.startswith('净利润') and '归母' not in line and '扣非' not in line
    print(f"Line: {line}")
    print(f"  startswith('净利润'): {line.startswith('净利润')}")
    print(f"  '归母' not in line: {'归母' not in line}")
    print(f"  '扣非' not in line: {'扣非' not in line}")
    print(f"  MATCH: {matched}")
    if matched:
        val = _parse_num_from_line(line)
        print(f"  Parsed value: {val}")
    print()

# Now test the full annual block extraction
print("=== Testing full block extraction ===")
annual_block = """
统计截止日期为20251231的年报，主要财务指标如下：
资产负债结构：资产负债率9.56%；
营业总收入40.40亿元，营业收入同比增长 154.80%；
归母净利润同比增长 472.62%；
净利润1642130865.33元，
归母净利润1672149337.87元，
扣非净利润1598214741.80元，
加权净资产收益率ROE 17.90%；
销售毛利率 66.13%，销售净利率 40.65%；
经营活动产生的现金流量净额 2634555758.47元；
总资产周转率 0.39次；
应收账款周转率 16.77次。
"""

# Test the parsing logic
line = None
for l in annual_block.split('\n'):
    l = l.strip()
    if l.startswith('净利润') and '归母' not in l and '扣非' not in l:
        line = l
        print(f"Matched line: {line}")
        break

if line:
    val = _parse_num_from_line(line)
    print(f"Parsed: {val}")
else:
    print("No matching line found!")
