#!/usr/bin/env python3
"""测试数据完整度功能"""
import pandas as pd
import numpy as np
from calculator import IndicatorCalculator

# 构造只有3个季度的数据（缺Q2）
data = {
    'report_date': pd.to_datetime(['2024-03-31', '2024-09-30', '2024-12-31', '2025-03-31']),
    'ann_date': pd.to_datetime(['2024-04-30', '2024-10-31', '2025-04-30', '2025-04-30']),
    'revenue': [100, 200, 300, 150],
    'oper_cost': [50, 100, 150, 75],
    'oper_profit': [50, 100, 150, 75],
    'net_profit_parent': [30, 60, 90, 45],
    'net_profit_ex': [25, 50, 75, 38],
    'fin_expense': [5, 5, 5, 5],
    'total_assets': [1000, 1100, 1200, 1300],
    'total_liab': [400, 440, 480, 520],
    'total_equity': [600, 660, 720, 780],
    'equity_parent': [580, 640, 700, 760],
    'current_assets': [300, 330, 360, 390],
    'current_liab': [150, 165, 180, 195],
    'ocf': [40, 70, 100, 50],
    'capex': [10, 15, 20, 12],
    'cash_from_sales': [95, 190, 285, 142],
}
df = pd.DataFrame(data)
calc = IndicatorCalculator(df, eval_date=pd.Timestamp('2025-04-28'))
comp = calc.get_completeness_info()
print('=== 缺Q2场景 ===')
print(f'  score: {comp["score"]}')
print(f'  quarter_coverage: {comp["quarter_coverage"]}')
print(f'  field_gaps: {comp["field_gaps"]}')

# 构造只有2个季度的数据（缺Q1,Q3）
data3 = {
    'report_date': pd.to_datetime(['2024-06-30', '2024-12-31']),
    'ann_date': pd.to_datetime(['2024-08-30', '2025-04-30']),
    'revenue': [200, 300],
    'oper_cost': [100, 150],
    'oper_profit': [100, 150],
    'net_profit_parent': [60, 90],
    'net_profit_ex': [50, 75],
    'fin_expense': [5, 5],
    'total_assets': [1100, 1200],
    'total_liab': [440, 480],
    'total_equity': [660, 720],
    'equity_parent': [640, 700],
    'current_assets': [330, 360],
    'current_liab': [165, 180],
    'ocf': [70, 100],
    'capex': [15, 20],
    'cash_from_sales': [190, 285],
}
df3 = pd.DataFrame(data3)
calc3 = IndicatorCalculator(df3, eval_date=pd.Timestamp('2025-04-28'))
comp3 = calc3.get_completeness_info()
print()
print('=== 缺Q1,Q3场景 ===')
print(f'  score: {comp3["score"]}')
print(f'  quarter_coverage: {comp3["quarter_coverage"]}')
print(f'  field_gaps: {comp3["field_gaps"]}')

# 4/4完整场景
data4 = {
    'report_date': pd.to_datetime(['2024-03-31', '2024-06-30', '2024-09-30', '2024-12-31']),
    'ann_date': pd.to_datetime(['2024-04-30', '2024-08-30', '2024-10-31', '2025-04-30']),
    'revenue': [100, 200, 300, 400],
    'oper_cost': [50, 100, 150, 200],
    'oper_profit': [50, 100, 150, 200],
    'net_profit_parent': [30, 60, 90, 120],
    'net_profit_ex': [25, 50, 75, 100],
    'fin_expense': [5, 5, 5, 5],
    'total_assets': [1000, 1100, 1200, 1300],
    'total_liab': [400, 440, 480, 520],
    'total_equity': [600, 660, 720, 780],
    'equity_parent': [580, 640, 700, 760],
    'current_assets': [300, 330, 360, 390],
    'current_liab': [150, 165, 180, 195],
    'ocf': [40, 70, 100, 130],
    'capex': [10, 15, 20, 25],
    'cash_from_sales': [95, 190, 285, 380],
}
df4 = pd.DataFrame(data4)
calc4 = IndicatorCalculator(df4, eval_date=pd.Timestamp('2025-04-28'))
comp4 = calc4.get_completeness_info()
print()
print('=== 4/4完整场景 ===')
print(f'  score: {comp4["score"]}')
print(f'  quarter_coverage: {comp4["quarter_coverage"]}')
print(f'  field_gaps: {comp4["field_gaps"]}')

# 有NaN字段场景（ocf全为NaN）
data5 = data4.copy()
data5['ocf'] = [np.nan, np.nan, np.nan, np.nan]
df5 = pd.DataFrame(data5)
calc5 = IndicatorCalculator(df5, eval_date=pd.Timestamp('2025-04-28'))
comp5 = calc5.get_completeness_info()
print()
print('=== OCF全NaN场景 ===')
print(f'  score: {comp5["score"]}')
print(f'  quarter_coverage: {comp5["quarter_coverage"]}')
print(f'  field_gaps: {comp5["field_gaps"]}')
