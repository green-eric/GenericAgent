# Acceleration因子IC分析报告

## 背景
TODO #6: 动量加速度因子(AccelerationScorer)已实现但权重=0未启用，需分析IC决定是否启用。

## 因子定义
- **公式**: `acceleration = ret_5d - (ret_10d - ret_5d)` = 当前5日收益 - 前5日收益
- **含义**: 加速度为正→动能增强→看涨
- **实现位置**: `D:\Project\ScoreSys\factors\scorers.py:1218` (AccelerationScorer)
- **注册**: CORE_SCORERS字典已注册，scorer.py有委托方法，__init__.py已导出
- **权重机制**: `weight_optimizer.py` 从 `data/ic_data/regime_ic.json` 读取IC数据驱动权重

## IC计算结果

### 全周期IC (2024-01 ~ 2026-05, 574个交易日)
| 指标 | 值 |
|------|------|
| Mean IC | **-0.0276** |
| IC IR | **-0.197** |
| IC > 0 比例 | 41.99% |
| Std IC | 0.1403 |

### 按年份
| 年份 | Mean IC | Std | 日期数 |
|------|---------|-----|--------|
| 2024 | -0.0327 | 0.1662 | 242 |
| 2025 | -0.0301 | 0.1207 | 243 |
| 2026 | -0.0070 | 0.1095 | 89 |

### 与其他因子对比 (full_cycle IC)
| 排名 | 因子 | IC |
|------|------|------|
| 🥇 | industry_momentum | +0.092 |
| 🥈 | alpha_023 | +0.075 |
| 🥉 | momentum | +0.062 |
| 4 | valuation | +0.055 |
| ... | ... | ... |
| 9 | turnover | +0.030 |
| 10 | growth | +0.028 |
| 11 | alpha_rsi | +0.028 |
| 12 | profitability | **+0.015** (最弱但仍为正) |
| ❌ | **acceleration** | **-0.028** (唯一负IC) |

## 结论
**不启用。保持权重=0。**

理由：
1. IC为负(-0.028)，与现有最弱因子(profitability +0.015)方向相反
2. IC IR仅-0.20，远低于其他因子(momentum因子IC虽也有衰减但方向正确)
3. 负IC意味着"动能增强→后续反而跌"，与直觉相悖，可能因A股动量因子本身弱
4. 3年数据一致性负值(2024:-0.033, 2025:-0.030, 2026:-0.007)，非偶然

## 建议
- 保留AccelerationScorer代码，未来市场风格切换时可重新评估
- 若未来启用，需反向使用(负IC→direction改negative)或仅在特定regime使用
- 关注动量类因子的周期性变化，定期重算IC
