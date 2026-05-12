#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, re

sys.path.insert(0, r'D:\Project\QAScorer')
from qa_scorer import run_neodata, load_token, _extract_all_quarterly_blocks, _parse_single_block

token = load_token()
text = run_neodata("300189.SZ 神农种业 最新季报", token)

# 看看_extract_all_quarterly_blocks返回什么
blocks = _extract_all_quarterly_blocks(text)
print("Number of blocks: " + str(len(blocks)))
for i, (year, q_date, block) in enumerate(blocks):
    print("\n=== Block " + str(i) + " (year=" + year + ", q=" + q_date + ") ===")
    print("Block text length: " + str(len(block)))
    print("First 300 chars:")
    print(block[:300])
    
    # 解析
    parsed = _parse_single_block(block)
    print("\nParsed:")
    for k, v in parsed.items():
        if v is not None:
            print("  " + k + "=" + str(v))
