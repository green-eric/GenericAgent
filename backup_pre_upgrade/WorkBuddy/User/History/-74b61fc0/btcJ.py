#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试备用数据源"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_provider import DataProvider

for symbol in ['600519', '000858']:
    print(f"\n=== {symbol} ===")
    name = DataProvider.get_stock_name(symbol)
    industry = DataProvider.get_industry(symbol)
    quote = DataProvider.get_stock_quote(symbol)
    is_st = DataProvider.is_st_stock(symbol)
    print(f"  名称: {name}")
    print(f"  行业: {industry}")
    print(f"  总市值(元): {quote['total_mv']:,.0f}")
    print(f"  总市值(亿): {quote['total_mv']/1e8:,.2f}")
    print(f"  PE-TTM: {quote['pe_ttm']}")
    print(f"  ST: {is_st}")
print("\nDONE")
