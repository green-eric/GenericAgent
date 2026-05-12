#!/usr/bin/env python3
"""精简版银行股检查"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import sqlite3, pandas as pd, os
sys.path.insert(0, r'd:\Project\ScoreSys')

TEST_DB = r'd:\Project\ScoreSys\stock_data_test.db'

# 1. DB中的值
conn = sqlite3.connect(TEST_DB)
cur = conn.cursor()
symbol = '601398'
cur.execute("SELECT report_date, oper_cost, current_assets, current_liab, cash_from_sales, capex FROM financials WHERE symbol=? ORDER BY report_date DESC LIMIT 3", (symbol,))
rows = cur.fetchall()
print("DB中601398最新3期:")
for r in rows:
    print(f"  {r[0]}: oper_cost={r[1]}, current_assets={r[2]}, current_liab={r[3]}, cash_from_sales={r[4]}, capex={r[5]}")
conn.close()

# 2. 重新获取一次，检查各表数据和合并后差异
import akshare as ak
from data_provider import DataProvider, PROFIT_METRICS, BALANCE_METRICS, CASHFLOW_METRICS
from data_provider import PROFIT_COLS, BALANCE_COLS, CASHFLOW_COLS

# 利润表
profit = DataProvider._fetch_and_pivot(symbol, ak.stock_financial_benefit_new_ths, 'profit', PROFIT_METRICS)
# 资产负债表
balance = DataProvider._fetch_and_pivot(symbol, ak.stock_financial_debt_new_ths, 'balance', BALANCE_METRICS)
# 现金流量表
cashflow = DataProvider._fetch_and_pivot(symbol, ak.stock_financial_cash_new_ths, 'cashflow', CASHFLOW_METRICS)

if profit is not None:
    print(f"\n利润表行数: {len(profit)}")
    # 检查operating_costs值
    if 'operating_costs' in profit.columns:
        vals = profit[['report_date', 'operating_costs']].tail(3)
        for _, row in vals.iterrows():
            v = row['operating_costs']
            print(f"  operating_costs @ {row['report_date']}: '{v}' (type={type(v).__name__})")

if balance is not None:
    print(f"\n资产负债表行数: {len(balance)}")
    # 检查total_current_assets
    if 'total_current_assets' in balance.columns:
        vals = balance[['report_date', 'total_current_assets']].tail(3)
        for _, row in vals.iterrows():
            v = row['total_current_assets']
            print(f"  total_current_assets @ {row['report_date']}: '{v}' (type={type(v).__name__})")
    else:
        print("  total_current_assets 列不存在!")
    
    if 'current_total_debt' in balance.columns:
        vals = balance[['report_date', 'current_total_debt']].tail(3)
        for _, row in vals.iterrows():
            v = row['current_total_debt']
            print(f"  current_total_debt @ {row['report_date']}: '{v}' (type={type(v).__name__})")

if cashflow is not None:
    print(f"\n现金流量表行数: {len(cashflow)}")
    if 'sale_received_cash' in cashflow.columns:
        vals = cashflow[['report_date', 'sale_received_cash']].tail(3)
        for _, row in vals.iterrows():
            v = row['sale_received_cash']
            print(f"  sale_received_cash @ {row['report_date']}: '{v}' (type={type(v).__name__})")
    else:
        print("  sale_received_cash 列不存在!")
    
    if 'pay_fixed_assets_etc_cash' in cashflow.columns:
        vals = cashflow[['report_date', 'pay_fixed_assets_etc_cash']].tail(3)
        for _, row in vals.iterrows():
            v = row['pay_fixed_assets_etc_cash']
            print(f"  pay_fixed_assets_etc_cash @ {row['report_date']}: '{v}' (type={type(v).__name__})")
    else:
        print("  pay_fixed_assets_etc_cash 列不存在!")

# 3. 合并后检查
if profit is not None and balance is not None and cashflow is not None:
    p = profit.rename(columns=PROFIT_COLS)
    b = balance.rename(columns=BALANCE_COLS)
    c = cashflow.rename(columns=CASHFLOW_COLS)
    
    # 检查report_date格式
    print(f"\n利润表report_date类型: {p['report_date'].dtype}, 示例: {p['report_date'].iloc[0]}")
    print(f"资产负债表report_date类型: {b['report_date'].dtype}, 示例: {b['report_date'].iloc[0]}")
    print(f"现金流量表report_date类型: {c['report_date'].dtype}, 示例: {c['report_date'].iloc[0]}")
    
    # 检查日期匹配
    p_dates = set(str(x) for x in p['report_date'])
    b_dates = set(str(x) for x in b['report_date'])
    c_dates = set(str(x) for x in c['report_date'])
    common = p_dates & b_dates & c_dates
    print(f"\n三表共同报告期: {len(common)} / 利润{len(p_dates)} / 资产{len(b_dates)} / 现金{len(c_dates)}")
    
    if len(common) < len(p_dates):
        missing_p = p_dates - common
        print(f"利润表独有日期(前5): {sorted(missing_p)[:5]}")
