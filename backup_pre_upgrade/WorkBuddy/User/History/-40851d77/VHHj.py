#!/usr/bin/env python3
"""深入检查银行股DB数据问题"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import sqlite3, pandas as pd
import akshare as ak

TEST_DB = r'd:\Project\ScoreSys\stock_data_test.db'
symbol = '601398'

# 1. DB中的值
conn = sqlite3.connect(TEST_DB)
cur = conn.cursor()
cur.execute("SELECT report_date, oper_cost, current_assets, current_liab, cash_from_sales, capex FROM financials WHERE symbol=? ORDER BY report_date DESC LIMIT 5", (symbol,))
rows = cur.fetchall()
print("DB中601398最新5期:")
for r in rows:
    print(f"  {r[0]}: oper_cost={r[1]}, current_assets={r[2]}, current_liab={r[3]}, cash_from_sales={r[4]}, capex={r[5]}")
conn.close()

# 2. 直接从API获取各表
print("\n\n直接API获取利润表:")
df_profit = ak.stock_financial_benefit_new_ths(symbol=symbol, indicator="按报告期")
for metric in ['operating_costs', 'operating_income']:
    sub = df_profit[df_profit['metric_name'] == metric].sort_values('report_date', ascending=False).head(3)
    for _, row in sub.iterrows():
        val = row['value']
        print(f"  {metric} @ {row['report_date']}: value='{val}' (type={type(val).__name__})")

print("\n\n直接API获取资产负债表:")
df_debt = ak.stock_financial_debt_new_ths(symbol=symbol, indicator="按报告期")
for metric in ['total_current_assets', 'current_total_debt', 'current_assets_special', 'current_debt_special']:
    sub = df_debt[df_debt['metric_name'] == metric].sort_values('report_date', ascending=False).head(3)
    if sub.empty:
        print(f"  {metric}: 不存在")
    else:
        for _, row in sub.iterrows():
            val = row['value']
            print(f"  {metric} @ {row['report_date']}: value='{val}' (type={type(val).__name__})")

print("\n\n直接API获取现金流量表:")
df_cash = ak.stock_financial_cash_new_ths(symbol=symbol, indicator="按报告期")
for metric in ['sale_received_cash', 'pay_fixed_assets_etc_cash', 'act_cash_flow_net']:
    sub = df_cash[df_cash['metric_name'] == metric].sort_values('report_date', ascending=False).head(3)
    if sub.empty:
        print(f"  {metric}: 不存在")
    else:
        for _, row in sub.iterrows():
            val = row['value']
            print(f"  {metric} @ {row['report_date']}: value='{val}' (type={type(val).__name__})")

# 3. 检查inner join是否丢失行
from data_provider import DataProvider, PROFIT_METRICS, BALANCE_METRICS, CASHFLOW_METRICS
from data_provider import PROFIT_COLS, BALANCE_COLS, CASHFLOW_COLS

profit = DataProvider._fetch_and_pivot(symbol, ak.stock_financial_benefit_new_ths, 'profit', PROFIT_METRICS)
balance = DataProvider._fetch_and_pivot(symbol, ak.stock_financial_debt_new_ths, 'balance', BALANCE_METRICS)
cashflow = DataProvider._fetch_and_pivot(symbol, ak.stock_financial_cash_new_ths, 'cashflow', CASHFLOW_METRICS)

if profit is not None:
    print(f"\n利润表行数: {len(profit)}")
if balance is not None:
    print(f"资产负债表行数: {len(balance)}")
if cashflow is not None:
    print(f"现金流量表行数: {len(cashflow)}")

# 检查合并后行数
if profit is not None and balance is not None:
    merged = pd.merge(profit.rename(columns=PROFIT_COLS), 
                      balance.rename(columns=BALANCE_COLS), 
                      on='report_date', how='inner')
    print(f"利润+资产inner join行数: {len(merged)}")
    if len(merged) < len(profit):
        # 找出缺失的报告期
        profit_dates = set(profit['report_date'])
        merged_dates = set(merged['report_date'])
        missing = profit_dates - merged_dates
        print(f"缺失的报告期: {sorted(missing)[:5]}")
