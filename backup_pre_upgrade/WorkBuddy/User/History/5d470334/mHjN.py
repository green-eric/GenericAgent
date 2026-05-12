#!/usr/bin/env python3
"""查看NeoData API返回的原始数据结构"""
import os, json, sys
sys.path.insert(0, r"D:\Project\QAScorer")

from qa_scorer import load_token, run_neodata

token = load_token()

# 测试1: 简单查询
print("=" * 80)
print("测试1: 查询600519茅台最新季报")
print("=" * 80)
text = run_neodata("600519.SH 贵州茅台 最新季报", token)
print(f"返回类型: {type(text)}")
print(f"返回长度: {len(text)}")
print(f"前2000字符:\n{text[:2000]}")

# 测试2: 查询三大报表
print("\n" + "=" * 80)
print("测试2: 查询600519三大报表结构化数据")
print("=" * 80)
text2 = run_neodata("600519.SH 贵州茅台 利润表 资产负债表 现金流量表 最近4个季度", token)
print(f"返回长度: {len(text2)}")
print(f"前2000字符:\n{text2[:2000]}")

# 测试3: 查询结构化JSON格式
print("\n" + "=" * 80)
print("测试3: 查询600519财报数据JSON格式")
print("=" * 80)
text3 = run_neodata("600519 贵州茅台 财报数据 营业收入 净利润 资产负债 现金流量", token)
print(f"返回长度: {len(text3)}")
print(f"前2000字符:\n{text3[:2000]}")
