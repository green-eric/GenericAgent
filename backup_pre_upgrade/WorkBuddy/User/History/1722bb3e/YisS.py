#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, re

sys.path.insert(0, r'D:\Project\QAScorer')
from qa_scorer import run_neodata, load_token, _extract_all_quarterly_blocks, _parse_single_block, _parse_num_from_line

token = load_token()
text = run_neodata("300189.SZ 神农种业 最新季报", token)
blocks = _extract_all_quarterly_blocks(text)

year, q_date, block = blocks[0]
print("=== Block 0 full text ===")
print(block)
print("\n=== Searching for '营业总收入' in block ===")
for i, line in enumerate(block.split('\n')):
    if '营业总收入' in line or '营业收入' in line:
        print("Line " + str(i) + ": " + line.strip())
        val = _parse_num_from_line(line)
        print("  Parsed value: " + str(val))
