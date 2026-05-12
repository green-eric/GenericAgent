#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查AkShare利润表API实际返回的metric_name"""
import akshare as ak
import pandas as pd

symbol = '600519'
print(f"=== {symbol} 利润表指标 ===")
df = ak.stock_financial_benefit_new_ths(symbol=symbol, indicator="按报告期")
all_metrics = sorted(df['metric_name'].unique())
print(f"共 {len(all_metrics)} 个指标：")
for m in all_metrics:
    print(f"  {m}")

# 查找扣非净利润相关
print(f"\n=== 扣非相关指标 ===")
for m in all_metrics:
    if '扣' in m or 'deduct' in m.lower() or '非经' in m or 'ex' in m.lower():
        print(f"  >>> {m}")

# 查找利息/财务费用相关
print(f"\n=== 利息/财务费用相关 ===")
for m in all_metrics:
    if '利息' in m or 'interest' in m.lower() or '财务费' in m or 'financ' in m.lower():
        print(f"  >>> {m}")

# 检查实际的值
print(f"\n=== 最新4期关键指标值 ===")
latest_dates = sorted(df['report_date'].unique())[-4:]
for d in latest_dates:
    sub = df[df['report_date'] == d]
    for metric in ['parent_holder_net_profit', 'index_deduct_holder_net_profit', 
                   'operating_income', 'operating_profit', 'interest_expenses',
                   'financial_interest_expenses']:
        rows = sub[sub['metric_name'] == metric]
        if not rows.empty:
            val = rows['value'].values[0]
            print(f"  {d} | {metric}: {val}")
        else:
            print(f"  {d} | {metric}: N/A")
