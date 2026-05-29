# R95 | 2026-05-12 | 评估 | AlphaTrading(lca-123/alphas)因子库实测评估

## 摘要
克隆并评估了 `lca-123/alphas` 仓库（含alpha101 83个 + alpha191 191个因子），分析与ScoreSys现有9因子的互补性。

## 仓库信息
- 地址: https://github.com/lca-123/alphas
- 内容: alpha101(83因子) + alpha191(191因子) + alphalens分析 + backtrader回测
- 语言: Python (pandas/numpy)
- 依赖: 需要jqdata或本地数据源

## 因子分类（与ScoreSys对比）

| 因子类别 | alpha101/191 | ScoreSys | 互补性 |
|---------|-------------|----------|--------|
| 动量/趋势 | alpha001-010等 | momentum | ⚠️ 重叠 |
| 反转 | alpha041-050等 | reversal | ⚠️ 重叠 |
| 成交量 | alpha011-020等 | turnover | ⚠️ 重叠 |
| 波动率 | 多个 | ❌ 无 | ✅ 新信号 |
| 价量关系 | 多个 | ❌ 无 | ✅ 新信号 |
| OHLC形态 | 多个 | ❌ 无 | ✅ 新信号 |
| 基本面 | ❌ 无 | growth/profitability等 | ScoreSys独有 |

## 可运行性评估
- ✅ 代码结构清晰，纯Python
- ⚠️ 依赖jqdata数据接口（聚宽），需要替换为本地数据
- ⚠️ alpha191部分因子计算复杂，需要OHLCV完整数据
- ✅ ScoreSys已有baostock数据，可适配

## 关键发现

### 与ScoreSys互补的因子方向
1. **波动率因子**: alpha101中多个波动率相关因子，ScoreSys完全没有
2. **价量关系**: close/open/high/low组合因子，ScoreSys没有
3. **OHLC形态**: 日内价格形态特征，ScoreSys没有

### 与ScoreSys重叠的因子
1. 动量因子（与momentum重叠）
2. 反转因子（与reversal重叠）
3. 成交量因子（与turnover重叠）

## 推荐可加入ScoreSys的新因子方向
1. **波动率**: 已实现波动率、波动率变化率
2. **价量背离**: 价格与成交量的相关性
3. **日内动量**: (close-open)/(high-low)
4. **Amihud非流动性**: |return|/volume

## 结论
- 仓库本身不能直接运行（依赖jqdata），但因子计算公式可直接移植
- **最有价值**: 波动率因子 + 价量关系因子（ScoreSys目前完全没有这些维度）
- **建议**: 选取5-10个与ScoreSys不重叠的因子移植到scorer.py
- **优先级**: P1（因子改造需用户批准修改scorer.py）

## 下一步
- 需用户批准后移植因子到ScoreSys
- 移植后做IC验证
