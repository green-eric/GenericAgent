# R263 - scikit-learn/statsmodels在ScoreSys中的应用探测

## 任务信息
- 类型: 环境探测
- 来源: TODO.txt「环境 | scikit-learn/statsmodels在ScoreSys中的应用探测」
- 时间: 2026-05-25 (自主行动)
- 环境: scikit-learn 1.8.0, statsmodels 0.14.6, scipy 1.17.1

## 探测结论

### 1. IC计算交叉验证（核心发现）

ScoreSys手写 `_spearman()` 与 `scipy.stats.spearmanr()` 对比：

| 方法 | IC值 | 差异 |
|------|------|------|
| ScoreSys 手写 _spearman | -0.07408396 | — |
| scipy.stats.spearmanr | -0.07408396 | **0.00e+00** |

**✅ 结论: 两者完全一致，可相互替换。**

### 2. ML库在ScoreSys各场景的应用评估

| 场景 | 库/方法 | 适用性 | 备注 |
|------|---------|--------|------|
| IC计算 | scipy.stats.spearmanr | ✅ 可直接替换 | 结果完全一致 |
| 因子回归 | statsmodels.OLS/WLS | ✅ 可用于因子显著性检验 | 提供t/p值、R² |
| 因子筛选 | sklearn Lasso | ✅ 可用于因子压缩选择 | L1正则化自动筛选 |
| 因子降维 | sklearn PCA | ✅ 可用于因子冗余消除 | 提取主成分 |
| 稳健IC | scipy.stats.kendalltau | ✅ 更稳健的秩相关 | 对异常值更鲁棒 |
| 线性IC | scipy.stats.pearsonr | ⚠️ 可作为参考 | 对异常值敏感 |

### 3. 实际数据测试（2025-01-01 ~ 2025-06-30，200只股票）

单因子IC分析：
- total_score IC = +0.1025 (1期，p≈0.33不显著，样本少)

多因子回归（OLS）：
- total_score coef = -0.0040, R² = 0.013
- 受限：score_batch只返回total_score，不含子因子分项

### 4. 建议

1. **立即可做**: 用 `scipy.stats.spearmanr` 替换手写 `_spearman`，减少维护负担
2. **中期可做**: 用 `statsmodels.OLS` 做因子显著性检验，替代手工t检验
3. **长期可做**: 用 `sklearn Lasso/Ridge` 做因子权重优化

## 备注
- score_batch只返回total_score字段，多因子分析需要score_batch返回子因子分项
- 当前IC计算逻辑正确，手写实现与scipy一致
- 所有ML库已安装，无需额外安装
