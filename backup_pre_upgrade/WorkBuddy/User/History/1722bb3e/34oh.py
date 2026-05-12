#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, re

sys.path.insert(0, r'D:\Project\QAScorer')
from qa_scorer import run_neodata, load_token, _extract_all_quarterly_blocks, _parse_single_block

token = load_token()
text = run_neodata("300189.SZ 神农种业 最新季报", token)

blocks = _extract_all_quarterly_blocks(text)

# 打印Block 0的完整文本
year, q_date, block = blocks[0]
print("=== Block 0 (year=" + year + ", q=" + q_date + ") ===")
print("Full text:")
print(block)
print("\n=== Parsed ===")
parsed = _parse_single_block(block)
for k, v in parsed.items():
    if v is not None:
        print("  " + k + "=" + str(v))
