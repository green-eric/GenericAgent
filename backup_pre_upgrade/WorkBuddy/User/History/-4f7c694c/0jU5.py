import json

with open(r'D:\Project\AnnualScorer\股票分析数据_20260426_133556.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

stocks = data['stocks']
success = [s for s in stocks if s.get('fetch_success')]

# 定义正确的 percentile_rank
def percentile_rank_correct(value, values):
    if not values:
        return 50.0
    n = len(values)
    count_leq = sum(1 for v in values if v <= value)
    return (count_leq / n) * 100

# 定义当前的 percentile_rank（有bug）
def percentile_rank_wrong(value, values, reverse=False):
    if not values:
        return 50.0
    sorted_vals = sorted(values, reverse=reverse)
    n = len(sorted_vals)
    if n == 1:
        ref = sorted_vals[0]
        return 100.0 if value >= ref else 0.0
    for i, v in enumerate(sorted_vals):
        if value >= v:
            return (i / (n - 1)) * 100
    return 0.0

# 取几个样本股票
samples = [
    ('300164.SZ', '通源石油'),
    ('002546.SZ', '新联电子'),
    ('601997.SH', '贵阳银行'),
    ('300590.SZ', '移为通信'),
]

for ts_code, name in samples:
    stock = [s for s in success if s['ts_code'] == ts_code][0]
    ind = stock.get('industry_l1', '')
    pool = [s for s in success if s.get('industry_l1') == ind and s['ts_code'] != ts_code]

    print(f'=== {ts_code} {name} ===')
    print(f'行业: {ind}, pool大小: {len(pool)}')

    # 获取各指标值和pool
    def get_pool_values(key):
        return [s[key] for s in pool if s.get(key) is not None]

    roe_vals = get_pool_values('roe')
    gross_vals = get_pool_values('gross_margin')
    net_vals = get_pool_values('net_margin')
    rev_vals = get_pool_values('revenue_yoy')
    prof_vals = get_pool_values('profit_yoy')
    debt_vals = get_pool_values('debt_ratio')
    ocf_vals = get_pool_values('ocf_to_profit')

    metrics = {
        'roe': stock.get('roe'), 'gross_margin': stock.get('gross_margin'),
        'net_margin': stock.get('net_margin'), 'revenue_yoy': stock.get('revenue_yoy'),
        'profit_yoy': stock.get('profit_yoy'), 'debt_ratio': stock.get('debt_ratio'),
        'ocf_to_profit': stock.get('ocf_to_profit')
    }

    scores = {}
    for metric, vals in zip(['roe', 'gross_margin', 'net_margin', 'revenue_yoy', 'profit_yoy', 'debt_ratio', 'ocf_to_profit'],
                            [roe_vals, gross_vals, net_vals, rev_vals, prof_vals, debt_vals, ocf_vals]):
        val = metrics[metric]
        if val is not None and vals:
            wrong = percentile_rank_wrong(val, vals)
            correct = percentile_rank_correct(val, vals)
            scores[metric] = {'val': val, 'wrong': wrong, 'correct': correct}
            print(f'{metric}: {val} -> 当前:{wrong:.2f} 正确:{correct:.2f}')
        else:
            scores[metric] = {'val': val, 'wrong': 0.0, 'correct': 0.0}

    # 计算 profit_score (盈利能力)
    roe_score = scores['roe']['correct'] if scores['roe']['val'] is not None else 0.0
    gross_score = scores['gross_margin']['correct'] if scores['gross_margin']['val'] is not None else 0.0
    net_score = scores['net_margin']['correct'] if scores['net_margin']['val'] is not None else 0.0
    profit_score = round(roe_score * 0.4 + gross_score * 0.3 + net_score * 0.3, 2)

    # growth_score (成长性)
    rev_score = scores['revenue_yoy']['correct'] if scores['revenue_yoy']['val'] is not None else 0.0
    prof_score = scores['profit_yoy']['correct'] if scores['profit_yoy']['val'] is not None else 0.0
    growth_score = round(rev_score * 0.4 + prof_score * 0.6, 2)

    # ocf_score (现金流质量)
    ocf_score = scores['ocf_to_profit']['correct'] if scores['ocf_to_profit']['val'] is not None else 0.0

    # debt_score (偿债风险, 越低越好)
    debt_score = scores['debt_ratio']['correct'] if scores['debt_ratio']['val'] is not None else 0.0

    total_score = round(profit_score * 0.35 + growth_score * 0.30 + ocf_score * 0.15 + debt_score * 0.20, 2)
    grade = 'A' if total_score >= 75 else 'B' if total_score >= 55 else 'C' if total_score >= 40 else 'D' if total_score >= 25 else 'E'

    print(f'profit_score={profit_score}, growth_score={growth_score}, ocf_score={ocf_score}, debt_score={debt_score}')
    print(f'total_score={total_score}, grade={grade}')
    print()