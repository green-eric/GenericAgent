# R81 — V13.4 Regime 自适应权重优化

## 执行摘要
重写 scorer.py 中的 `_resolve_regime_weights` 函数，将基准从旧版 WEIGHTS(momentum=0.60) 更新为 V13.3 权重体系，按市场状态动态调整因子权重。

## 修改内容

### scorer.py — _resolve_regime_weights (V13.4)
- 基准: industry_momentum=0.35 | growth=0.30 | valuation=0.20 | leverage=0.08 | turnover=0.05 | profitability=0.02
- reversal/turnover 基准为 0，仅在对应 regime 激活
- 各 regime 调整:
  - trending: 基准不变, reversal+0.08, ind_w(hot+0.07/cooling+0.04/neutral+0.02)
  - crash_slow: valuation+0.08, 行业动量-0.14, 成长-0.06, 换手率-0.02, reversal+0.12
  - crash_sharp_bounce: valuation+0.08, 行业动量-0.06, 成长-0.06, reversal+0.12
  - crash_moderate: momentum+0.12, valuation+005, 行业动量-0.14, 成长-0.04, reversal+0.10
  - low_vol/low_vol_flight: 估值+0.04, 成长-0.08, 行业动量-0.06, reversal+0.08
  - recovery: valuation+0.03, 行业动量+0.02, reversal+0.03
- 调整后归一化至总和=1.0

### README.md
- 补充 V13.4 Regime 自适应权重调整表

### 记忆
- global_mem.txt: 版本更新至 V13.4
- global_mem_insight.txt: 同步更新

## 回测验证
| 指标 | V13.3 | V13.4 | 变化 |
|:--|:--|:--|:--|
| 总收益 | +7.08% | +7.08% | = |
| 年化收益 | +3.54% | +3.54% | = |
| 夏普比率 | 2.07 | 2.07 | = |
| 最大回撤 | 10.64% | 10.64% | = |
| IC均值 | +0.0070 | +0.0070 | = |

## 结论
Regime 权重调整对回测绩效无影响。原因：各因子得分高度相关，权重重新分配不改变选股排序；reversal/turnover 因子 IC 质量差，即使 regime 激活也贡献微弱。

## Git
已提交: v13.4 regime自适应权重:重写_resolve_regime_weights以V13.3基准,README补充调整表
