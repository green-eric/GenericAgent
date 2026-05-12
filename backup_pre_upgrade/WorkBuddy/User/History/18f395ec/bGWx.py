#!/usr/bin/env python3
"""检查银行股API返回的字段差异"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import akshare as ak
import pandas as pd

for symbol in ['601398', '600519']:
    print(f"\n{'='*60}")
    print(f"{symbol} 利润表所有metric_name:")
    df = ak.stock_financial_benefit_new_ths(symbol=symbol, indicator="按报告期")
    metrics = sorted(df['metric_name'].unique())
    for m in metrics:
        print(f"  {m}")
    
    # 检查关键字段
    needed = ['operating_income', 'operating_costs', 'operating_profit',
              'parent_holder_net_profit', 'index_deduct_holder_net_profit',
              'interest_expenses', 'benefit_finance_fee']
    print(f"\n  关键字段存在性:")
    for n in needed:
        exists = n in df['metric_name'].values
        print(f"    {n}: {'✅' if exists else '❌'}")
    
    print(f"\n{symbol} 资产负债表所有metric_name:")
    df2 = ak.stock_financial_debt_new_ths(symbol=symbol, indicator="按报告期")
    metrics2 = sorted(df2['metric_name'].unique())
    for m in metrics2:
        print(f"  {m}")
    
    needed2 = ['assets_total', 'total_debt', 'parent_holder_equity_total',
               'holder_equity_total', 'total_current_assets', 'current_total_debt']
    print(f"\n  关键字段存在性:")
    for n in needed2:
        exists = n in df2['metric_name'].values
        print(f"    {n}: {'✅' if exists else '❌'}")
    
    # 查找可能的替代字段
    print(f"\n  可能的流动资产/负债替代字段:")
    for m in metrics2:
        if 'current' in m.lower() or '流动' in m:
            print(f"    {m}")
    
    print(f"\n{symbol} 现金流量表所有metric_name:")
    df3 = ak.stock_financial_cash_new_ths(symbol=symbol, indicator="按报告期")
    metrics3 = sorted(df3['metric_name'].unique())
    for m in metrics3:
        print(f"  {m}")
    
    needed3 = ['act_cash_flow_net', 'pay_fixed_assets_etc_cash', 'sale_received_cash']
    print(f"\n  关键字段存在性:")
    for n in needed3:
        exists = n in df3['metric_name'].values
        print(f"    {n}: {'✅' if exists else '❌'}")
    
    # 查找可能的替代字段
    print(f"\n  可能的资本支出/收现替代字段:")
    for m in metrics3:
        if 'fixed' in m.lower() or 'sale' in m.lower() or 'invest' in m.lower():
            print(f"    {m}")
    
    # 只检查第一只就够
    if symbol == '601398':
        break
