#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, re

sys.path.insert(0, r'D:\Project\QAScorer')
from qa_scorer import run_neodata, load_token, _extract_all_quarterly_blocks

token = load_token()
text = run_neodata("300189.SZ 神农种业 最新季报", token)

# 搜索所有"统计截止日期"的出现
pattern_all = r"统计截止日期为(\d{4})(\d{4})"
matches_all = list(re.finditer(pattern_all, text))
print("=== All '统计截止日期为' occurrences ===")
for m in matches_all:
    start = max(0, m.start())
    end = min(len(text), m.end() + 30)
    print("  pos=" + str(m.start()) + " year=" + m.group(1) + " date=" + m.group(2))
    print("  context: ..." + text[start:end] + "...")

# 测试代码中的正则
pattern_code = r"统计截止日期为(\d{4})(0331|0630|0930)的季报"
matches_code = list(re.finditer(pattern_code, text))
print("\n=== Code regex matches ===")
print("Count: " + str(len(matches_code)))
for m in matches_code:
    print("  year=" + m.group(1) + " q=" + m.group(2))
    print("  matched text: " + text[m.start():m.end()])

# 测试宽松正则
pattern_loose = r"统计截止日期为(\d{4})(0331|0630|0930)"
matches_loose = list(re.finditer(pattern_loose, text))
print("\n=== Loose regex matches ===")
print("Count: " + str(len(matches_loose)))
for m in matches_loose:
    print("  year=" + m.group(1) + " q=" + m.group(2))
    print("  matched text: " + text[m.start():m.end()])
    print("  after match: " + text[m.end():m.end()+20])
