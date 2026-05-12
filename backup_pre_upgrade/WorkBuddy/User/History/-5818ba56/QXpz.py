#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""调试五粮液同比数据异常"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ['PYTHONIOENCODING'] = 'utf-8'
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import pandas as pd
from data_provider import DataProvider
from calculator import IndicatorCalculator
from datetime import datetime

symbol = '000858'
provider = DataProvider()
df = provider.get_combined_financials(symbol)

print(f"五粮液财务数据: {len(df)} 条")
print(f"列名: {list(df.columns)}")

# 显示最近8期的关键数据
print("\n最近8期数据:")
recent = df.tail(8)[['report_date', 'revenue', 'net_profit_parent', 'ocf']]
for _, row in recent.iterrows():
    print(f"  {row['report_date'].date()}: 营收={row['revenue']/1e8:.2f}亿  净利润={row['net_profit_parent']/1e8:.2f}亿  OCF={row['ocf']/1e8:.2f}亿")

# 手动计算单季数据
print("\n手动计算单季:")
df2 = df.copy()
for col in ['revenue', 'net_profit_parent']:
    df2[f'q_{col}'] = df2[col].diff()
    # Q1不差分
    df2.loc[df2['report_date'].dt.month == 3, f'q_{col}'] = df2.loc[df2['report_date'].dt.month == 3, col]

print("\n单季数据（最近8期）:")
for _, row in df2.tail(8).iterrows():
    q_rev = row.get('q_revenue', 0) or 0
    q_np = row.get('q_net_profit_parent', 0) or 0
    print(f"  {row['report_date'].date()}: 单季营收={q_rev/1e8:.2f}亿  单季净利润={q_np/1e8:.2f}亿")

# 用IndicatorCalculator计算
print("\nIndicatorCalculator 计算结果:")
calc = IndicatorCalculator(df, eval_date=pd.Timestamp(datetime.today()))
print(f"  q_revenue_yoy: {calc.q_revenue_yoy:.2f}%")
print(f"  q_net_profit_yoy: {calc.q_net_profit_yoy:.2f}%")
print(f"  roe_ttm: {calc.roe_ttm:.2f}%")
print(f"  gross_margin_ttm: {calc.gross_margin_ttm:.2f}%")

# 检查最新两期的单季数据
print("\n检查最新两期单季净利润:")
df3 = df.copy()
# 手动拆分单季
for i in range(len(df3)):
    row = df3.iloc[i]
    month = row['report_date'].month
    if month == 3:
        df3.at[df3.index[i], 'q_np'] = row['net_profit_parent']
    elif month in [6, 9, 12]:
        prev_month = {6: 3, 9: 6, 12: 9}[month]
        prev_rows = df3[(df3['report_date'].dt.year == row['report_date'].year) & 
                        (df3['report_date'].dt.month == prev_month)]
        if not prev_rows.empty:
            prev_np = prev_rows.iloc[0]['net_profit_parent']
            df3.at[df3.index[i], 'q_np'] = row['net_profit_parent'] - prev_np
        else:
            df3.at[df3.index[i], 'q_np'] = None
    else:
        df3.at[df3.index[i], 'q_np'] = None

print("最近8期单季净利润:")
for _, row in df3.tail(8).iterrows():
    q_np = row.get('q_np', None)
    if q_np is not None:
        print(f"  {row['report_date'].date()}: 单季净利润={q_np/1e8:.2f}亿")
    else:
        print(f"  {row['report_date'].date()}: 单季净利润=N/A")
