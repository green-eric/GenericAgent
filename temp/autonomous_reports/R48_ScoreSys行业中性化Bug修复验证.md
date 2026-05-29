# R117 | 2026-05-19 | 产出 | ScoreSys行业中性化Bug修复验证

## 执行摘要
发现并修复database.py中calc_industry_stats的key映射bug，使Growth和Profitability因子的行业中性化真正生效。修复后IC提升26.4%，IR提升40.2%。

## Bug根因

### 问题：KEY不匹配导致行业中性化从未生效

`database.py` 的 `calc_industry_stats()` 返回的key：
- `net_profit_yoy_p25/p75`
- `revenue_yoy_p25/p75`

`GrowthScorer` 期望的key：
- `profit_accel_p25/p75`
- `revenue_accel_p25/p75`

`ProfitabilityScorer` 期望的key：
- `profit_accel_p25/p75`

**结果**：当 `industry_stats.get("profit_accel_p25")` 返回 None 时，`_percentile_score` 使用默认值，打分退化为绝对阈值路径。

## 修复方案

在 `database.py` L1111-1124 的统计结果输出前添加key映射：
```python
_mapped = {'net_profit_yoy': 'profit_accel', 'revenue_yoy': 'revenue_accel'}.get(metric, metric)
```

## 修复前后对比

| 指标 | 修复前 | 修复后 | 变化 |
|------|--------|--------|------|
| 平均IC | +0.0755 | +0.0954 | **+26.4%** |
| IC标准差 | 0.1451 | 0.1309 | **-9.8%** |
| IC>0占比 | 72.7% | 81.8% | **+9.1%** |
| IR | 0.520 | 0.729 | **+40.2%** |

## 回测配置
- 区间：2023-09-01 ~ 2026-03-31
- 调仓：3个月 | 11期
- 股票池：300只（粗筛自4221只）

## 结论
修复后行业中性化效果显著，11期中有8期IC提升。建议后续：
1. 对动量/换手率等技术指标也做行业中性化
2. 按行业分组看IC改善效果
3. 扩展到24期+进一步提升统计显著性

---
*验收: bug修复+回测验证完成*
*修复文件: database.py L1111-1124*
*回测脚本: industry_neutral_backtest.py*
