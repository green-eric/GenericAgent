#!/usr/bin/env python3
"""快速验证 calculator 优化正确性 + 性能基准"""
import pandas as pd
import numpy as np
import time
import sys
sys.path.insert(0, r'd:\Project\ScoreSys')
from calculator import IndicatorCalculator

# 构造测试数据：模拟8个季度的累计值
data = {
    'report_date': pd.to_datetime([
        '2024-03-31','2024-06-30','2024-09-30','2024-12-31',
        '2025-03-31','2025-06-30','2025-09-30','2025-12-31'
    ]),
    'ann_date': pd.to_datetime([
        '2024-04-30','2024-08-30','2024-10-30','2025-04-30',
        '2025-04-30','2025-08-30','2025-10-30','2026-04-30'
    ]),
    'revenue':        [100, 220, 350, 500,  110, 250, 400, 580],
    'oper_cost':      [60,  130, 210, 300,   65, 145, 240, 340],
    'oper_profit':    [40,   90, 140, 200,   45, 105, 160, 240],
    'net_profit_parent': [30, 70, 110, 160,  35,  85, 135, 200],
    'net_profit_ex':  [28,   65, 105, 150,   33,  80, 128, 190],
    'fin_expense':    [2,     4,   6,   8,    2,   4,   6,   8],
    'ocf':            [35,   80, 130, 180,   40,  95, 150, 220],
    'capex':          [10,   20,  30,  40,   12,  22,  32,  45],
    'cash_from_sales':[90,  200, 320, 460,  100, 230, 370, 540],
    'total_assets':   [500, 520, 540, 560,  580, 600, 620, 650],
    'total_liab':     [200, 210, 220, 230,  240, 250, 260, 270],
    'total_equity':   [300, 310, 320, 330,  340, 350, 360, 380],
    'equity_parent':  [280, 290, 300, 310,  320, 330, 340, 360],
    'current_assets': [150, 160, 170, 180,  190, 200, 210, 220],
    'current_liab':   [80,  85,  90,  95,  100, 105, 110, 115],
}
df = pd.DataFrame(data)

# 正确性验证
print("=" * 60)
print("正确性验证")
print("=" * 60)

calc = IndicatorCalculator(df, eval_date=pd.Timestamp('2026-04-28'))

# 期望单季值
expected_q_rev =    [100.0, 120.0, 130.0, 150.0, 110.0, 140.0, 150.0, 180.0]
expected_q_profit = [30.0,   40.0,  40.0,  50.0,  35.0,  50.0,  50.0,  65.0]

actual_q_rev = calc.df['q_revenue'].tolist()
actual_q_profit = calc.df['q_net_profit_parent'].tolist()

print(f"期望单季营收: {expected_q_rev}")
print(f"实际单季营收: {actual_q_rev}")
rev_ok = all(
    (np.isnan(a) and np.isnan(e)) or abs(a - e) < 0.01
    for a, e in zip(actual_q_rev, expected_q_rev)
)
print(f"单季营收验证: {'PASS' if rev_ok else 'FAIL'}")

print(f"\n期望单季归母净利: {expected_q_profit}")
print(f"实际单季归母净利: {actual_q_profit}")
profit_ok = all(
    (np.isnan(a) and np.isnan(e)) or abs(a - e) < 0.01
    for a, e in zip(actual_q_profit, expected_q_profit)
)
print(f"单季归母净利验证: {'PASS' if profit_ok else 'FAIL'}")

# 同比验证：2025Q1 vs 2024Q1
# revenue: 110/100 - 1 = 10%
# profit: 35/30 - 1 = 16.67%
print(f"\n2025Q1营收同比: {calc.df.iloc[4]['q_revenue_yoy']:.2f}% (期望: 10.00%)")
print(f"2025Q1净利同比: {calc.df.iloc[4]['q_net_profit_parent_yoy']:.2f}% (期望: 16.67%)")

# TTM验证
print(f"\nroe_ttm: {calc.roe_ttm:.2f}")
print(f"gross_margin_ttm: {calc.gross_margin_ttm:.2f}")
print(f"net_profit_ratio: {calc.net_profit_ratio:.2f}")
print(f"de_ratio: {calc.de_ratio:.2f}")
print(f"current_ratio: {calc.current_ratio:.2f}")

# 性能基准
print("\n" + "=" * 60)
print("性能基准 (1000次迭代)")
print("=" * 60)

N = 1000
t0 = time.time()
for _ in range(N):
    c = IndicatorCalculator(df, eval_date=pd.Timestamp('2026-04-28'))
elapsed = time.time() - t0
per_stock = elapsed / N * 1000
print(f"总耗时: {elapsed:.2f}s")
print(f"单次耗时: {per_stock:.2f}ms")
print(f"预估4344只: {per_stock * 4344 / 1000:.1f}s")

# 数据完整度验证
print("\n" + "=" * 60)
print("数据完整度验证")
print("=" * 60)
comp = calc.get_completeness_info()
print(f"完整度评分: {comp['score']}")
print(f"季度覆盖: {comp['quarter_coverage']}")
print(f"缺失字段: {comp['field_gaps']}")
