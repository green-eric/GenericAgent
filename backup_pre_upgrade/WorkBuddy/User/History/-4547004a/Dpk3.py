import json
from collections import Counter

with open(r'D:\Project\AnnualScorer\股票分析数据_20260426_133556.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

stocks = data['stocks']

# 1. 检查 fetch_success 和评分的关系
success = [s for s in stocks if s.get('fetch_success')]
failed = [s for s in stocks if not s.get('fetch_success')]
print(f'成功: {len(success)}, 失败: {len(failed)}')

# 2. 成功的股票评级分布
grade_s = Counter(s.get('grade','?') for s in success)
print(f'成功股票评级分布: {dict(sorted(grade_s.items()))}')

# 3. 成功的股票中，总分范围
scores = [s.get('total_score', 0) for s in success]
if scores:
    print(f'成功股票总分: min={min(scores):.2f}, max={max(scores):.2f}, avg={sum(scores)/len(scores):.2f}')

# 4. 检查completeness
comp_levels = Counter(s.get('completeness_level','?') for s in success)
print(f'成功股票完整度分布: {dict(sorted(comp_levels.items()))}')

# 5. 取总分最高的5只股票看看
top5 = sorted(success, key=lambda x: x.get('total_score',0), reverse=True)[:5]
print()
print('=== 总分最高的5只 ===')
for s in top5:
    print(f"  {s['ts_code']} {s['name']} 总分={s.get('total_score',0):.2f} 评级={s.get('grade','?')} 完整度={s.get('completeness_level','?')}")
    print(f"    roe={s.get('roe')} gross={s.get('gross_margin')} net={s.get('net_margin')} rev_yoy={s.get('revenue_yoy')} prof_yoy={s.get('profit_yoy')} debt={s.get('debt_ratio')} ocf={s.get('ocf_to_profit')}")
    print(f"    profit_score={s.get('profit_score',0):.2f} growth_score={s.get('growth_score',0):.2f} ocf_score={s.get('ocf_score',0):.2f} debt_score={s.get('debt_score',0):.2f}")
    print()

# 6. 检查行业分组
industries = Counter(s.get('industry_l1','未知') for s in success)
print(f'行业分布 (top10): {dict(industries.most_common(10))}')

# 7. 行业样本数分布
ind_sizes = Counter(len([x for x in success if x.get('industry_l1') == ind]) for ind in set(s.get('industry_l1','未知') for s in success))
print(f'行业样本数分布: {dict(sorted(ind_sizes.items()))}')

# 8. 检查market_fallback比例
fallback = sum(1 for s in success if s.get('market_fallback'))
print(f'使用市场基准(fallback): {fallback}/{len(success)}')

# 9. 检查roe为None的比例
roe_none = sum(1 for s in success if s.get('roe') is None)
rev_none = sum(1 for s in success if s.get('revenue_yoy') is None)
print(f'roe为None: {roe_none}/{len(success)}, revenue_yoy为None: {rev_none}/{len(success)}')
