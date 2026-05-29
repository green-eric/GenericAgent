# ScoreSys V11.0 因子改造方案

> 基于 scorer.py V10.1 (940行) + config.py (121行) 深度分析
> 生成时间: 2026-05-09

---

## 现状诊断

### 当前权重配置 (config.py V10.1)

| 因子 | 权重 | 月频IC | 状态 |
|------|------|--------|------|
| momentum | 60% | +0.0765 | 最强 |
| industry_momentum | 23% | 良好 | 有效 |
| leverage | 7% | +0.0086 | 微弱正 |
| cash_flow | 5% | -0.0246 | 负IC |
| valuation | 5% | -0.0192 | 负IC |
| growth | 0% | +0.0006 | 零IC |
| profitability | 0% | -0.0256 | 最差 |

### 核心问题

1. **profitability 负IC [-0.0256]** — 评分逻辑与A股实际脱节
   - 当前: ROE高→高分, 毛利率高→高分, 盈利加速→高分
   - 问题: A股中盈利好的公司往往已被充分定价, 未来超额收益为负
   - 根因: 价值因子在A股失效（好公司≠好股票）

2. **cash_flow 负IC [-0.0246]** — 最强逻辑被权重压制
   - 当前权重仅5%, 但现金流质量是A股最稳健alpha来源
   - 问题: 净现比阈值≥1.0过严, A股中位数约0.7

3. **momentum 60%权重过高** — 回撤风险集中
   - 趋势市IC=+0.1653, 震荡市/熊市IC为负
   - crash_sharp反转逻辑(100-mom_score)过于粗暴

4. **valuation 负IC** — 反转逻辑在震荡市失效
   - V9.8反转估值(高PE→高分)在趋势市有效, 震荡市失效
   - PEG: growth为负时peg为负→满分100, 荒谬

5. **growth 零IC** — 营收/利润增速无预测力
   - 阈值过高(净利润增速≥10%满分)导致区分度不足

---

## 改造方向

### P0: profitability 因子重构

**假设**: A股盈利因子负IC = "好公司溢价消失"信号
- 高ROE已被充分定价→未来收益低
- 但ROE趋势(加速度)可能仍有alpha

**方案: ROE趋势替代ROE水平**
```python
# 原逻辑: roe_ttm水平分
roe_score = linear_score(roe_ttm, threshold=15%)

# 新逻辑: ROE变化率（加速度）
roe_delta = roe_ttm - roe_ttm_4q_ago
roe_score = linear_score(roe_delta, threshold=5%)
# ROE提升5%以上→满分, 下降5%以下→0分
```

**备选: 盈利质量替代盈利水平**
```python
# 经营现金流/净利润 替代 ROE
earning_quality = ocf_ttm / net_profit_ttm
# >1.2 → 100分, 0.8~1.2 → 60分, <0.5 → 0分
```

### P0: CashFlow 增强表达

**问题**: 净现比阈值1.0过严

**方案: 阈值调整 + 滚动均值**
```python
# 原: 单季度净现比
# 新: 近4季度净现比均值
npr_4q = mean([npr_q1, npr_q2, npr_q3, npr_q4])
# 阈值: ≥0.8满分(原1.0), ≥0.5及格
score = linear_score(npr_4q, threshold=0.8)
```

### P1: Momentum 降权 + 分化

**方案: 权重上限约束**
```python
# 任何regime下momentum权重不超过40%
momentum_w = min(momentum_w, 0.40)
# 释放的权重分配给cash_flow和reversal
```

**方案: crash反转逻辑平滑化**
```python
# 原: crash_sharp → mom_score = 100 - mom_score (硬反转)
# 新: 线性插值
crash_severity = min(1.0, abs(market_drop_1m) / 0.15)
mom_score = mom_score * (1 - crash_severity) + (100 - mom_score) * crash_severity
```

### P1: Valuation 修复

**方案: PEG修复**
```python
# 原: growth为负时peg<0→满分100 (荒谬)
# 新:
if growth <= 0:
    peg_score = 30  # 无增长→低分
elif pe <= 0:
    peg_score = 5   # 亏损→极低分
else:
    peg = pe / growth
    peg_score = max(0, min(100, 80 - peg * 20))
```

### P2: Growth 复活

**方案: 营收加速度替代增速水平**
```python
# 原: revenue_yoy水平
# 新: 营收增速变化
rev_accel = revenue_yoy_q1 - revenue_yoy_q2
# 加速→高分(成长加速期), 减速→低分(成长见顶)
```

---

## 推荐实施顺序

| 优先级 | 改造项 | 预期IC提升 | 难度 |
|--------|--------|------------|------|
| P0 | profitability→ROE加速度 | +0.015 | 中 |
| P0 | cash_flow净现比阈值+滚动均值 | +0.010 | 低 |
| P1 | momentum权重上限40% | 降风险 | 低 |
| P1 | crash反转平滑化 | +0.005 | 中 |
| P1 | PEG修复 | +0.003 | 低 |
| P2 | 营收加速度 | TBD | 中 |

---

## 预期改造后权重

| 因子 | 当前权重 | 建议权重 | 变化 |
|------|----------|----------|------|
| momentum | 60% | 35% | -25% |
| industry_momentum | 23% | 20% | -3% |
| cash_flow | 5% | 20% | +15% |
| leverage | 7% | 7% | 0 |
| valuation | 5% | 5% | 0 |
| reversal | 0% | 8% | +8% |
| growth | 0% | 5% | +5% |
| profitability | 0% | 0% | 合并入cash_flow |

---

## 待验证假设

1. ROE加速度是否有正IC? → 需回测验证
2. 净现比0.8阈值是否最优? → 可网格搜索
3. momentum权重40%上限是否合理? → 需regime-specific测试
4. cash_flow增强后IC能否转正? → 需回测验证

---

*下一步: 用户确认方向后, 实施P0改造 + 回测验证*
