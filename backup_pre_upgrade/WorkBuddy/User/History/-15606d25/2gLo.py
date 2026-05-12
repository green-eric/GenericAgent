import json
from collections import Counter

with open(r'D:\Project\AnnualScorer\股票分析数据_20260426_133556.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

stocks = data['stocks']
print(f'总股票数: {len(stocks)}')
print(f'成功获取: {sum(1 for s in stocks if s.get("fetch_success"))}')
print(f'获取失败: {sum(1 for s in stocks if not s.get("fetch_success"))}')
print()

grade_dist = Counter(s.get('grade','?') for s in stocks)
print('评级分布:', dict(sorted(grade_dist.items())))
print()

# 选3只: A级高分1只、B级1只、失败1只
a_stocks = [s for s in stocks if s.get('grade') == 'A' and s.get('fetch_success')]
b_stocks = [s for s in stocks if s.get('grade') == 'B' and s.get('fetch_success')]
fail_stocks = [s for s in stocks if not s.get('fetch_success')]

for label, pool in [('A级样本', a_stocks), ('B级样本', b_stocks), ('失败样本', fail_stocks)]:
    print(f'=== {label} (共{len(pool)}只, 取第1只) ===')
    if pool:
        s = pool[0]
        for k,v in s.items():
            print(f'  {k}: {v}')
    print()
