# R155 — scheduled_backtest 运行状态验证

## 验证结论: ⚠️ 定时任务未持续运行

### 核心发现

| 项目 | 状态 |
|---|---|
| scheduled_backtest.py 存在 | ✅ `D:\Project\ScoreSys\scheduled_backtest.py` (283行) |
| 当前运行中的 scheduler 进程 | ❌ 无 |
| jobstore 持久化文件 | ❌ 无 jobs.sqlite |
| scheduler.log | ✅ 26行，最后写入 5-15 22:54 |

### scheduler.log 关键事件

1. **22:29:45** — 单次模式启动周度回测
2. **22:29:45** — ❌ 立即失败: `BacktestEngine.run_backtest() got an unexpected keyword argument 'verbose'`
3. **22:34:08** — 模块导入成功（可能是 --list 或 --daily 调用）
4. **22:54:20** — 再次模块导入成功后退出（前台模式，主进程结束即退出）

### 根因分析

**直接原因**: `weekly_backtest_job()` 调用 `bt.run_backtest(... verbose=True)` 传入了 `verbose` 参数，但 `BacktestEngine.run_backtest()` 不支持此参数 → `TypeError` 崩溃。

**架构原因**: 即使修复了参数错误，`scheduled_backtest.py` 是**前台阻塞模式**（`BlockingScheduler.start()`），需要用户手动保持终端打开。没有注册为 Windows 服务或后台进程，用户离开即停止。

### 最近 ScoreSys 活动

最新日志全部集中在 **5-15**，包括多次 fetch、run、score 操作，说明用户当天手动运行了多次。但 scheduler 定时任务从未成功完成过一次完整的周度回测。

### 建议修复

1. **紧急**: 修复 `weekly_backtest_job()` 中的 `verbose` 参数问题
2. **架构**: 改为后台服务（Windows Task Scheduler / NSSM / pythonw + 无限循环）
3. **验证**: 修复后用 `--once` 模式测试一次完整周度回测

### 探测: calculator.py Polars 状态

顺便确认: `calculator.py` 标题已注明"Polars版"，完全向量化，零逐行循环。polars 替换在该文件已完成。
