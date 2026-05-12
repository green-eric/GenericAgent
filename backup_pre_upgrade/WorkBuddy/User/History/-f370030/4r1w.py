import pandas as pd

# 读取最新的Excel报告
excel_path = r"C:\Users\green\Desktop\股票业绩评价_20260424_2133_真实列表.xlsx"
df = pd.read_excel(excel_path, sheet_name='综合评价结果')

print("=== 行业分布分析 ===")
print(f"总股票数: {len(df)}")

# 显示行业分布
if '行业' in df.columns:
    industry_counts = df['行业'].value_counts()
    print("\n=== 各行业股票数量 ===")
    for industry, count in industry_counts.items():
        percentage = count / len(df) * 100
        print(f"{industry}: {count}只 ({percentage:.1f}%)")

    # 显示前几个行业的详细股票
    top_industries = industry_counts.head(5)
    print(f"\n=== 前5个行业详细股票 ===")
    for industry in top_industries.index:
        industry_stocks = df[df['行业'] == industry].head(3)
        print(f"\n{industry} (共{top_industries[industry]}只):")
        for _, row in industry_stocks.iterrows():
            print(f"  {row['股票名称']}({row['股票代码']}) - 评分: {row['总评分']}")

else:
    print("没有找到'行业'列")

print(f"\n=== 数据列名 ===")
for col in df.columns:
    print(f"'{col}'")