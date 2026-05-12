#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""步骤1：验证备用数据源字段准确性"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_provider import DataProvider, _westock_profile

print("=" * 60)
print("步骤1：验证备用数据源")
print("=" * 60)

# 测试 westock-data profile 原始输出
print("\n--- westock-data profile 原始输出 ---")
for code in ['sh600519', 'sz000858', 'sz002415']:
    result = _westock_profile(code.replace('sh','').replace('sz','').replace('bj',''))
    print(f"\n  {code}:")
    print(f"    name:     {result.get('name') if result else 'FAILED'}")
    print(f"    industry: {result.get('industry') if result else 'FAILED'}")

# 测试 DataProvider 接口
print("\n--- DataProvider 接口测试 ---")
for symbol in ['600519', '000858', '002415']:
    print(f"\n  [{symbol}]")
    name = DataProvider.get_stock_name(symbol)
    industry = DataProvider.get_industry(symbol)
    quote = DataProvider.get_stock_quote(symbol)
    is_st = DataProvider.is_st_stock(symbol)
    print(f"    名称:     {name}")
    print(f"    行业:     {industry}")
    print(f"    总市值(元): {quote['total_mv']:,.0f}")
    print(f"    总市值(亿): {quote['total_mv']/1e8:,.2f}")
    print(f"    PE-TTM:   {quote['pe_ttm']}")
    print(f"    ST:       {is_st}")

print("\n完成")
