#!/usr/bin/env python3
"""精简版银行股检查 - 输出到文件"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import sqlite3, pandas as pd, logging
sys.path.insert(0, r'd:\Project\ScoreSys')

# 禁用akshare日志到stdout
logging.getLogger('ScoreSys').setLevel(logging.ERROR)

TEST_DB = r'd:\Project\ScoreSys\stock_data_test.db'
OUT = r'd:\Project\ScoreSys\bank_check_result.txt'

result = []

# 1. DB中的值
conn = sqlite3.connect(TEST_DB)
cur = conn.cursor()
symbol = '601398'
cur.execute("SELECT report_date, oper_cost, current_assets, current_liab, cash_from_sales, capex FROM financials WHERE symbol=? ORDER BY report_date DESC LIMIT 3", (symbol,))
rows = cur.fetchall()
result.append("DB中601398最新3期:")
for r in rows:
    result.append(f"  {r[0]}: oper_cost={r[1]}, current_assets={r[2]}, current_liab={r[3]}, cash_from_sales={r[4]}, capex={r[5]}")
conn.close()

# 2. 直接从API获取各表
import akshare as ak
from data_provider import DataProvider, PROFIT_METRICS, BALANCE_METRICS, CASHFLOW_METRICS
from data_provider import PROFIT_COLS, BALANCE_COLS, CASHFLOW_COLS

profit = DataProvider._fetch_and_pivot(symbol, ak.stock_financial_benefit_new_ths, 'profit', PROFIT_METRICS)
balance = DataProvider._fetch_and_pivot(symbol, ak.stock_financial_debt_new_ths, 'balance', BALANCE_METRICS)
cashflow = DataProvider._fetch_and_pivot(symbol, ak.stock_financial_cash_new_ths, 'cashflow', CASHFLOW_METRICS)

if profit is not None:
    result.append(f"\n利润表行数: {len(profit)}")
    if 'operating_costs' in profit.columns:
        vals = profit[['report_date', 'operating_costs']].tail(3)
        for _, row in vals.iterrows():
            v = row['operating_costs']
            result.append(f"  operating_costs @ {row['report_date']}: '{v}' (type={type(v).__name__})")

if balance is not None:
    result.append(f"\n资产负债表行数: {len(balance)}")
    for col_name in ['total_current_assets', 'current_total_debt']:
        if col_name in balance.columns:
            vals = balance[['report_date', col_name]].tail(3)
            for _, row in vals.iterrows():
                v = row[col_name]
                result.append(f"  {col_name} @ {row['report_date']}: '{v}' (type={type(v).__name__})")
        else:
            result.append(f"  {col_name} 列不存在!")

if cashflow is not None:
    result.append(f"\n现金流量表行数: {len(cashflow)}")
    for col_name in ['sale_received_cash', 'pay_fixed_assets_etc_cash']:
        if col_name in cashflow.columns:
            vals = cashflow[['report_date', col_name]].tail(3)
            for _, row in vals.iterrows():
                v = row[col_name]
                result.append(f"  {col_name} @ {row['report_date']}: '{v}' (type={type(v).__name__})")
        else:
            result.append(f"  {col_name} 列不存在!")

# 3. 合并检查
if profit is not None and balance is not None and cashflow is not None:
    p = profit.rename(columns=PROFIT_COLS)
    b = balance.rename(columns=BALANCE_COLS)
    c = cashflow.rename(columns=CASHFLOW_COLS)
    
    result.append(f"\n利润表oper_cost最新3期:")
    if 'oper_cost' in p.columns:
        vals = p[['report_date', 'oper_cost']].tail(3)
        for _, row in vals.iterrows():
            result.append(f"  {row['report_date']}: oper_cost='{row['oper_cost']}'")
    
    result.append(f"\n资产负债表current_assets最新3期:")
    if 'current_assets' in b.columns:
        vals = b[['report_date', 'current_assets']].tail(3)
        for _, row in vals.iterrows():
            result.append(f"  {row['report_date']}: current_assets='{row['current_assets']}'")
    
    result.append(f"\n现金流量表cash_from_sales最新3期:")
    if 'cash_from_sales' in c.columns:
        vals = c[['report_date', 'cash_from_sales']].tail(3)
        for _, row in vals.iterrows():
            result.append(f"  {row['report_date']}: cash_from_sales='{row['cash_from_sales']}'")

    # 检查inner join后的合并
    p['report_date'] = pd.to_datetime(p['report_date'])
    b['report_date'] = pd.to_datetime(b['report_date'])
    c['report_date'] = pd.to_datetime(c['report_date'])
    
    merged = pd.merge(p, b, on='report_date', how='inner')
    merged = pd.merge(merged, c, on='report_date', how='inner')
    result.append(f"\n合并后行数: {len(merged)} (利润{len(p)} + 资产{len(b)} + 现金{len(c)})")
    
    # 检查合并后的字段值
    result.append(f"\n合并后oper_cost最新3期:")
    for _, row in merged[['report_date', 'oper_cost']].tail(3).iterrows():
        result.append(f"  {row['report_date']}: oper_cost={row['oper_cost']}")
    
    result.append(f"\n合并后current_assets最新3期:")
    for _, row in merged[['report_date', 'current_assets']].tail(3).iterrows():
        result.append(f"  {row['report_date']}: current_assets={row['current_assets']}")
    
    result.append(f"\n合并后cash_from_sales最新3期:")
    for _, row in merged[['report_date', 'cash_from_sales']].tail(3).iterrows():
        result.append(f"  {row['report_date']}: cash_from_sales={row['cash_from_sales']}")

with open(OUT, 'w', encoding='utf-8') as f:
    f.write('\n'.join(result))
print("Done")
