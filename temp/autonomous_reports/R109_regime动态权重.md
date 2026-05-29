# R109 | 2026-05-14 | 实现 | Regime动态权重方案

## 摘要
基于regime_ic.json的per-regime IC数据，用IC²加权+full_cycle混合算法，替代现有的硬编码权重覆盖逻辑。**关键发现：不同regime下最优因子权重差异巨大（crash_sharp中reversal占47%，choppy中cash_flow占39%）。**

## 算法设计

```
blended_IC = (1 - blend) × regime_IC + blend × full_cycle_IC    (blend=0.30)
raw_weight = IC²_smooth × (1 + ir_bonus)    if IC > 0
raw_weight = |IC|²_smooth × 0.05            if IC ≤ 0
→ clip(min_weight=0.02, max_weight=0.40) → 归一化
```

## 6个Regime动态权重结果

### full_cycle（全周期基准）
| 因子 | IC | 权重 |
|------|-----|------|
| industry_momentum | +0.0881 | 0.338 |
| alpha_023 | +0.0657 | 0.188 |
| momentum | +0.0556 | 0.135 |
| valuation | +0.0498 | 0.108 |
| alpha_momentum | +0.0350 | 0.053 |

### trending（趋势行情）
| 因子 | IC | 权重 |
|------|-----|------|
| industry_momentum | +0.0808 | 0.342 |
| alpha_023 | +0.0740 | 0.254 |
| valuation | +0.0448 | 0.106 |
| alpha_momentum | +0.0423 | 0.080 |
**vs full_cycle: momentum↓0.116, alpha_023↑0.066**

### choppy（震荡行情）
| 因子 | IC | 权重 |
|------|-----|------|
| cash_flow | +0.2588 | 0.386 |
| momentum | +0.1316 | 0.182 |
| valuation | +0.1281 | 0.169 |
| turnover | +0.0759 | 0.057 |
**vs full_cycle: cash_flow↑0.367, industry_momentum↓0.318**

### crash_sharp（急跌行情）
| 因子 | IC | 权重 |
|------|-----|------|
| reversal | +0.1176 | 0.472 |
| alpha_rsi | +0.0320 | 0.101 |
| alpha_momentum | +0.0250 | 0.095 |
**vs full_cycle: reversal↑0.453, industry_momentum↓0.315**

### crash_slow（阴跌行情）
| 因子 | IC | 权重 |
|------|-----|------|
| profitability | +0.2177 | 0.367 |
| industry_momentum | +0.1482 | 0.266 |
| growth | +0.1487 | 0.146 |
**vs full_cycle: profitability↑0.348, growth↑0.128**

### low_vol（低波行情）
| 因子 | IC | 权重 |
|------|-----|------|
| profitability | +0.1438 | 0.390 |
| reversal | +0.1145 | 0.247 |
| alpha_023 | +0.0550 | 0.141 |
**vs full_cycle: profitability↑0.372, reversal↑0.229**

## 关键洞察

1. **reversal是危机alpha** — crash_sharp中占47%权重，但在trending中几乎为0
2. **cash_flow在震荡市中王者** — choppy中占39%（IC=+0.2588）
3. **profitability在阴跌/低波中核心** — crash_slow中37%，low_vol中39%
4. **industry_momentum在趋势中不可替代** — trending中34%
5. **alpha_023在趋势/低波中有效** — trending中25%，但权重偏高（IC仅0.0657），建议regime下调至10%

## 实现状态
- [x] 算法设计完成
- [x] 6个regime权重计算完成
- [ ] 写入ScoreSys代码（需替换scorer.py中硬编码逻辑）
- [ ] 回测验证
