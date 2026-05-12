#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""步骤1：验证所有备用数据源字段准确性"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ['PYTHONIOENCODING'] = 'utf-8'

import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from data_provider import DataProvider, _westock_profile, _neodata_query

print("=" * 60)
print("步骤1：验证备用数据源")
print("=" * 60)

# 1. 测试 westock-data profile
print("\n[1] westock-data profile (名称/行业)")
for code in ['600519', '000858']:
    result = _westock_profile(code)
    if result:
        print(f"  {code}: name={result.get('name')}, industry={result.get('industry')}")
    else:
        print(f"  {code}: FAILED")

# 2. 测试 NeoData
print("\n[2] NeoData (总市值/PE)")
for code in ['600519', '000858']:
    result = _neodata_query(code)
    if result:
        mv = result.get('total_mv', 0)
        pe = result.get('pe_ttm', 0)
        print(f"  {code}: total_mv={mv:,.0f}元 ({mv/1e8:,.2f}亿), PE-TTM={pe}")
    else:
        print(f"  {code}: FAILED")

# 3. 测试 DataProvider 完整接口
print("\n[3] DataProvider 完整接口")
for symbol in ['600519', '000858']:
    print(f"\n  [{symbol}]")
    name = DataProvider.get_stock_name(symbol)
    industry = DataProvider.get_industry(symbol)
    quote = DataProvider.get_stock_quote(symbol)
    print(f"    名称:     {name}")
    print(f"    行业:     {industry}")
    print(f"    总市值(亿): {quote['total_mv']/1e8:,.2f}")
    print(f"    PE-TTM:   {quote['pe_ttm']}")

print("\n完成")
