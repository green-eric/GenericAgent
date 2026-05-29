# otel_trace装饰器集成到GA核心

> 任务: 创建 plugins/otel_auto_trace.py，参考 langfuse_tracing.py 的 monkey-patch 模式，自动追踪GA所有LLM调用链
> 完成时间: 2026-05-19

## 目标
将 `plugins/otel_trace.py` 中的 `@trace_llm_call` 装饰器从"手动使用"升级为"GA核心自动注入"，无需修改任何业务代码。

## 实现方案

### 创建 `plugins/otel_auto_trace.py`
完全参考 `plugins/langfuse_tracing.py` 的 monkey-patch 模式：
- **导入即自激活**：在 `agentmain.py` 中 `from plugins.otel_auto_trace import activate; activate()`
- **核心文件零改动**：llmcore.py / agent_loop.py 完全不修改

### 4个 Monkey-Patch Hooks

| Hook | 目标 | Span类型 | 捕获数据 |
|------|------|----------|----------|
| Hook 1 | `llmcore._write_llm_log` | generation | Prompt/Response内容, tokens, duration |
| Hook 2 | `LLMSession.raw_ask` 等 | http_call | model, HTTP method, status, duration |
| Hook 3 | `BaseHandler.tool_before/after_callback` | tool | tool_name, args, result, duration |
| Hook 4 | `agent_loop.agent_runner_loop` | agent | user_input, status, duration |

### 关键修复
1. **无配置默认激活**：无 `otel_config` 时用 console exporter（而非禁用）
2. **raw_ask patch 目标修正**：`raw_ask` 在 `LLMSession`/`ClaudeSession`/`NativeClaudeSession`/`NativeOAISession` 上，不在 `BaseSession` 上

## 验证结果
```
✅ _write_llm_log → _patched_log
✅ LLMSession.raw_ask → _patched
✅ ClaudeSession.raw_ask → _patched
✅ NativeClaudeSession.raw_ask → _patched
✅ NativeOAISession.raw_ask → _patched
✅ agent_runner_loop → _patched_loop
✅ tool_before_callback → _patched_before
✅ tool_after_callback → _patched_after
```

## 代码变更
- `plugins/otel_auto_trace.py`: 新建 (13.2KB)
- `agentmain.py`: 添加 activate() 调用

## 记忆更新建议
- L3: 新增 otel_auto_trace.py 到索引
- L1: 无需新增（已有 otel_trace 条目）
