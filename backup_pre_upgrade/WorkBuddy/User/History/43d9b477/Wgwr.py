#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重新分析API返回的完整结构
搞清楚：
1. 最外层的"统计截止日期"锚点到底有几个
2. 每个锚点内的子段落结构
3. 营收同比和净利润同比的正确来源
"""
import os, sys, re

sys.path.insert(0, r'D:\Project\QAScorer')

import importlib
import qa_scorer
importlib.reload(qa_scorer)

from qa_scorer import run_neodata, load_token

token = load_token()

ts_code, name = "300189.SZ", "神农种业"
query = f"{ts_code} {name} 最新季报"
text = run_neodata(query, token)

# 打印完整文本，看清楚结构
print("=" * 80)
print("完整API返回文本")
print("=" * 80)
print(text)

print("\n\n" + "=" * 80)
print("分析：找出所有'营业收入同比增长'和'归母净利润同比增长'的位置")
print("=" * 80)

for m in re.finditer(r'营业收入同比增长\s*([-+]?\d+\.?\d*)%', text):
    # 往前找最近的"统计截止日期"锚点
    before_text = text[:m.start()]
    anchor_match = None
    for am in re.finditer(r'统计截止日期为(\d{4})(0331|0630|0930|1231)的(?:Q[1-4]单?)?(?:季?年报?)', before_text):
        anchor_match = am
    # 往前找最近的"根据...发布的财报数据"
    pub_match = None
    for pm in re.finditer(r'根据.+?在A股市场(\d+)发布的财报数据', before_text):
        pub_match = pm

    context_start = max(0, m.start() - 200)
    context = text[context_start:m.end()].replace('\n', ' ')

    print(f"\n  营收同比 {m.group(1)}% @ pos={m.start()}")
    if anchor_match:
        print(f"    最近锚点: {anchor_match.group()}")
    if pub_match:
        print(f"    发布日期: {pub_match.group(1)}")
    print(f"    上下文: ...{context}...")

print()
for m in re.finditer(r'归母净利润同比增长\s*([-+]?\d+\.?\d*)%', text):
    before_text = text[:m.start()]
    anchor_match = None
    for am in re.finditer(r'统计截止日期为(\d{4})(0331|0630|0930|1231)的(?:Q[1-4]单?)?(?:季?年报?)', before_text):
        anchor_match = am
    pub_match = None
    for pm in re.finditer(r'根据.+?在A股市场(\d+)发布的财报数据', before_text):
        pub_match = pm

    context_start = max(0, m.start() - 200)
    context = text[context_start:m.end()].replace('\n', ' ')

    print(f"\n  归母净利润同比 {m.group(1)}% @ pos={m.start()}")
    if anchor_match:
        print(f"    最近锚点: {anchor_match.group()}")
    if pub_match:
        print(f"    发布日期: {pub_match.group(1)}")
    print(f"    上下文: ...{context}...")
