# R71 — 微信Bot回复速度诊断：ScoreSys数据抓取拖慢系统

**日期**: 2026-05-08 | **类型**: 诊断

---

## 🔍 诊断结果

| 指标 | 数值 | 状态 |
|------|------|------|
| 系统 CPU | **99.6%** | 🔴 满载 |
| 内存 | 10.6/15.7GB (67.4%) | 🟡 偏高 |
| 进程 PID=18504 | **434.4% CPU** / 43线程 / 191MB | 🔴 元凶 |

### 元凶进程

```
PID=18504 | python main.py --real --pool stock_pool.txt 
--workers 8 --save-db --fetch-only --db stock_data.db --force-refresh
```

ScoreSys 全量股票数据抓取，8 并发 worker + akshare 网络请求，占满全部 CPU 核心。

---

## ⛓️ 对 Bot 回复速度的影响链

```
ScoreSys 8 workers → CPU 99.6% → Agent 工具调用排队
→ 单次 tool call 耗时 2-5s（正常 <1s）→ 单次回复 10+ 轮次
```

---

## 💡 建议方案

| 方案 | 操作 | 风险 | 效果 |
|------|------|------|------|
| 🅐 限并发 | `--workers 2` 重新运行 | 无 | 释放 75% CPU |
| 🅑 降优先级 | `psutil.Process(18504).nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)` | 极低 | Agent 优先调度 |
| 🅒 等完成 | 等待 fetch 自然结束 | 无 | 时间未知 |
| 🅓 杀进程 | `taskkill /PID 18504` | 数据不完整 | 立即释放 |

> **推荐 🅑 降优先级** — 不中断数据抓取，同时让 Agent/Bot 获得 CPU 调度优先权。已可执行。

---

## 📊 关联 TODO

| # | 任务 | 本次进展 |
|---|------|---------|
| 4 | 微信Bot回复速度优化 | 🔍 诊断完成，根因明确，待用户选择方案执行 |

> ⚠️ 未执行优化操作（需用户确认不可逆步骤）。本报告作为诊断交付。