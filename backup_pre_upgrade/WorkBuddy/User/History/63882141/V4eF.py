#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""步骤1：验证备用数据源字段准确性"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 强制重新加载模块
import importlib
import data_provider
importlib.reload(data_provider)

from data_provider import DataProvider, _westock_profile

print("=" * 60)
print("步骤1：验证备用数据源")
print("=" * 60)

# 测试 _westock_profile 函数
print("\n--- _westock_profile 函数测试 ---")
for code in ['600519', '000858', '002415']:
    result = _westock_profile(code)
    if result:
        print(f"  {code}: name={result.get('name')}, industry={result.get('industry')}")
    else:
        print(f"  {code}: FAILED (None)")

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
