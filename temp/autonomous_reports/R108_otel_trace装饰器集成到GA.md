# R108 | 2026-05-19 | 能力 | otel_trace装饰器集成到GA

## 执行摘要
分析otel_trace.py @trace_llm_call装饰器集成到GA核心代码的可行性方案。参考langfuse_tracing.py的monkey-patch模式，提出非侵入式集成方案。

## 现有组件分析

### otel_trace.py (plugins/otel_trace.py, 205行)
- 已有完整@trace_llm_call装饰器实现
- 支持setup_tracer(service_name, exporter, resource_attrs)
- Span捕获: llm.model, llm.operation, llm.input.messages, llm.output.content
- 捕获usage: input_tokens/output_tokens/total_tokens
- 捕获error, duration_ms
- 需要opentelemetry-sdk已安装

### llmcore.py (llmcore.py, 1023行)
核心LLM调用点:
- **ClaudeSession.raw_ask()** (L601): Claude API调用
- **LLMSession.raw_ask()** (L619): OpenAI兼容API调用
- 两者都通过_stream_with_retry() -> requests.post()发送请求
- _write_llm_log(): 日志记录点（已被langfuse_tracing.py patch）

### langfuse_tracing.py (plugins/langfuse_tracing.py, 122行)
- 已有monkey-patch集成先例
- 通过import时自激活，无需修改llmcore.py
- 只patch _write_llm_log函数

## 集成方案（非侵入式）

### 方案: 创建otel_auto_trace.py插件
参考langfuse_tracing.py模式，创建新插件文件:

**plugins/otel_auto_trace.py**:
- import时检查mykey中otel_config
- 若存在则自动patch ClaudeSession.raw_ask和LLMSession.raw_ask
- 使用@trace_llm_call装饰器包装原始方法
- 完全不修改llmcore.py核心代码

### mykey配置
```python
otel_config = {
    'service_name': 'ga-agent',
    'exporter': 'otlp',
    'endpoint': 'http://localhost:4317'
}
```

## 技术挑战

### 生成器函数装饰器问题
- raw_ask()是生成器函数(yield from)
- @trace_llm_call需要支持生成器wrap
- 需验证otel_trace.py是否已处理生成器

### 装饰器对self参数的兼容性
- raw_ask(self, messages)是实例方法
- monkey-patch后需保持self正确传递

## 实施步骤
1. 确认opentelemetry-sdk已安装
2. 验证otel_trace.py的@trace_llm_call支持生成器
3. 创建plugins/otel_auto_trace.py
4. 在mykey.py添加otel_config
5. 测试验证Span数据正确生成

## 结论
- 方案可行，参考langfuse_tracing.py先例
- 无需修改llmcore.py核心代码
- 需验证生成器兼容性
- 需用户批准后创建新文件（修改GA代码库）

---
*分析完成，验收通过，待用户批准实施*