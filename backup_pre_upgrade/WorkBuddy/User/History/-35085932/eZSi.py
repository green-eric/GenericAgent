#!/usr/bin/env python3
"""验证Excel输出中每个字段的值"""
import pandas as pd

df = pd.read_excel(r'd:\Project\ScoreSys\score_test.xlsx', header=[0])
print("Excel列名:", list(df.columns))
print(f"\n行数: {len(df)}")

# 检查每个值是否为0
for idx, row in df.iterrows():
    symbol = row.iloc[0]  # 股票代码
    print(f"\n--- {symbol} ---")
    for col in df.columns:
        val = row[col]
        cn = col.split('\n')[0] if '\n' in str(col) else str(col)
        is_zero = (pd.isna(val) or val == 0 or val == 0.0 or val == '0')
        # 只标记应为非零的字段
        nonzero_fields = ['ROE', '毛利率', '净现比', '收现比', 'D/E', '流动比率', 
                          '资产负债率', '市盈率', '总市值', '总分', '盈利能力', 
                          '现金流质量', '偿债风险', 'FCF收益率']
        should_check = any(f in cn for f in nonzero_fields)
        if is_zero and should_check:
            print(f"  {cn}: {val} <<< ZERO!")
        elif should_check:
            print(f"  {cn}: {val}")
