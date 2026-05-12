#!/usr/bin/env python3
"""调试fin_expense列映射问题"""
import akshare as ak
import pandas as pd
import sys
sys.path.insert(0, r'd:\Project\ScoreSys')
from data_provider import DataProvider, PROFIT_METRICS, PROFIT_COLS, FINAL_COLS

symbol = '600519'

# Step 1: 原始利润表
print("=== Step 1: 原始利润表 ===")
df = ak.stock_financial_benefit_new_ths(symbol=symbol, indicator="按报告期")
df_filtered = df[df['metric_name'].isin(PROFIT_METRICS)]
pivot = df.pivot_table(index='report_date', columns='metric_name', values='value', aggfunc='first').reset_index()
print(f"列名: {list(pivot.columns)}")

# Step 2: rename后
profit = pivot.rename(columns=PROFIT_COLS)
print(f"\n=== Step 2: rename后列名 ===")
print(f"列名: {list(profit.columns)}")
dup_cols = [c for c in profit.columns if list(profit.columns).count(c) > 1]
print(f"重复列: {dup_cols}")

# 检查fin_expense列（如果重复）
if 'fin_expense' in profit.columns:
    # 可能有多个fin_expense列
    fe_cols = [c for c in profit.columns if c == 'fin_expense']
    print(f"\nfin_expense列数量: {len(fe_cols)}")
    
# Step 3: dedup后
profit_dedup = profit.loc[:, ~profit.columns.duplicated(keep='first')]
print(f"\n=== Step 3: dedup后列名 ===")
print(f"列名: {list(profit_dedup.columns)}")

# 检查fin_expense的值
if 'fin_expense' in profit_dedup.columns:
    latest = profit_dedup.tail(4)
    print(f"\nfin_expense最新4期值:")
    for _, row in latest.iterrows():
        print(f"  {row['report_date']} | fin_expense = {row.get('fin_expense', 'N/A')}")

# Step 4: 更好的方式 - 优先用interest_expenses
print(f"\n=== Step 4: 修正方案 - 用interest_expenses ===")
# 先移除financial_interest_expenses列（如果存在）
if 'financial_interest_expenses' in pivot.columns and 'interest_expenses' in pivot.columns:
    # 优先保留interest_expenses（值更大，更常用）
    pivot_fixed = pivot.drop(columns=['financial_interest_expenses'])
    profit_fixed = pivot_fixed.rename(columns=PROFIT_COLS)
    profit_fixed = profit_fixed.loc[:, ~profit_fixed.columns.duplicated(keep='first')]
    if 'fin_expense' in profit_fixed.columns:
        latest = profit_fixed.tail(4)
        print(f"修正后fin_expense最新4期值:")
        for _, row in latest.iterrows():
            print(f"  {row['report_date']} | fin_expense = {row.get('fin_expense', 'N/A')}")
