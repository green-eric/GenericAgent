# R77 - ScoreSys 因子层面改造分析报告

> 自动生成 @ 2026-05-09 | 基于 R65/R70 回测结论 + 代码结构分析

---

## 📌 背景与动机

**R65/R70 核心结论**：权重优化对 IC 几乎无影响（各因子相关性高，权重微调不改变排序）
→ **必须从因子层面改造**，而非权重层面

---

## 🔍 现有架构分析

### 因子计算链路
```
原始数据 → calculator.py (指标计算) → scorer.py (评分) → backtest.py (回测)
```

### 当前 7 因子 (config.py)
| 因子 | 权重 | 方向 | 问题 |
|------|------|------|------|
| momentum | 0.25 | 正向 | ⚠️ 震荡市失效 |
| growth | 0.15 | 正向 | 正常 |
| valuation | 0.10 | 反向 | 正常 |
| profitability | 0.15 | 正向 | ❌ 持续负IC |
| cash_flow | 0.20 | 正向 | ✅ 全周期最强 |
| leverage | 0.10 | 反向 | 正常 |
| industry_momentum | 0.05 | 正向 | V9.3新增 |

---

## 🎯 改造方案 (3个方向)

### 方向①：Momentum → Regime-Specific 变体

**问题**：动量因子在趋势市有效，震荡市反转
**方案**：
```python
# 新增市场状态检测
def detect_regime(returns_60d):
    """基于60日波动率+趋势强度判断市场状态"""
    volatility = returns_60d.std()
    trend_strength = abs(returns_60d.mean()) / volatility
    if trend_strength > 0.5:
        return 'trending'      # 趋势市 → 标准动量
    else:
        return 'mean_reverting' # 震荡市 → 反转动量

# Momentum评分改为
if regime == 'trending':
    score = standard_momentum
else:
    score = -standard_momentum  # 反转
```

**预期收益**：震荡市 IC 从负转正，整体 IC 提升 15-25%

### 方向②：Cash Flow 增强表达

**发现**：cash_flow 全周期最强，但当前仅用经营现金流/总资产
**方案**：增加子维度
```python
cash_flow_score = (
    0.4 * operating_cf_to_asset +    # 现有
    0.3 * fcf_yield +                 # 新增：自由现金流收益率
    0.3 * cf_consistency               # 新增：现金流稳定性(4季标准差倒数)
)
```

**预期收益**：强化最强因子，IC 提升 5-10%

### 方向③：Profitability 反转或替换

**问题**：profitability 持续负IC（可能与A股壳价值有关）
**方案A**：反转信号
```python
# 低盈利 → 高评分（反转）
profitability_score = -rank(current_score)
```

**方案B**：替换为质量因子
```python
# 用 ROE 变化率替代 ROE 水平
quality_score = roe_change_4q = roe_t - roe_t_4q_ago
```

**预期收益**：消除负贡献，IC 提升 10-15%

---

## 📊 预期综合效果

| 改造 | 当前avgIC | 预期avgIC | 提升 |
|------|-----------|-----------|------|
| 基准(V10.0) | ~0.045 | - | - |
| +Momentum regime | - | ~0.052 | +15% |
| +CashFlow增强 | - | ~0.055 | +7% |
| +Profitability修复 | - | ~0.060 | +10% |
| **全部应用** | - | **~0.060** | **+33%** |

---

## 🛠️ 实施优先级

1. **P0**：Momentum regime-specific（影响最大，代码改动小）
2. **P1**：Profitability 反转（立即消除负贡献）
3. **P2**：CashFlow 增强（锦上添花）

---

## ⚠️ 风险提示

- Regime检测需要额外参数调优（阈值0.5需验证）
- 反转策略在A股小盘壳价值环境中可能过拟合
- 建议先做分组回测验证单调性，再做完整IC回测

---

*报告由自主智能体生成，待用户审核后实施*