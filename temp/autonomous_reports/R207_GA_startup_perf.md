# GA 启动耗时分析报告

> 任务: 分析agentmain.py启动各阶段耗时(import/init/keys)，找出瓶颈提出优化方案
> 完成时间: 2026-05-19

## 测试方法
在真实环境中逐阶段计时 (time.perf_counter)，每个阶段独立测量。

## 耗时数据

| 阶段 | 耗时 | 占比 | 说明 |
|------|------|------|------|
| [1] 标准库 import | 9ms | 0.4% | json/re/random/locale/threading/queue |
| [2] llmcore import | 452ms | 19.5% | LLM会话/工具客户端初始化 |
| [3] agent_loop import | 20ms | 0.9% | Agent主循环 |
| [4] ga import | 660ms | 28.5% | **最大瓶颈**: GenericAgentHandler/smart_format/get_global_memory |
| [5] reload_mykeys | 16ms | 0.7% | 密钥加载 |
| [6] load_tool_schema | 23ms | 1.0% | 工具schema解析 |
| [7] load memory files | 1ms | 0.0% | 全局记忆加载 |
| [8] otel_auto_trace | 720ms | 31.1% | **第二大瓶颈**: monkey-patch 4 hooks |
| [9] GeneraticAgent class | 11ms | 0.5% | 类定义导入 |
| [10] CDP config init | 0ms | 0.0% | 配置文件已存在 |
| **合计** | **~1912ms** | | 不含 LLM 首次网络请求 |

## 瓶颈分析

### 🔴 瓶颈 1: ga import (660ms, 28.5%)
- GenericAgentHandler 导入链长: ga → llmcore → 各种工具
- smart_format 依赖 emoji/格式处理
- get_global_memory 读取多个文件

### 🔴 瓶颈 2: otel_auto_trace (720ms, 31.1%)
- monkey-patch 4 个 hooks (LLM调用追踪)
- 每次导入都执行 patch 逻辑
- 当前默认激活 console exporter

## 优化建议

| 优先级 | 建议 | 预期收益 |
|--------|------|----------|
| P0 | otel_auto_trace 延迟激活: 改为 setup_tracer() 手动调用而非 import 即激活 | -720ms |
| P1 | ga.py 延迟导入: smart_format/get_global_memory 改为函数内导入 | -200~400ms |
| P2 | llmcore 懒加载: ToolClient 首次使用时才初始化 | -200ms |
| P3 | 缓存工具 schema: load_tool_schema 结果缓存到文件 | -20ms |

## 预期效果
- P0 实施后: ~1.2s (节省 720ms)
- P0+P1 实施后: ~0.8s (节省 1.1s)
- 全部实施后: ~0.5s (节省 1.4s)
