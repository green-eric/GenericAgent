# R296 — 动量加速度+偏度因子调研

> 自主行动 | 2026-05-28 | TODO #3

## 1. 调研结论（TL;DR）

| 因子 | 现有状态 | 建议 |
|------|---------|------|
| 动量加速度 (acceleration) | ✅ AccelerationScorer 已实现，但 **config 权重未配置** | P0: 直接配置权重后回测验证 |
| 收益偏度 (skewness) | ❌ SkewnessScorer 不存在，需全新开发 | P1: 实现后回测验证 |

---

## 2. 动量加速度因子

### 2.1 现有实现

`AccelerationScorer` 已在 `factors/scorers.py:1218` 中实现：

```python
公式: acceleration = 当前5日收益 - 前5日收益
     (close[-1]/close[-6] - 1) - (close[-6]/close[-11] - 1)
方向: positive（加速度为正 → 动能增强 → 看涨）
数据要求: 至少 11 日 close
```

### 2.2 互补性分析

| 现有因子 | 信号类型 | 加速度补充 |
|----------|---------|-----------|
| `alpha_momentum` | 价格动量方向（趋势） | 加速度衡量动量**变化率**，提前捕捉趋势加速/减速 |
| `reversal` | 反转信号 | 加速度可区分"动量延续"vs"动量衰竭→反转" |
| `alpha_rsi` | 超买超卖 | 加速度在 RSI 极端区域提供方向确认 |

**核心价值**：momentum 告诉你在涨/跌，acceleration 告诉你涨/跌的**速度在加快还是减慢**。这是二阶信息，与一阶动量天然互补。

### 2.3 配置状态

❌ **未配置进 `weights_short_term`**。当前 short_term 共 15 个因子，不含 acceleration。

### 2.4 建议步骤

1. 在 `config.yaml` 的 `weights_short_term` 中添加 `acceleration: 0.05`（初始小权重）
2. 在 `weights_short_term_bear` 中同样添加 `acceleration: 0.03`
3. 运行回测验证 IC 和组合收益贡献
4. 若 IC 显著 > 0，逐步提升权重至 0.08~0.10

---

## 3. 收益偏度因子

### 3.1 因子定义

收益偏度（Return Skewness）衡量收益率分布的不对称性：

```
skewness = E[(r - μ)³] / σ³
```

| 偏度值 | 含义 | 交易含义 |
|--------|------|---------|
| 正偏度 (右偏) | 少数极端正收益 + 多数小负收益 | 可能有"暴涨"潜力，但日常表现平庸 |
| 负偏度 (左偏) | 少数极端负收益 + 多数小正收益 | "稳赚小钱但偶尔爆雷"，风险不对称 |
| 接近 0 | 对称分布 | 收益均匀，无偏 |

### 3.2 学术支持

- **Harvey & Siddique (2000)**: 条件偏度是资产定价的重要因子，正偏度股票要求额外收益补偿
- **Bali, Engle & Murray (2016)**: 尾部风险偏度因子在横截面上有显著预测力
- **Alpha191 库**: 包含 `alpha_075` 等基于偏度的因子

### 3.3 互补性分析

现有因子体系中**完全没有偏度维度**：

| 维度 | 现有因子 | 偏度补充 |
|------|---------|---------|
| 趋势方向 | momentum, alpha_momentum | 偏度衡量趋势的**质量**而非方向 |
| 波动性 | volatility_ma, vol_deviation | 波动是二阶矩，偏度是三阶矩，信息不重叠 |
| 尾部风险 | ❌ 无 | 偏度直接捕捉尾部不对称性 |

**核心价值**：偏度因子提供**三阶矩信息**，与现有二阶矩（波动率）和一阶矩（动量）完全不冗余。

### 3.4 实现方案

```python
class SkewnessScorer(BaseFactorScorer):
    """收益偏度因子 — 收益率分布三阶矩
    
    公式: skewness = mean((r - mean(r))^3) / std(r)^3
    窗口: 20日收益率
    方向: negative（负偏度=左偏=尾部风险大→看空）
    数据要求: 至少 21 日 close
    """
    factor_key = "skewness"
    direction = "negative"  # 负偏度 → 风险大 → 低分
    
    def score(self) -> float:
        close = self._hist.get("close", [])
        if len(close) < 21:
            return 50.0
        import numpy as np
        returns = np.diff(np.log(close[-21:]))
        if len(returns) < 3:
            return 50.0
        mean_r = np.mean(returns)
        std_r = np.std(returns, ddof=1)
        if std_r < 1e-10:
            return 50.0
        skew = np.mean((returns - mean_r)**3) / std_r**3
        # 映射到 0-100: 负偏度→高分(风险大应减仓), 正偏度→低分
        score = 50.0 - skew * 25.0
        return round(max(0.0, min(100.0, score)), 2)
```

### 3.5 建议步骤

1. 在 `factors/scorers.py` 中新增 `SkewnessScorer` 类
2. 在 `CORE_SCORERS` 字典中注册 `"skewness": SkewnessScorer`
3. 在 `config.yaml` 中添加权重 `skewness: 0.04`
4. 回测验证 IC 方向（预期负偏度股票未来收益更低）

---

## 4. 优先级与验收标准

| 优先级 | 任务 | 验收标准 |
|--------|------|---------|
| P0 | 启用已有 AccelerationScorer 权重 | 回测 IC > 0.02，组合收益有正贡献 |
| P1 | 实现 SkewnessScorer | 因子 IC 分析 + 回测对比报告 |

---

## 5. 记忆更新建议

- ScoreSys short_term 当前 15 个因子（不含 acceleration）
- AccelerationScorer 已实现但未启用，可直接配置权重
- SkewnessScorer 需全新开发，方向为 negative（负偏度=风险大=低分）
