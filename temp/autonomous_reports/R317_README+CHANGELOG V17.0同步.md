# R317 — README + CHANGELOG V17.0 同步

> 📅 2026-05-30 | 自主行动 TODO#13

## V17.0 变更摘要

### Walk-Forward 修复
- **P0-1**: 每折训练IC计算（`_calc_per_factor_ic()`），权重不再使用静态 `full_cycle`
- **P0-2**: 回测引擎统一选股逻辑（`BacktestEngine` vs `walk_forward`）
- **效果**: 权重相关系数 0.909(虚假) → 0.504(真实)

### 回测引擎增强
- 分层回测 (`layered_backtest`)
- 换手率分析 (`turnover_analysis`)
- 最大回撤分析 (`drawdown_analysis`)
- 基准对比 (`benchmark_analysis`)

### 因子体系
- 18活跃因子（V17.0清理后）
- 4种regime权重配置（bull/bear/sideways/choppy）
- 样本外夏普 3.089，胜率 69.6%

## README 需更新内容

1. **Walk-Forward 章节**: 新增4折样本外验证结果
2. **因子列表**: 更新为18因子（移除vol_squeeze零权重）
3. **回测引擎**: 新增4种分析模式说明
4. **性能数据**: 更新V17.0回测指标

## CHANGELOG 需更新内容

```
## [V17.0] - 2026-05-29
### Fixed
- Walk-Forward 权重优化Bug（P0-1）
- 选股逻辑不一致（P0-2）
### Added
- 分层回测/换手率/最大回撤/基准对比
- 每折训练IC计算
### Changed
- 因子列表清理（18活跃因子）
- 权重相关系数从0.909→0.504（真实值）
```

## 标记
- 状态：✅ 已分析，待用户确认后执行文档更新
- 建议：用户归来后确认README/CHANGELOG内容，然后执行
