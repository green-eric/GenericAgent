#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""调试API - 测试不同接口"""
import akshare as ak
import time

symbol = '600519'

# 测试1: 财务数据接口
print("=== Test 1: stock_financial_benefit_new_ths ===")
try:
    df = ak.stock_financial_benefit_new_ths(symbol=symbol, indicator="按报告期")
    print(f"OK: {len(df)} rows")
    if not df.empty:
        print(f"Columns: {df.columns.tolist()}")
        print(f"Metrics: {df['metric_name'].unique().tolist()[:10]}")
except Exception as e:
    print(f"Error: {e}")

time.sleep(2)

# 测试2: 行情接口
print("\n=== Test 2: stock_individual_info_em ===")
try:
    info = ak.stock_individual_info_em(symbol=symbol)
    print(f"OK: {len(info)} rows")
    print(info.to_string())
except Exception as e:
    print(f"Error: {e}")

time.sleep(2)

# 测试3: 尝试东方财富实时行情
print("\n=== Test 3: stock_zh_a_spot_em ===")
try:
    spot = ak.stock_zh_a_spot_em()
    row = spot[spot['代码'] == symbol]
    if not row.empty:
        print(f"OK: {row[['代码','名称','最新价','总市值','市盈率-动态']].to_string()}")
    else:
        print("Not found")
except Exception as e:
    print(f"Error: {e}")

time.sleep(2)

# 测试4: 腾讯行情
print("\n=== Test 4: stock_zh_a_daily (腾讯) ===")
try:
    df = ak.stock_zh_a_daily(symbol="sh600519", adjust="qfq")
    if not df.empty:
        latest = df.iloc[-1]
        print(f"Latest date: {latest.name}, Close: {latest['close']}")
except Exception as e:
    print(f"Error: {e}")
