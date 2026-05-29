# R315 — V17.0 AccelerationScorer IC回测验证

> 📅 2026-05-30 | 自主行动 TODO#11

## 结论：⚠️ 无法验证 — AccelerationScorer 未找到

### 搜索结果
- `acceleration_scorer.py` — 不存在于 `D:\Project\ScoreSys\`
- `scorers/` 目录 — 不存在
- 关键字搜索（accel, skew, acceleration）— 无匹配文件

### 背景
- R295（2026-05-28）提到 "AccelerationScorer已实现未启用权重"
- 实际代码仓库中不存在该文件
- 可能状态：规划中 / 曾在其他分支 / 描述有误

### 建议
1. **确认需求**：用户确认是否需要实现 AccelerationScorer
2. **如需要**：参考 SkewnessScorer（R301已实现）模式开发
3. **预计工作量**：2~3小时（数据获取 + 计算逻辑 + 回测集成）

### 替代方案
在 AccelerationScorer 实现前，可先使用现有动量因子组：
- `momentum`（权重 0.0672）
- `industry_momentum`（权重 0.1728）
- `alpha_momentum`（权重 0.0576）

三者合计权重 0.2976，已覆盖动量加速度逻辑。

## 标记
- 状态：⏸️ 等待用户确认是否需要实现
- 建议优先级：P2（低，现有动量因子已覆盖）
