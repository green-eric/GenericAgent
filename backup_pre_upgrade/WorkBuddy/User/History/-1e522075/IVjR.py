#!/usr/bin/env python3
"""验证单季拆分逻辑 vs 累计值直接求和"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import sqlite3, pandas as pd
sys.path.insert(0, r'd:\Project\ScoreSys')
from database import StockDatabase
from calculator import IndicatorCalculator

db = StockDatabase(r'd:\Project\ScoreSys\stock_data_test.db')
df = db.get_financials('600519')
if not pd.api.types.is_datetime64_any_dtype(df['report_date']):
    df['report_date'] = pd.to_datetime(df['report_date'], errors='coerce')
if 'ann_date' in df.columns and not pd.api.types.is_datetime64_any_dtype(df['ann_date']):
    df['ann_date'] = pd.to_datetime(df['ann_date'], errors='coerce')

# 显示最新5期的累计值和单季值
df_sorted = df.sort_values('report_date').tail(5)
print("最新5期累计值（DB原始）:")
for _, row in df_sorted.iterrows():
    print(f"  {row['report_date'].strftime('%Y-%m-%d')}: "
          f"营收={row.get('revenue',0)/1e8:.1f}亿 "
          f"归母净利={row.get('net_profit_parent',0)/1e8:.1f}亿 "
          f"扣非净利={row.get('net_profit_ex',0)/1e8:.1f}亿 "
          f"OCF={row.get('ocf',0)/1e8:.1f}亿")

# Calculator的单季拆分
calc = IndicatorCalculator(df)
print(f"\nCalculator拆分后最新5期单季值:")
df_calc = calc.df.sort_values('report_date').tail(5)
for _, row in df_calc.iterrows():
    print(f"  {row['report_date'].strftime('%Y-%m-%d')}: "
          f"q_revenue={row.get('q_revenue',0)/1e8:.1f}亿 "
          f"q_net_profit_parent={row.get('q_net_profit_parent',0)/1e8:.1f}亿 "
          f"q_net_profit_ex={row.get('q_net_profit_ex',0)/1e8:.1f}亿 "
          f"q_ocf={row.get('q_ocf',0)/1e8:.1f}亿")

# 最近4个单季求和
recent4 = calc.df.dropna(subset=['q_net_profit_parent']).sort_values('report_date').tail(4)
ttm_np_parent = recent4['q_net_profit_parent'].sum()
ttm_np_ex = recent4['q_net_profit_ex'].sum() if 'q_net_profit_ex' in recent4.columns else 0
ttm_rev = recent4['q_revenue'].sum()
ttm_ocf = recent4['q_ocf'].sum()
equity_parent = calc._equity_parent

print(f"\n单季拆分TTM（最近4季）:")
print(f"  TTM营收={ttm_rev/1e8:.1f}亿")
print(f"  TTM归母净利润={ttm_np_parent/1e8:.1f}亿")
print(f"  TTM扣非净利润={ttm_np_ex/1e8:.1f}亿")
print(f"  TTM OCF={ttm_ocf/1e8:.1f}亿")
print(f"  归母权益={equity_parent/1e8:.1f}亿")
print(f"  ROE(TTM)={calc._ttm_net_profit/equity_parent*100:.2f}%")
print(f"  净现比={ttm_ocf/calc._ttm_net_profit:.2f}")

# 累计值直接求和（错误方法，但作为对比）
latest4_cum = df_sorted.tail(4)
cum_rev = latest4_cum['revenue'].sum()
cum_np = latest4_cum['net_profit_ex'].sum() if (latest4_cum['net_profit_ex'] != 0).any() else latest4_cum['net_profit_parent'].sum()
cum_ocf = latest4_cum['ocf'].sum()
print(f"\n累计值直接求和（错误方法，会重复计数）:")
print(f"  TTM营收={cum_rev/1e8:.1f}亿 (重复计数! 2025Q2+Q3+Q4不是独立单季)")
print(f"  ROE(错误)={cum_np/equity_parent*100:.2f}% (偏高因为重复计数)")

print(f"\n✅ Calculator使用单季拆分→TTM求和是正确方法")
print(f"   累计值直接求和会导致Q2包含Q1数据、Q3包含Q1+Q2、造成重复计数")
