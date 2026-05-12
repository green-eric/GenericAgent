#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""调试API - 寻找替代接口获取名称/行业/行情"""
import akshare as ak
import time

symbol = '600519'

# 方案1: 从财务数据中获取名称
print("=== 方案1: 检查财务数据中是否有名称 ===")
try:
    df = ak.stock_financial_benefit_new_ths(symbol=symbol, indicator="按报告期")
    if not df.empty:
        print(f"Columns: {df.columns.tolist()}")
        # 检查是否有名称相关列
        for col in df.columns:
            if 'name' in col.lower() or '名称' in col:
                print(f"  Found: {col} = {df[col].unique()[:5]}")
except Exception as e:
    print(f"Error: {e}")

time.sleep(2)

# 方案2: 东方财富股票基本信息
print("\n=== 方案2: stock_individual_info_em with retry ===")
for attempt in range(3):
    try:
        info = ak.stock_individual_info_em(symbol=symbol)
        print(f"OK: {info.to_string()}")
        break
    except Exception as e:
        print(f"Attempt {attempt+1} failed: {e}")
        time.sleep(3)

time.sleep(2)

# 方案3: 尝试新浪财经接口
print("\n=== 方案3: 尝试其他接口 ===")
try:
    # 东方财富历史行情（可能包含名称）
    hist = ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date="20250101", adjust="qfq")
    if not hist.empty:
        print(f"hist columns: {hist.columns.tolist()}")
        print(hist.tail(3).to_string())
except Exception as e:
    print(f"Error: {e}")

time.sleep(2)

# 方案4: 东方财富概念板块（可能包含行业）
print("\n=== 方案4: stock_board_industry_name_em ===")
try:
    boards = ak.stock_board_industry_name_em()
    print(f"Boards: {boards.columns.tolist()}")
    print(boards.head(5).to_string())
except Exception as e:
    print(f"Error: {e}")
