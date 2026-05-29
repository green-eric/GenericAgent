# R156 — scheduled_backtest.py verbose参数修复

## 修复内容
- ✅ 已移除 `run_backtest(..., verbose=True)` 中的 `verbose=True` 参数
- ✅ 修复了 BacktestEngine.run_backtest() 不支持 verbose 参数的兼容性问题

## 修复前错误
```
TypeError: BacktestEngine.run_backtest() got an unexpected keyword argument 'verbose'
```

## 修复后状态
- scheduled_backtest.py 现在可以直接运行 `run_backtest(...)`
- 定时任务可以正常启动周度回测

## 后续建议
1. 用 `--once` 模式测试一次完整周度回测
2. 配置 Windows Task Scheduler 作为后台服务
