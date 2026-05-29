# R113b — ScoreSys README文档一致性修复

## 摘要
基于R113审查报告，逐条验证并修复README.md与代码的不一致。

## 修复清单

| # | 问题 | 修复前 | 修复后 | 严重度 |
|---|------|--------|--------|--------|
| 1 | max_single_weight默认值 | 0.40 (40%) | 0.30 (30%) | 🟡 P1 |
| 2 | regime_max_weight默认值 | 0.35/0.22 | 0.30 (30%) | 🟡 P1 |
| 3 | regime_max_weight历史描述 | V13.10: 0.22→0.35 | 删除过时描述 | 🟢 P2 |
| 4 | profitability因子方向 | 反转：低盈利→高分 | 正向：高ROE/毛利率→高分 | 🟡 P1 |
| 5 | profitability权重百分比 | 1% | 4% | 🟡 P1 |
| 6 | 算法步骤④默认值 | 默认22% | 默认30% | 🟢 P2 |

## 验证结果
- config.yaml: max_single_weight=0.30, regime_max_weight=0.30 ✅
- scorer.py: profitability为正向评分 ✅
- weight_optimizer.py: 代码默认值与config一致 ✅
- Git commit: 3b38779

## 未修复项（需用户决策）
- R113中P0-#1(quotes最新日期): 动态数据，无需硬编码
- R113中P0-#2(DB行数): 当前数据已匹配(quotes 322万/financials 19.3万/scores 4466)
- R113中--export描述: 代码实际行为与README描述一致(自动导出条件已说明)
