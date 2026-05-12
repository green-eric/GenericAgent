#!/usr/bin/env python3
"""验证Excel所有字段"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pandas as pd

df = pd.read_excel(r'd:\Project\ScoreSys\score_test.xlsx', header=[0])
print("Excel字段列表:")
for i, col in enumerate(df.columns):
    print(f"  {i+1}. {col}")

print(f"\n共{len(df)}行 x {len(df.columns)}列")

# 逐字段检查非零
print("\n逐字段值检查:")
zero_issues = []
for col in df.columns:
    for idx, row in df.iterrows():
        val = row[col]
        if isinstance(val, (int, float)) and val == 0:
            symbol = row.get(df.columns[0], '?')
            # 银行股允许的0值字段
            bank_zeros = ['毛利率(%)(TTM)', '收现比', '流动比率(倍)']
            col_cn = col.split('\n')[0] if '\n' in col else col
            if col_cn in bank_zeros and symbol in ['601398', '600036']:
                continue  # 银行股这些0值是正常的
            zero_issues.append(f"  {symbol} {col_cn} = 0")

if zero_issues:
    print(f"\n⚠️ 发现零值字段:")
    for z in zero_issues:
        print(z)
else:
    print("✅ 所有字段均非零（银行股行业特性0值除外）")

# 展示关键数据
print("\n关键数据汇总:")
for _, row in df.iterrows():
    symbol = row.iloc[0]
    name = row.iloc[1]
    score = row.get('总分\n(TotalScore)', row.get('总分', 0))
    roe = row.get('ROE(%)(TTM)\n(ROE_TTM)', row.get('ROE(%)(TTM)', 0))
    npr = row.get('净现比\n(OCFtoProfit)', row.get('净现比', 0))
    print(f"  {symbol} {name}: 总分={score}, ROE={roe}, 净现比={npr}")
