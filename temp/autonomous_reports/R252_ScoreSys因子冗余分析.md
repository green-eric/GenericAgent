# R255 — ScoreSys 因子冗余分析

> 📅 2026-05-23 | 用户指示执行

## 分析方法

- 工具: `ScoreSys/archive/factor_redundancy.py`（修复了DB_PATH和GROUP BY alias bug）
- 数据: `stock_data.db` (1.4GB, 4344只股票, 26032条评分记录, 最新2026-05-22)
- 因子库: 9个因子（与R142一致，无新增）

## 三组分析结果

### ① 单日截面 (2026-05-22, threshold=0.9)
**🔴 冗余因子对: 0 对** ✅

### ② 历史均值 (全量GROUP BY, threshold=0.9)
**🔴 冗余因子对: 0 对** ✅

### ③ 历史均值敏感性 (threshold=0.8)
**🔴 冗余因子对: 0 对** ✅

## 相关矩阵对比（历史均值 vs 单日）

| 因子对 | 单日(5/22) | 历史均值 | 差异 |
|--------|-----------|---------|------|
| profitability ↔ valuation | +0.238 | **+0.58** | ⬆️ 长期相关性显著更高 |
| momentum ↔ industry_momentum | +0.344 | **+0.53** | ⬆️ 长期更紧密 |
| industry_momentum ↔ reversal | -0.276 | **-0.34** | ⬆️ 负相关增强 |
| growth ↔ profitability | -0.348 | -0.21 | ⬇️ 长期相关性减弱 |
| reversal ↔ turnover | -0.128 | **-0.19** | ⬆️ 轻微增强 |

## 关键发现

1. **无冗余因子** — 所有因子对 |r| < 0.6，远低于0.9阈值，9个因子全部独立
2. **最高相关对** — profitability ↔ valuation (历史均值 r=+0.58)，盈利能力与估值长期有中度正相关
3. **最强负相关** — industry_momentum ↔ reversal (历史均值 r=-0.34)，行业动量与反转效应互为补充
4. **最独立因子** — growth（成长性）与其他因子相关性最低，提供最多增量信息
5. **数据质量** — 现金流/动量/行业动量/换手率覆盖率100%；反转因子覆盖率最低(66%)

## 结论

**ScoreSys当前9因子库设计合理，无冗余，无需降维。**

因子间最大相关性仅0.58（盈利能力↔估值），处于"中度相关"而非"冗余"区间。
各因子从不同维度（成长/盈利/现金流/杠杆/估值/动量/行业动量/反转/换手率）独立贡献信息。

## 工具修复

- 修复 DB_PATH: `archive/stock_data.db` → `../stock_data.db`
- 修复 GROUP BY alias: `AVG(col)` → `AVG(col) AS col`（避免pandas列名不匹配）

## 产出文件

- `ScoreSys/archive/factor_correlation_matrix.csv` — 相关矩阵
- `ScoreSys/archive/factor_redundancy_report.md` — 详细分析报告
