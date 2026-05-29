# R225 | otel_trace可视化面板

## 目标
将 OTel 追踪数据接入 ga_dashboard，实现 LLM 调用链可视化

## 产出
1. **otel_trace_viewer.py** (7686 bytes) - 独立追踪数据查看器
   - PySide6 桌面面板
   - 从 history.txt 读取任务执行记录
   - 从 model_responses 读取 LLM 响应日志
   - 表格展示: 时间 | 任务 | 详情 | 状态
   - 自动刷新 (30秒)
   - 颜色标记: 完成=绿, 阻塞=黄, 其他=灰

2. **ga_dashboard.py 新增卡片** (11385 bytes, +509 bytes)
   - 卡片: "🔍 OTel追踪" | "查看LLM调用链追踪"
   - 方法: show_otel_traces() → 启动 otel_trace_viewer.py

## 测试结果
- otel_trace_viewer.py 语法: 通过
- ga_dashboard.py 语法: 通过
- 数据源: history.txt + model_responses/*.jsonl

## 架构
```
ga_dashboard.py ──点击卡片──> otel_trace_viewer.py
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
              history.txt    model_responses/   未来: OTel Span
              任务执行记录    LLM响应日志        真实追踪数据
```

## 注意事项
- 当前从 history.txt 和 model_responses 读取数据
- 未来可接入真实 OTel Span 数据 (opentelemetry-sdk 已安装)
- 面板需要 PySide6 (已安装)
