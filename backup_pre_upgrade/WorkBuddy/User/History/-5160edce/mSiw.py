#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re

def _parse_num_from_line(line):
    """从财报行提取带单位数值，单位匹配顺序：万亿元>亿元>万元>千元>元"""
    m = re.search(r'([-+]?\d+\.?\d*)\s*(万亿元|亿元|万元|千元|元)', line)
    if not m:
        return None
    val = float(m.group(1))
    unit = m.group(2)
    if unit == "万亿元": return val * 1e12
    elif unit == "亿元": return val * 1e8
    elif unit == "万元": return val * 1e4
    elif unit == "千元": return val * 1e3
    else: return val

# 测试 mock 数据中的 revenue 行
test_lines = [
    "营业总收入18654321098.76元",
    "营业收入18654321098.76元",
    "主营收入18654321098.76元",
]

for line in test_lines:
    result = _parse_num_from_line(line)
    print(f"{line} -> {result}")