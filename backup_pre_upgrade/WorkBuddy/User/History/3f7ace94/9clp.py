import pandas as pd

# 读取Excel报告
excel_path = r"C:\Users\green\Desktop\股票业绩评价_20260424_2129_真实列表.xlsx"
df = pd.read_excel(excel_path, sheet_name='综合评价结果')

print("=== 行业分布分析 ===")
print(f"总股票数: {len(df)}")

# 显示前几列来了解数据结构
print("\n=== 数据列名 ===")
for col in df.columns:
    print(col)

print("\n=== 前5行数据预览 ===")
print(df.head())

print("\n=== 行业分类统计 ===")
if '行业' in df.columns:
    industry_counts = df['行业'].value_counts()
    print(industry_counts)
else:
    print("没有找到'行业'列，检查实际列名...")

print("\n=== 股票代码和名称示例 ===")
print(df[['ts_code', 'name']].head(10))