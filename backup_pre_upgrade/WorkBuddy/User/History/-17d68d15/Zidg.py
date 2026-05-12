#!/usr/bin/env python3
"""检查000858利润表API是否返回interest_expenses"""
import akshare as ak

symbol = '000858'
df = ak.stock_financial_benefit_new_ths(symbol=symbol, indicator="按报告期")

# 检查是否有interest_expenses
ie = df[df['metric_name'] == 'interest_expenses']
fie = df[df['metric_name'] == 'financial_interest_expenses']
bff = df[df['metric_name'] == 'benefit_finance_fee']

print(f"interest_expenses: {len(ie)} rows")
if not ie.empty:
    print(f"  values: {list(ie['value'].tail(4).values)}")

print(f"financial_interest_expenses: {len(fie)} rows")
if not fie.empty:
    print(f"  values: {list(fie['value'].tail(4).values)}")

print(f"benefit_finance_fee: {len(bff)} rows")
if not bff.empty:
    print(f"  values: {list(bff['value'].tail(4).values)}")

# 查找所有含"利息"或"interest"或"财务费"的指标
all_metrics = sorted(df['metric_name'].unique())
print(f"\n所有含利息/财务费的指标:")
for m in all_metrics:
    if '利息' in m or 'interest' in m.lower() or 'financ' in m.lower() or '财务' in m:
        vals = df[df['metric_name'] == m]['value'].tail(2).values
        print(f"  {m}: {list(vals)}")
