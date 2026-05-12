#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""调试API返回值"""
import akshare as ak
import json

symbol = '600519'

print("=== stock_individual_info_em ===")
try:
    info = ak.stock_individual_info_em(symbol=symbol)
    print(info.to_string())
except Exception as e:
    print(f"Error: {e}")

print("\n=== 检查字段 ===")
try:
    info = ak.stock_individual_info_em(symbol=symbol)
    print("Items:", info['item'].tolist())
    
    # 检查名称
    for key in ['股票简称', '名称', '股票名称', '简称']:
        rows = info[info['item'] == key]
        if not rows.empty:
            print(f"  名称(key={key}): {rows['value'].values[0]}")
    
    # 检查行业
    for key in ['行业', '所属行业', '申万行业', '行业分类']:
        rows = info[info['item'] == key]
        if not rows.empty:
            print(f"  行业(key={key}): {rows['value'].values[0]}")
    
    # 检查市值
    for key in ['总市值', '市值', '流通市值']:
        rows = info[info['item'] == key]
        if not rows.empty:
            print(f"  市值(key={key}): {rows['value'].values[0]}")
    
    # 检查PE
    for key in ['市盈率-动态', '市盈率', 'PE(TTM)', 'pe_ttm', '市盈率(动)', '市盈率(静)']:
        rows = info[info['item'] == key]
        if not rows.empty:
            print(f"  PE(key={key}): {rows['value'].values[0]}")
except Exception as e:
    print(f"Error: {e}")
