#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析API返回的block内部结构：
每个"年报"block内实际上包含多个子段落（年报+Q4+Q3+Q2）
需要搞清楚如何正确提取
"""
import os, sys, re

sys.path.insert(0, r'D:\Project\QAScorer')

import importlib
import qa_scorer
importlib.reload(qa_scorer)

from qa_scorer import run_neodata, load_token, _extract_all_quarterly_blocks

token = load_token()

# 分析300189的完整block 0结构
ts_code, name = "300189.SZ", "神农种业"
query = f"{ts_code} {name} 最新季报"
text = run_neodata(query, token)

# 手动提取block 0的完整内容
pattern = r"统计截止日期为(\d{4})(0331|0630|0930|1231)的(?:Q[1-4]单?)?(?:季?年报?)"
matches = list(re.finditer(pattern, text))

print(f"总锚点数: {len(matches)}")
for i, m in enumerate(matches):
    print(f"  锚点{i}: '{m.group()}' @ pos={m.start()}")
    # 打印锚点后的200字符
    snippet = text[m.start():m.start()+200].replace('\n', ' ')
    print(f"    内容: {snippet}...")

# block 0 的完整文本
block0_text = text[matches[0].end():matches[1].start()].strip()

# 在block 0内找所有"根据...发布的财报数据"子段落
sub_pattern = r"根据.+?在A股市场\d+发布的财报数据[，,]"
sub_matches = list(re.finditer(sub_pattern, block0_text))
print(f"\nBlock 0 内子段落数: {len(sub_matches)}")
for i, m in enumerate(sub_matches):
    print(f"  子段落{i}: '{m.group()}' @ pos={m.start()}")
    # 提取该子段落中的同比增长
    end_pos = sub_matches[i+1].start() if i+1 < len(sub_matches) else len(block0_text)
    sub_text = block0_text[m.start():end_pos]
    for line in sub_text.split('\n'):
        if '同比' in line and ('营业收入' in line or '归母净利润' in line):
            print(f"    >> {line.strip()}")

# 现在看看正确的提取方式：
# 对于"统计截止日期为20251231的年报"段落，营收同比是59.18%
# 对于"统计截止日期为20251231的Q4单季报"段落，归母净利润同比是444.78%
# 这两个值在同一个block的不同子段落中

print("\n\n" + "="*80)
print("测试：用子段落拆分后提取")
print("="*80)

# 在block内按"根据...发布的财报数据"拆分子段落
def split_block_subparagraphs(block_text):
    """将block拆分为子段落，每个子段落是一次财报发布"""
    sub_pattern = r"(根据.+?在A股市场\d+发布的财报数据[，,])"
    parts = re.split(sub_pattern, block_text)
    # parts[0]是第一个锚点后的前言，parts[1:]是交替的[标题, 内容]对
    sub_paras = []
    for i in range(1, len(parts), 2):
        header = parts[i] if i < len(parts) else ""
        content = parts[i+1] if i+1 < len(parts) else ""
        sub_paras.append((header, content))
    return sub_paras

sub_paras = split_block_subparagraphs(block0_text)
print(f"子段落数: {len(sub_paras)}")
for i, (header, content) in enumerate(sub_paras):
    print(f"\n--- 子段落{i} ---")
    print(f"  标题: {header.strip()[:80]}")
    # 提取营收同比和净利润同比
    rev_yoy = None
    prof_yoy = None
    for line in content.split('\n'):
        if '营业收入同比增长' in line:
            m = re.search(r'营业收入同比增长\s*([-+]?\d+\.?\d*)%', line)
            if m:
                rev_yoy = float(m.group(1))
        if '归母净利润同比增长' in line:
            m = re.search(r'归母净利润同比增长\s*([-+]?\d+\.?\d*)%', line)
            if m:
                prof_yoy = float(m.group(1))
    print(f"  营收同比={rev_yoy}, 归母净利润同比={prof_yoy}")

# 用其他股票验证这个模式
print("\n\n" + "="*80)
print("验证其他股票")
print("="*80)

for ts_code, name in [("000001.SZ", "平安银行"), ("600519.SH", "贵州茅台"), ("300750.SZ", "宁德时代")]:
    print(f"\n{ts_code} {name}:")
    query = f"{ts_code} {name} 最新季报"
    text = run_neodata(query, token)
    blocks = _extract_all_quarterly_blocks(text)
    if blocks:
        sub_paras = split_block_subparagraphs(blocks[0][2])
        for i, (header, content) in enumerate(sub_paras):
            rev_yoy = None
            prof_yoy = None
            for line in content.split('\n'):
                if '营业收入同比增长' in line:
                    m = re.search(r'营业收入同比增长\s*([-+]?\d+\.?\d*)%', line)
                    if m:
                        rev_yoy = float(m.group(1))
                if '归母净利润同比增长' in line:
                    m = re.search(r'归母净利润同比增长\s*([-+]?\d+\.?\d*)%', line)
                    if m:
                        prof_yoy = float(m.group(1))
            # 只打印有值的
            if rev_yoy is not None or prof_yoy is not None:
                header_short = header.strip()[:60]
                print(f"  子段落{i}: {header_short}... → 营收同比={rev_yoy}, 净利润同比={prof_yoy}")
