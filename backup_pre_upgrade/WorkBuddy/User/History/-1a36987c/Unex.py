import json

with open(r'D:\Project\AnnualScorer\股票分析数据_20260426_133556.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

stocks = data['stocks']
success = [s for s in stocks if s.get('fetch_success')]

# 取通源石油(300164.SZ) - 总分最高的
target = [s for s in success if s['ts_code'] == '300164.SZ'][0]
ind = target.get('industry_l1', '')
pool = [s for s in success if s.get('industry_l1') == ind]

print(f"目标: {target['ts_code']} {target['name']}")
print(f"行业: {ind}, pool大小: {len(pool)}")
print(f"roe={target.get('roe')}, gross={target.get('gross_margin')}, net={target.get('net_margin')}")
print(f"rev_yoy={target.get('revenue_yoy')}, prof_yoy={target.get('profit_yoy')}")
print(f"debt={target.get('debt_ratio')}, ocf={target.get('ocf_to_profit')}")
print()

# 检查 pool_values
def pool_values(key):
    return [s[key] for s in pool if s.get("ts_code") != "300164.SZ" and s.get(key) is not None]

roe_vals = pool_values('roe')
gross_vals = pool_values('gross_margin')
net_vals = pool_values('net_margin')
rev_vals = pool_values('revenue_yoy')
prof_vals = pool_values('profit_yoy')
debt_vals = pool_values('debt_ratio')
ocf_vals = pool_values('ocf_to_profit')

print(f"pool roe: count={len(roe_vals)}, min={min(roe_vals) if roe_vals else 'N/A'}, max={max(roe_vals) if roe_vals else 'N/A'}")
print(f"pool gross: count={len(gross_vals)}, min={min(gross_vals) if gross_vals else 'N/A'}, max={max(gross_vals) if gross_vals else 'N/A'}")
print(f"pool net: count={len(net_vals)}, min={min(net_vals) if net_vals else 'N/A'}, max={max(net_vals) if net_vals else 'N/A'}")
print(f"pool rev_yoy: count={len(rev_vals)}, min={min(rev_vals) if rev_vals else 'N/A'}, max={max(rev_vals) if rev_vals else 'N/A'}")
print()

# 手动计算 percentile_rank
def percentile_rank(value, values, reverse=False):
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

# 计算 roe_score
target_roe = target.get('roe')
if target_roe is not None and roe_vals:
    roe_score = 0.0 if target_roe < 0 else percentile_rank(target_roe, roe_vals)
    print(f"roe_score: roe={target_roe}, score={roe_score:.2f}")
    
    # 详细追踪
    sorted_roe = sorted(roe_vals)
    n = len(sorted_roe)
    print(f"  sorted_roe: n={n}, min={sorted_roe[0]:.2f}, max={sorted_roe[-1]:.2f}")
    print(f"  target_roe={target_roe}")
    
    # 找第一个 <= target_roe 的位置
    for i, v in enumerate(sorted_roe):
        if target_roe >= v:
            print(f"  first match at i={i}, v={v:.2f}, score={(i/(n-1))*100:.2f}")
            break
    
    # 有多少 roe_vals <= target_roe
    count_leq = sum(1 for v in roe_vals if v <= target_roe)
    print(f"  count <= target: {count_leq}/{n} = {count_leq/n*100:.2f}%")

# 计算 gross_score
target_gross = target.get('gross_margin')
if target_gross is not None and gross_vals:
    gross_score = percentile_rank(target_gross, gross_vals)
    print(f"\ngross_score: gross={target_gross}, score={gross_score:.2f}")
    sorted_gross = sorted(gross_vals)
    n = len(sorted_gross)
    for i, v in enumerate(sorted_gross):
        if target_gross >= v:
            print(f"  first match at i={i}, v={v:.2f}, score={(i/(n-1))*100:.2f}")
            break

# 计算 net_score
target_net = target.get('net_margin')
if target_net is not None and net_vals:
    net_score = percentile_rank(target_net, net_vals)
    print(f"\nnet_score: net={target_net}, score={net_score:.2f}")

# profit_score = roe_score * 0.4 + gross_score * 0.3 + net_score * 0.3
# 如果三个都是0，那profit_score就是0

# 关键：看看有多少股票的 profit_score/growth_score/ocf_score 是 0
zero_profit = sum(1 for s in success if s.get('profit_score', 0) == 0)
zero_growth = sum(1 for s in success if s.get('growth_score', 0) == 0)
zero_ocf = sum(1 for s in success if s.get('ocf_score', 0) == 0)
zero_debt = sum(1 for s in success if s.get('debt_score', 0) == 0)
print(f"\n=== 零分统计 ===")
print(f"profit_score=0: {zero_profit}/{len(success)}")
print(f"growth_score=0: {zero_growth}/{len(success)}")
print(f"ocf_score=0: {zero_ocf}/{len(success)}")
print(f"debt_score=0: {zero_debt}/{len(success)}")

# 看看debt_score的分布
debt_scores = [s.get('debt_score', 0) for s in success]
print(f"\ndebt_score: min={min(debt_scores):.2f}, max={max(debt_scores):.2f}, avg={sum(debt_scores)/len(debt_scores):.2f}")
