import json

with open(r'c:\Users\green\WorkBuddy\20260424203734\workplace\股票分析数据_20260426_000332.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

stocks = d.get('stocks', [])
n = len(stocks)

print("=== 数据质量验证 ===")
print(f"data_timestamp: {d.get('data_timestamp')}")
print(f"total_stocks: {d.get('total_stocks')}")

null_profit = sum(1 for s in stocks if s.get('annual_net_profit') is None)
has_ocf = sum(1 for s in stocks if s.get('annual_ocf_to_profit'))
has_date = sum(1 for s in stocks if s.get('annual_report_date'))
has_industry = sum(1 for s in stocks if s.get('industry_l1'))
has_rating = sum(1 for s in stocks if s.get('rating') and s.get('rating') != 'N/A')
has_score = sum(1 for s in stocks if s.get('total_score'))

print(f"\nannual_net_profit 为 null: {null_profit}/{n} ({null_profit/n*100:.1f}%)")
print(f"annual_ocf_to_profit 有值: {has_ocf}/{n} ({has_ocf/n*100:.1f}%)")
print(f"annual_report_date 有值: {has_date}/{n} ({has_date/n*100:.1f}%)")
print(f"industry_l1 有值: {has_industry}/{n} ({has_industry/n*100:.1f}%)")
print(f"rating 有值: {has_rating}/{n} ({has_rating/n*100:.1f}%)")
print(f"total_score 有值: {has_score}/{n} ({has_score/n*100:.1f}%)")

# 评级分布
grades = {}
for s in stocks:
    g = s.get('rating', 'N/A')
    grades[g] = grades.get(g, 0) + 1
print(f"\n=== 评级分布 ===")
for g in sorted(grades.keys(), key=lambda x: (x!='S', x!='A', x!='B', x!='C', x!='D', x)):
    print(f"  {g}: {grades[g]} ({grades[g]/n*100:.1f}%)")

# 行业分布 top10
industries = {}
for s in stocks:
    ind = s.get('industry_l1', '未知')
    industries[ind] = industries.get(ind, 0) + 1
print(f"\n=== 行业分布 Top10 ===")
for ind, cnt in sorted(industries.items(), key=lambda x: -x[1])[:10]:
    print(f"  {ind}: {cnt}")

# 净利润为null的原因分析
print(f"\n=== 净利润null样本（前5只）===")
null_stocks = [s for s in stocks if s.get('annual_net_profit') is None]
for s in null_stocks[:5]:
    print(f"  {s.get('name')} ({s.get('ts_code')}) | fetch_success={s.get('fetch_success')} | report_date={s.get('annual_report_date')}")

# 评分最高/最低
print(f"\n=== 评分最高 Top5 ===")
scored = sorted([s for s in stocks if s.get('total_score')], key=lambda x: -x['total_score'])
for s in scored[:5]:
    print(f"  {s['name']} ({s['ts_code']}): {s['total_score']:.1f}分 | {s['rating']} | 行业:{s.get('industry_l1')}")

print(f"\n=== 评分最低 Top5 ===")
for s in scored[-5:]:
    print(f"  {s['name']} ({s['ts_code']}): {s['total_score']:.1f}分 | {s['rating']} | 行业:{s.get('industry_l1')}")
