#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""步骤1：验证备用数据源字段准确性"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_provider import DataProvider, _westock_profile
import subprocess

print("=" * 60)
print("步骤1：验证备用数据源")
print("=" * 60)

# 先直接测试 subprocess 调用
print("\n--- 直接 subprocess 测试 ---")
r = subprocess.run(
    'npx --yes westock-data-skillhub@latest profile sh600519',
    shell=True, capture_output=True, text=True, encoding='utf-8', timeout=60
)
output = r.stdout + r.stderr
# 过滤掉 CLIXML 和 PowerShell 噪音行
clean_lines = []
for line in output.split('\n'):
    stripped = line.strip()
    if stripped.startswith('|'):
        clean_lines.append(stripped)
print(f"  表格行数: {len(clean_lines)}")
for l in clean_lines[:3]:
    print(f"  {l}")

# 测试 _westock_profile 函数（传入纯数字代码）
print("\n--- _westock_profile 函数测试 ---")
for code in ['600519', '000858', '002415']:
    result = _westock_profile(code)
    print(f"  {code}: {result}")

# 测试 DataProvider 接口
print("\n--- DataProvider 接口测试 ---")
for symbol in ['600519', '000858']:
    print(f"\n  [{symbol}]")
    name = DataProvider.get_stock_name(symbol)
    industry = DataProvider.get_industry(symbol)
    quote = DataProvider.get_stock_quote(symbol)
    print(f"    名称:     {name}")
    print(f"    行业:     {industry}")
    print(f"    总市值(元): {quote['total_mv']:,.0f}")
    print(f"    PE-TTM:   {quote['pe_ttm']}")

print("\n完成")
