# R70 — ScoreSys 权重优化器 V1.3 全Regime混入

**日期**: 2026-05-08 | **类型**: 产出

---

## 背景

V1.2 引入全周期地板混入（30%全周期权重 + 70% regime权重），但仅对 `trending` 生效。2024回测区间3个调仓期仅1个是trending → 零效果。

## 根因

`weight_optimizer.py` `get_regime_weights()` 中混入逻辑被 `if regime.startswith('trending')` 包裹，choppy/low_vol 未混入。

## 修复（V1.3）

移除 `trending` 条件限制，所有 regime 统一混入 30% 全周期地板：

```python
# V1.2: 仅 trending 混入
if regime.startswith('trending'):
    blend_ratio = 0.30
    ...

# V1.3: 全 regime 混入
blend_ratio = 0.30
blended = {}
for f in FULL_CYCLE_FACTORS:
    blended[f] = (1 - blend_ratio) * regime_w[f] + blend_ratio * fc_w[f]
```

## 权重变化

| Regime | 主要变化 |
|--------|---------|
| choppy | 行业动量 7.8%→11.0% (+3.2pp), 现金流 57%→54.4% (-2.6pp) |
| low_vol | 同 choppy |
| trending_bull | 动量 40.3%→30.2% (-10.1pp), 现金流 21.8%→29.8% (+8.0pp) |

## 回测结果

| 版本 | avg_IC | IC列表 |
|------|--------|--------|
| V1.1 基线 | -0.1037 | [-0.0404, -0.2446, -0.0254] |
| V1.2 (仅trending) | -0.1037 | 同上（零效果） |
| V1.3 (全regime) | **-0.0972** | [+0.0763, -0.2338, -0.1340] |

- avg_IC 提升 6.3%
- T1 翻正：-0.0404 → +0.0763
- T2 微改善但仍是负值主源（系统性下跌，权重优化天花板）

## 改动文件

- `D:/Project/ScoreSys/weight_optimizer.py` — 移除 trending 条件限制
- `D:/Project/ScoreSys/README.md` — 新增权重优化器V1.3完整章节（~130行）