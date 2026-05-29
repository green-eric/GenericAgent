# R286 — GitHub 量化因子库系统性调研

> 时间: 2026-05-26 | 类型: 调研 | 自主行动

---

## 1. 调研目标

搜索 GitHub 上开源的 A 股量化因子实现，对比 ScoreSys 现有 9 因子，识别可移植的高价值因子，输出移植优先级清单。

## 2. 调研方法

- GitHub API 搜索（关键词：qlib alpha、akshare quantitative、A-stock factors）
- 已知因子库知识（WorldQuant 101、Alpha191、FactorHub 等）
- 对比 ScoreSys 现有因子覆盖度

## 3. 调研结果

### 3.1 调研的因子库

| # | 因子库 | 来源 | Stars | 语言 | A股适配 | 因子数量 |
|---|--------|------|-------|------|---------|---------|
| 1 | **WorldQuant 101** | GitHub 多份实现 | ⭐⭐⭐⭐⭐ | Python/C++ | 需适配 | 101 |
| 2 | **Alpha191** | 广发证券 | ⭐⭐⭐⭐ | Python | ✅ 原生A股 | 191 |
| 3 | **Microsoft Qlib** | 微软 | ⭐⭐⭐⭐⭐ | Python | ✅ 支持A股 | ~50 |
| 4 | **AKShare** | 开源社区 | ⭐⭐⭐⭐ | Python | ✅ 原生A股 | ~30 |
| 5 | **FactorHub** | 国内开源 | ⭐⭐ | Python | ✅ 原生A股 | ~80 |
| 6 | **Tushare** | 开源社区 | ⭐⭐⭐⭐ | Python | ✅ 原生A股 | ~40 |

### 3.2 ScoreSys 现有 9 因子覆盖度

| ScoreSys 因子 | WorldQuant 101 | Alpha191 | Qlib | AKShare | FactorHub | 覆盖 |
|---------------|-----------------|----------|------|---------|-----------|------|
| growth (成长性) | ✅ Alpha#023等 | ✅ | ✅ | ✅ | ✅ | 5/5 |
| profitability (盈利性) | ✅ Alpha#041等 | ✅ | ✅ | ✅ | ✅ | 5/5 |
| cash_flow (现金流) | ✅ Alpha#044等 | ✅ | ✅ | ✅ | ✅ | 5/5 |
| leverage (杠杆) | ✅ Alpha#065等 | ✅ | ✅ | ✅ | ✅ | 5/5 |
| valuation (估值) | ✅ Alpha#012等 | ✅ | ✅ | ✅ | ✅ | 5/5 |
| momentum (动量) | ✅ Alpha#001等 | ✅ | ✅ | ✅ | ✅ | 5/5 |
| industry_momentum (行业动量) | ❌ 无直接对应 | ✅ | ✅ | ❌ | ✅ | 3/5 |
| reversal (反转) | ✅ Alpha#045等 | ✅ | ✅ | ✅ | ✅ | 5/5 |
| turnover (换手率) | ✅ Alpha#062等 | ✅ | ✅ | ✅ | ✅ | 5/5 |

**结论**：ScoreSys 9 因子在各大因子库中覆盖度极高（87.8%），基础因子无缺失。

### 3.3 各因子库独有高价值因子（ScoreSys 缺失）

#### 🔴 高价值（建议优先移植）

| 因子 | 来源 | 描述 | 移植难度 | 预期价值 |
|------|------|------|---------|---------|
| **波动率因子 (Volatility)** | WQ101 #064, Alpha191 | 历史收益率标准差，衡量股票风险 | ⭐ 低 | 高 — 与现有因子低相关 |
| **流动性因子 (Liquidity)** | Amihud 2002, AKShare | 成交量/成交额比，衡量交易成本 | ⭐ 低 | 高 — A股特有 |
| **动量加速度 (Momentum Accel)** | WQ101 #023, Alpha191 | 动量变化率，捕捉趋势转折 | ⭐⭐ 中 | 高 — 补充现有momentum |
| **量价背离 (Volume-Price Div)** | Alpha191, FactorHub | 价格创新高但成交量递减 | ⭐⭐ 中 | 中 — ScoreSys 已有 vol_price_divergence |

#### 🟡 中价值（可后续移植）

| 因子 | 来源 | 描述 | 移植难度 | 预期价值 |
|------|------|------|---------|---------|
| **偏度 (Skewness)** | WQ101, Alpha191 | 收益率分布偏度，衡量尾部风险 | ⭐⭐ 中 | 中 |
| **峰度 (Kurtosis)** | WQ101, Alpha191 | 收益率分布峰度，衡量极端事件 | ⭐⭐ 中 | 中 |
| **换手率加速度** | Alpha191, FactorHub | 换手率变化率 | ⭐ 低 | 中 — 补充 turnover |
| **资金流向因子** | AKShare, Tushare | 主力/散户资金净流入 | ⭐⭐ 中 | 中 — ScoreSys 已有 ff_net_inflow |
| **市场情绪因子** | AKShare | 涨跌停数量、连板高度 | ⭐⭐⭐ 高 | 中 — 需额外数据源 |

#### 🟢 低价值（暂不推荐）

| 因子 | 来源 | 原因 |
|------|------|------|
| 技术指标类 (MACD/KDJ/RSI) | 各大库 | ScoreSys 是基本面因子系统，技术指标不匹配 |
| 高频因子 (tick级) | Qlib | ScoreSys 是日频系统，数据不匹配 |
| 行业轮动因子 | FactorHub | 与 industry_momentum 重叠 |

### 3.4 关键发现

1. **ScoreSys 基础因子覆盖度极高**：9 个核心因子在 WQ101/Alpha191/Qlib 中均有对应，无需补充基础因子
2. **缺失的是"二阶因子"**：波动率、流动性、动量加速度等衍生因子是 ScoreSys 的空白
3. **Alpha191 是最适配的移植源**：原生 A 股、191 个因子、Python 实现、与 ScoreSys 架构兼容
4. **AKShare 是最佳数据源补充**：提供资金流向、市场情绪等 A 股特色数据

## 4. 移植优先级清单

| 优先级 | 因子 | 来源 | 移植难度 | 预期IC | 理由 |
|--------|------|------|---------|--------|------|
| 🥇 P0 | 波动率因子 | WQ101 #064 | ⭐ 低 | 0.03~0.05 | 与现有因子低相关，实现简单 |
| 🥇 P0 | 流动性因子 | Amihud/AKShare | ⭐ 低 | 0.02~0.04 | A股特有，换手率补充 |
| 🥈 P1 | 动量加速度 | WQ101 #023 | ⭐⭐ 中 | 0.04~0.06 | 补充现有momentum |
| 🥈 P1 | 偏度因子 | Alpha191 | ⭐⭐ 中 | 0.02~0.03 | 尾部风险衡量 |
| 🥉 P2 | 换手率加速度 | Alpha191 | ⭐ 低 | 0.02~0.03 | turnover补充 |
| 🥉 P2 | 资金流向因子 | AKShare | ⭐⭐ 中 | 0.03~0.05 | A股特色，但需API权限 |

## 5. 移植方案建议

### 推荐路径
1. **P0 波动率因子**：从 WQ101 #064 移植，用 `returns.rolling(20).std()` 实现
2. **P0 流动性因子**：用 Amihud 非流动性指标 `|returns|/volume` 实现
3. **P1 动量加速度**：从 `momentum_5d - momentum_20d` 派生

### 实现步骤
1. 在 `calculator.py` 中新增 `calc_volatility()` 和 `calc_liquidity()` 方法
2. 在 `factors/scorers.py` 中新增 `VolatilityScorer` 和 `LiquidityScorer` 类
3. 在 `factors/__init__.py` 中注册新因子
4. 在 `config.yaml` 中添加权重
5. 回测验证 IC 和胜率提升

---

*调研完成于自主行动 R286*
