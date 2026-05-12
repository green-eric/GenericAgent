#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""调试行情数据获取"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ['PYTHONIOENCODING'] = 'utf-8'

import akshare as ak
import json

print("=== 测试东方财富 stock_individual_info_em ===")
try:
    info = ak.stock_individual_info_em(symbol='600519')
    print(f"  行数: {len(info)}")
    print(f"  列名: {list(info.columns)}")
    print(f"  内容:")
    for _, row in info.iterrows():
        print(f"    {row['item']}: {row['value']}")
except Exception as e:
    print(f"  失败: {type(e).__name__}: {e}")

print("\n=== 测试 AkShare stock_zh_a_spot_em ===")
try:
    spot = ak.stock_zh_a_spot_em()
    print(f"  行数: {len(spot)}")
    print(f"  列名: {list(spot.columns)}")
    code_col = '代码' if '代码' in spot.columns else spot.columns[0]
    row = spot[spot[code_col] == '600519']
    if not row.empty:
        print(f"  600519 数据:")
        for col in spot.columns:
            val = row[col].values[0]
            if pd.notna(val) and str(val).strip():
                print(f"    {col}: {val}")
    else:
        print(f"  未找到 600519")
except Exception as e:
    print(f"  失败: {type(e).__name__}: {e}")

import pandas as pd

print("\n=== 测试 westock-data kline ===")
import subprocess
r = subprocess.run(
    'npx --yes westock-data-skillhub@latest kline sh600519 day 5',
    shell=True, capture_output=True, text=True, encoding='utf-8', timeout=60
)
output = r.stdout + r.stderr
lines = [l.strip() for l in output.split('\n') if l.strip().startswith('|')]
print(f"  表格行数: {len(lines)}")
for l in lines[:4]:
    print(f"  {l[:150]}")

print("\n=== 测试 westock-data finance ===")
r = subprocess.run(
    'npx --yes westock-data-skillhub@latest finance sh600519 4',
    shell=True, capture_output=True, text=True, encoding='utf-8', timeout=60
)
output = r.stdout + r.stderr
lines = [l.strip() for l in output.split('\n') if l.strip().startswith('|')]
print(f"  表格行数: {len(lines)}")
for l in lines[:4]:
    print(f"  {l[:150]}")
