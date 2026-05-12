import json

# 模拟 percentile_rank 的逻辑
def percentile_rank(value, values, reverse=False):
    """当前代码中的实现"""
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

# 测试场景：4343只股票中，某只股票的roe在pool中的排名
# 假设 pool 有 1653 只机械设备股票
import random
random.seed(42)

# 模拟一个行业pool的roe值
pool_roe = [random.uniform(-5, 30) for _ in range(1653)]
# 某只股票的roe
stock_roe = 15.0

score = percentile_rank(stock_roe, pool_roe)
print(f'roe={stock_roe}, pool_size={len(pool_roe)}, percentile={score:.2f}')

# 测试边界：最大值
max_roe = max(pool_roe)
score_max = percentile_rank(max_roe, pool_roe)
print(f'max_roe={max_roe:.2f}, percentile={score_max:.2f}')

# 测试边界：最小值
min_roe = min(pool_roe)
score_min = percentile_rank(min_roe, pool_roe)
print(f'min_roe={min_roe:.2f}, percentile={score_min:.2f}')

# 测试：当 value 不在 values 中时
# 关键问题：percentile_rank 计算的是 value >= v 的第一个位置
# 但这不是标准的百分位排名！
# 标准应该是：有多少比例的 values <= value

# 正确的百分位排名
def percentile_rank_correct(value, values):
    if not values:
        return 50.0
    n = len(values)
    count_leq = sum(1 for v in values if v <= value)
    return (count_leq / n) * 100

print()
print('=== 正确实现对比 ===')
score_wrong = percentile_rank(stock_roe, pool_roe)
score_right = percentile_rank_correct(stock_roe, pool_roe)
print(f'当前实现: {score_wrong:.2f}')
print(f'正确实现: {score_right:.2f}')

# 测试debt_ratio (reverse=True)
pool_debt = [random.uniform(10, 90) for _ in range(1653)]
stock_debt = 28.62  # 低负债率应该得高分

score_debt_wrong = percentile_rank(stock_debt, pool_debt, reverse=True)
score_debt_right = percentile_rank_correct(stock_debt, pool_debt)
# reverse=True 意味着值越小越好，所以应该是 100 - percentile
print()
print(f'debt_ratio={stock_debt}')
print(f'当前reverse实现: {score_debt_wrong:.2f}')
print(f'正确(100-p): {100 - score_debt_right:.2f}')

# 核心问题分析
print()
print('=== 核心问题 ===')
print('当前 percentile_rank 逻辑:')
print('  sorted_vals = sorted(values, reverse=False)  # 升序')
print('  for i, v in enumerate(sorted_vals):')
print('      if value >= v: return (i / (n-1)) * 100')
print()
print('这意味着：找到第一个 <= value 的位置，返回其索引百分比')
print('这实际上是 "value 超过了多少比例的 pool" 的近似，但有偏差')
print()

# 真正的问题：当 value 等于某个 v 时，返回的是该 v 的索引位置
# 而不是 "有多少比例的 values <= value"
# 这会导致系统性偏差

# 更关键的：检查实际数据
with open(r'D:\Project\AnnualScorer\股票分析数据_20260426_133556.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

stocks = data['stocks']
success = [s for s in stocks if s.get('fetch_success')]

# 取通源石油(300164.SZ)看看
target = [s for s in success if s['ts_code'] == '300164.SZ'][0]
print(f"=== 通源石油(300164.SZ) ===")
print(f"roe={target.get('roe')}, gross={target.get('gross_margin')}, net={target.get('net_margin')}")
print(f"rev_yoy={target.get('revenue_yoy')}, prof_yoy={target.get('profit_yoy')}")
print(f"debt={target.get('debt_ratio')}, ocf={target.get('ocf_to_profit')}")
print()

# 找出它的行业(pool)
ind = target.get('industry_l1', '')
pool = [s for s in success if s.get('industry_l1') == ind]
print(f"行业: {ind}, pool_size: {len(pool)}")

# 手动计算 roe 百分位
pool_roe_vals = [s['roe'] for s in pool if s.get('roe') is not None and s['ts_code'] != '300164.SZ']
target_roe = target.get('roe')
print(f"target_roe={target_roe}, pool_roe count={len(pool_roe_vals)}")
if pool_roe_vals and target_roe is not None:
    score_wrong = percentile_rank(target_roe, pool_roe_vals)
    score_right = percentile_rank_correct(target_roe, pool_roe_vals)
    print(f"roe 百分位(当前): {score_wrong:.2f}")
    print(f"roe 百分位(正确): {score_right:.2f}")

# 手动计算 gross_margin 百分位
pool_gross = [s['gross_margin'] for s in pool if s.get('gross_margin') is not None and s['ts_code'] != '300164.SZ']
target_gross = target.get('gross_margin')
if pool_gross and target_gross is not None:
    score_wrong = percentile_rank(target_gross, pool_gross)
    score_right = percentile_rank_correct(target_gross, pool_gross)
    print(f"gross 百分位(当前): {score_wrong:.2f}")
    print(f"gross 百分位(正确): {score_right:.2f}")

# 手动计算 debt_ratio 百分位 (reverse=True, 越低越好)
pool_debt = [s['debt_ratio'] for s in pool if s.get('debt_ratio') is not None and s['ts_code'] != '300164.SZ']
target_debt = target.get('debt_ratio')
if pool_debt and target_debt is not None:
    score_wrong = percentile_rank(target_debt, pool_debt, reverse=True)
    score_right = percentile_rank_correct(target_debt, pool_debt)
    print(f"debt 百分位(当前,reverse): {score_wrong:.2f}")
    print(f"debt 百分位(正确,100-p): {100 - score_right:.2f}")
