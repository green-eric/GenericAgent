import pandas as pd

# 读取最新的Excel报告
excel_path = r"C:\Users\green\Desktop\股票业绩评价_20260424_2134_真实列表.xlsx"
df = pd.read_excel(excel_path, sheet_name='综合评价结果')

print("=== 调试信息 ===")
print(f"总股票数: {len(df)}")

# 检查前几行数据
print("\n=== 前5行数据 ===")
for i in range(min(5, len(df))):
    row = df.iloc[i]
    print(f"{i+1}. {row['股票名称']}({row['股票代码']}) - 行业: '{row['行业']}'")

# 检查是否有非"其他"的行业
non_other = df[df['行业'] != '其他']
if len(non_other) > 0:
    print(f"\n找到 {len(non_other)} 只非'其他'行业的股票:")
    for _, row in non_other.head(10).iterrows():
        print(f"  {row['股票名称']}({row['股票代码']}) - 行业: {row['行业']}")
else:
    print("\n没有找到非'其他'行业的股票")

# 检查行业列的实际内容
print(f"\n=== 行业列唯一值 ===")
unique_industries = df['行业'].unique()
for industry in unique_industries:
    count = len(df[df['行业'] == industry])
    print(f"'{industry}': {count}只")