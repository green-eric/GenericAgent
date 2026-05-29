# file_monitor_v2 真正回测触发集成报告

> 任务: 将 _trigger_backtest 从 print 模拟改为真正调用 ScoreSys backtest.py
> 完成时间: 2026-05-19

## 问题
`_trigger_backtest` 方法只有 `print("[ScoreSys] auto-trigger backtest...")` 模拟输出，未真正执行回测。

## 修复内容

### 1. 直接调用 backtest_engine API
- 导入 `BacktestEngine`, `StrategyConfig`, `pure_scoresys`
- 从 `D:\Project\ScoreSys\stock_data.db` 读取数据
- 自动获取再平衡日期，配置 top20/min_score=30 策略
- 执行回测并输出结果摘要

### 2. 防抖逻辑修复
- 30秒内不重复触发（首次不防抖）
- 修复了时间戳更新顺序导致的首次触发被跳过bug

### 3. 后台线程执行
- 回测在独立守护线程中运行，不阻塞文件监控
- 结果保存为 JSON 到 `autonomous_reports/auto_bt_*.json`

## E2E 测试结果
```
📝 创建 stock_data.db → 文件监控检测到变更
🚀 自动触发回测: 2 dates, top20, min_score=30
✅ 策略: auto_file_monitor | 总收益: +1.61% | 年化: +3.25%
📄 结果已保存: autonomous_reports/auto_bt_20260519_073507.json
```

## 代码变更
- `file_monitor_v2.py`: 添加 `import sys`, 重写 `_trigger_backtest` 方法
- 新增 `import json`（用于结果序列化）
