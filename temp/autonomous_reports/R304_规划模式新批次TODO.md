# 规划模式报告 R309 — 2026-05-29 自主行动

## 批判性历史分析

读取 history.txt 近50条，识别以下模式：

### 低价值模式（已停止）
- ✅ R300-304：验证/收尾/文档类任务，无新发现
- ✅ R286：GitHub因子库调研 → 调研完成但无后续执行
- ✅ R277：fusion_picker审查 → 发现P0但未执行修复

### 高价值线索（来自R295-R308）
- **R303 param_sweep** → 最优参数rb=10/top=10/min=50/夏普2.258，已应用V16.9
- **R295 因子调研** → AccelerationScorer已实现但未启用权重（需激活）
- **R291 BfM SSE** → clash-verge代理持续离线，根因在代理层
- **R307 V16.9** → +353.09% 夏普2.118，已整合入README

---

## 深度环境扫描发现

### 发现1：daily_health_check.py 已移入 archive/
**影响**：用户没有实时健康检查。
- `run_daily_score.py` 存在（手动运行脚本），但无定时健康检查
- archive/scheduled_backtest.py 存在但未部署
- **风险**：数据源/代理异常无告警

### 发现2：weight_optimizer V2.0 WIP
- commit e615bea: "WIP: V2.0 weight_optimizer soft混合诊断完成，准备修复"
- commit b781f8b: "update" — 大量清理归档
- **关键**：soft混合权重（softmax-style平滑分散）可能替代当前硬阈值regime权重
- **风险**：V2.0未完成，用户运行的是V16.9的硬阈值体系

### 发现3：大量文件归档至 archive/
```
fusion_picker.py       → archive/fusion_picker.py (392行已删除)
sweep_v2.py           → archive/sweep_v2.py
full_backfill.py       → archive/full_backfill.py
scheduled_backtest.py  → archive/scheduled_backtest.py
data_sources/         → archive/data_sources/
strategies/           → archive/strategies/
```
清理合理，但 daily_health_check.py 也被归档（疑似误操作）

### 发现4：基准超额仍为 -5.60%
- V15.9时期基准超额已修复
- 但V16.9回测基准对比仍有偏差空间

### 发现5：AccelerationScorer 未激活
- 已实现但权重为0或未配置到活跃列表

---

## 建议TODO批次

**需 subagent 评审后再执行**

### P0（必须，不执行）
1. **恢复 daily_health_check.py** → 确认 run_daily_score.py 是否替代，或从archive恢复
2. **weight_optimizer V2.0 进度确认** → 软混合权重是否可测试/是否阻塞当前V16.9

### P1（重要，不执行）
3. **AccelerationScorer 权重激活** → 已在R295确认实现，加权重0.05测试IC
4. **基准超额根因深挖** → V16.9 vs V15.9基准计算差异点

### P2（可选，不执行）
5. **BfM clash-verge代理状态** → 持续3天0%可用，需用户恢复代理
6. **信号推送稳定性** → 检查 --push 微信告警是否正常运行

---

## 记忆更新建议

无记忆更新（未执行任务）

---

> ⚠️ **本报告仅规划，待 subagent 评审后进入执行模式**