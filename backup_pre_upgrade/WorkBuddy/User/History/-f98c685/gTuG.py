import json

with open(r'c:\Users\green\WorkBuddy\20260424203734\workplace\股票分析数据_20260426_000332.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

print("=== 数据质量验证 ===")
print(f"data_timestamp: {d.get('data_timestamp')}")
print(f"total_stocks: {d.get('total_stocks')}")

stocks = d.get('stocks', [])
null_profit = sum(1 for s in stocks if s.get('annual_net_profit') is None)
has_ocf = sum(1 for s in stocks if s.get('annual_ocf_to_profit'))
has_date = sum(1 for s in stocks if s.get('annual_report_date'))
has_industry = sum(1 for s in stocks if s.get('industry_level1'))

print(f"\nannual_net_profit 为 null: {null_profit} / {len(stocks)}")
print(f"annual_ocf_to_profit 有值: {has_ocf} / {len(stocks)}")
print(f"annual_report_date 有值: {has_date} / {len(stocks)}")
print(f"industry_level1 有值: {has_industry} / {len(stocks)}")

# 找几个有数据的样本
print("\n=== 样本检查（前3只）===")
for s in stocks[:3]:
    print(f"\n{s.get('name')} ({s.get('ts_code','')})")
    print(f"  年报日期: {s.get('annual_report_date')}")
    print(f"  净利润: {s.get('annual_net_profit')}")
    print(f"  经营现金流/净利润: {s.get('annual_ocf_to_profit')}")
    print(f"  ROE: {s.get('roe')}")
    print(f"  毛利率: {s.get('gross_margin')}")
    print(f"  行业: {s.get('industry_level1')}")

# 评级分布
grades = {}
for s in stocks:
    g = s.get('grade', 'N/A')
    grades[g] = grades.get(g, 0) + 1
print(f"\n=== 评级分布 ===")
for g in sorted(grades.keys()):
    print(f"  {g}: {grades[g]}")
