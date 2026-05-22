"""
otel_auto_trace.py — GA核心OTel自动追踪插件
=================================================
参考 langfuse_tracing.py 的 monkey-patch 模式，自动追踪 GA 所有 LLM 调用链。

Self-activates on import if mykey 中有 otel_config 配置。

Monkey-patch hooks:
  - llmcore._write_llm_log       → LLM generation span (Prompt=start, Response=end)
  - llmcore.BaseSession.raw_ask  → HTTP call span (model, tokens, duration)
  - agent_loop.BaseHandler.tool_before/after_callback → tool span
  - agent_loop.agent_runner_loop → agent task span (parent of all)

Usage:
    # 在 mykey.py 中配置:
    otel_config = {
        "service_name": "ga-agent",
        "exporter": "console",       # "console" | "otlp" | "jaeger"
        "otlp_endpoint": "http://localhost:4317",
        "resource_attrs": {"env": "dev"},
    }
    
    # 导入即自动激活（在 llmcore.reload_mykeys 之后）:
    from plugins import otel_auto_trace
"""

import threading
import time
import json
import os
import sys
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# ── OTel SDK 延迟导入 ────────────────────────────────────────────────────────

_tracer_provider = None
_tracer = None
_initialized = False
_config = None

_tls = threading.local()


def _try_setup_tracer():
    """初始化 tracer：优先从 mykey 读取 otel_config，无配置则用默认 console exporter"""
    global _tracer_provider, _tracer, _initialized, _config
    if _initialized:
        return

    _cfg = None
    try:
        from llmcore import _load_mykeys
        _cfg = _load_mykeys().get('otel_config')
    except Exception:
        pass

    if _cfg:
        _config = _cfg
        service_name = _cfg.get('service_name', 'ga-agent')
        exporter_type = _cfg.get('exporter', 'console')
    else:
        # 无配置：默认 console exporter
        _config = None
        service_name = 'ga-agent'
        exporter_type = 'console'

    try:
        from opentelemetry import trace as otel_trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.resources import Resource

        resource_attrs = _cfg.get('resource_attrs', {}) if _cfg else {}
        resource = Resource(attributes={"service.name": service_name, **resource_attrs})
        _tracer_provider = TracerProvider(resource=resource)

        # 选择 exporter
        if exporter_type == 'console':
            from opentelemetry.sdk.trace.export import ConsoleSpanExporter
            exporter = ConsoleSpanExporter()
        elif exporter_type == 'otlp':
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            endpoint = (_cfg or {}).get('otlp_endpoint', 'http://localhost:4317')
            exporter = OTLPSpanExporter(endpoint=endpoint)
        elif exporter_type == 'jaeger':
            try:
                from opentelemetry.exporter.jaeger.thrift import JaegerExporter
                exporter = JaegerExporter()
            except ImportError:
                from opentelemetry.sdk.trace.export import ConsoleSpanExporter
                exporter = ConsoleSpanExporter()
        else:
            from opentelemetry.sdk.trace.export import ConsoleSpanExporter
            exporter = ConsoleSpanExporter()

        _tracer_provider.add_span_processor(BatchSpanProcessor(exporter))
        otel_trace.set_tracer_provider(_tracer_provider)
        _tracer = otel_trace.get_tracer(service_name)
        _initialized = True
        logger.info("otel_auto_trace: tracer initialized (service=%s, exporter=%s, config=%s)",
                     service_name, exporter_type, 'mykey' if _cfg else 'default')
    except ImportError as e:
        logger.warning("otel_auto_trace: OTel SDK not available: %s", e)
        _initialized = True
    except Exception as e:
        logger.error("otel_auto_trace: tracer init failed: %s", e)
        _initialized = True


def _ensure_tracer():
    """确保 tracer 已初始化（延迟初始化）"""
    if not _initialized:
        _try_setup_tracer()


def _safe_json(obj, max_len=4000):
    """安全序列化，截断超长内容"""
    try:
        s = json.dumps(obj, ensure_ascii=False, default=str)
    except Exception:
        s = str(obj)
    if len(s) > max_len:
        s = s[:max_len] + "...[truncated]"
    return s


# ── Hook 1: llmcore._write_llm_log → LLM Generation Span ────────────────────

def _patch_write_llm_log():
    """Monkey-patch llmcore._write_llm_log 创建 LLM generation span"""
    try:
        import llmcore
    except ImportError:
        return

    _orig_log = llmcore._write_llm_log

    def _patched_log(label, content):
        _ensure_tracer()
        if _tracer is not None:
            try:
                if label == 'Prompt':
                    # 开始新的 generation span
                    _tls.gen_span = _tracer.start_span(
                        name="llm.generation",
                        attributes={
                            "llm.operation": "chat",
                            "llm.input": _safe_json(content, max_len=8000),
                        }
                    )
                    _tls.gen_start_time = time.time()
                    _tls.usage = None
                elif label == 'Response':
                    # 结束 generation span
                    duration_ms = 0
                    if hasattr(_tls, 'gen_start_time'):
                        duration_ms = (time.time() - _tls.gen_start_time) * 1000
                    attrs = {
                        "llm.output": _safe_json(content, max_len=8000),
                        "llm.duration_ms": duration_ms,
                    }
                    if hasattr(_tls, 'usage') and _tls.usage:
                        attrs["llm.usage.input_tokens"] = _tls.usage.get('input', 0)
                        attrs["llm.usage.output_tokens"] = _tls.usage.get('output', 0)
                        attrs["llm.usage.total_tokens"] = _tls.usage.get('total', 0)
                    if hasattr(_tls, 'gen_span') and _tls.gen_span:
                        _tls.gen_span.set_attributes(attrs)
                        _tls.gen_span.end()
                        _tls.gen_span = None
            except Exception as e:
                logger.debug("otel_auto_trace: log hook error: %s", e)
        return _orig_log(label, content)

    llmcore._write_llm_log = _patched_log
    logger.info("otel_auto_trace: patched llmcore._write_llm_log")


# ── Hook 2: BaseSession.raw_ask → HTTP Call Span ──────────────────────────────

def _patch_raw_ask():
    """Monkey-patch raw_ask on all session classes that have it (LLMSession, ClaudeSession, Native*)"""
    try:
        import llmcore
    except ImportError:
        return

    # raw_ask is NOT on BaseSession — it's on leaf classes
    _targets = []
    for _name in ('LLMSession', 'ClaudeSession', 'NativeClaudeSession', 'NativeOAISession'):
        _cls = getattr(llmcore, _name, None)
        if _cls and hasattr(_cls, 'raw_ask'):
            _targets.append((_name, _cls))

    if not _targets:
        logger.debug("otel_auto_trace: no raw_ask targets found")
        return

    for _cls_name, _cls in _targets:
        _orig = _cls.raw_ask

        def _make_patched(orig, cls_name):
            def _patched(self, prompt, **kwargs):
                _ensure_tracer()
                if _tracer is None:
                    return orig(self, prompt, **kwargs)
                model_name = getattr(self, 'name', getattr(self, 'model', 'unknown'))
                with _tracer.start_as_current_span(
                    name=f"llm.http_call.{model_name}",
                    attributes={
                        "llm.model": model_name,
                        "llm.operation": "raw_ask",
                        "http.method": "POST",
                    }
                ) as span:
                    start_time = time.time()
                    try:
                        result = yield from orig(self, prompt, **kwargs)
                        duration_ms = (time.time() - start_time) * 1000
                        span.set_attribute("llm.duration_ms", duration_ms)
                        span.set_attribute("llm.status", "ok")
                        return result
                    except Exception as e:
                        duration_ms = (time.time() - start_time) * 1000
                        span.set_attribute("llm.duration_ms", duration_ms)
                        span.set_attribute("llm.status", "error")
                        span.set_attribute("llm.error", str(e))
                        raise
            return _patched

        _cls.raw_ask = _make_patched(_orig, _cls_name)
        logger.info("otel_auto_trace: patched %s.raw_ask", _cls_name)


# ── Hook 3: tool_before/after_callback → Tool Span ───────────────────────────

def _patch_tool_callbacks():
    """Monkey-patch agent_loop.BaseHandler tool_before/after 创建 tool span"""
    try:
        import agent_loop
    except ImportError:
        return

    _BaseHandler = getattr(agent_loop, 'BaseHandler', None)
    if _BaseHandler is None:
        return

    _orig_before = getattr(_BaseHandler, 'tool_before_callback', None)
    _orig_after = getattr(_BaseHandler, 'tool_after_callback', None)

    def _patched_before(self, tool_name, args, response):
        _ensure_tracer()
        if _tracer is not None:
            try:
                if not hasattr(_tls, 'tstack'):
                    _tls.tstack = []
                a = {k: v for k, v in args.items() if k != '_index'}
                span = _tracer.start_span(
                    name=f"tool.{tool_name}",
                    attributes={
                        "tool.name": tool_name,
                        "tool.input": _safe_json(a, max_len=4000),
                    }
                )
                _tls.tstack.append(span)
            except Exception as e:
                logger.debug("otel_auto_trace: tool_before hook error: %s", e)
        if _orig_before:
            return _orig_before(self, tool_name, args, response)

    def _patched_after(self, tool_name, args, response, ret):
        _ensure_tracer()
        if _tracer is not None:
            try:
                if getattr(_tls, 'tstack', None):
                    span = _tls.tstack.pop()
                    out = None
                    if ret is not None:
                        out = {
                            'data': getattr(ret, 'data', None),
                            'next_prompt': getattr(ret, 'next_prompt', None),
                            'should_exit': getattr(ret, 'should_exit', None),
                        }
                    span.set_attribute("tool.output", _safe_json(out, max_len=4000))
                    span.end()
            except Exception as e:
                logger.debug("otel_auto_trace: tool_after hook error: %s", e)
        if _orig_after:
            return _orig_after(self, tool_name, args, response, ret)

    _BaseHandler.tool_before_callback = _patched_before
    _BaseHandler.tool_after_callback = _patched_after
    logger.info("otel_auto_trace: patched tool_before/after_callback")


# ── Hook 4: agent_runner_loop → Agent Task Span ──────────────────────────────

def _patch_agent_loop():
    """Monkey-patch agent_loop.agent_runner_loop 创建 agent task span"""
    try:
        import agent_loop
    except ImportError:
        return

    _orig_loop = getattr(agent_loop, 'agent_runner_loop', None)
    if _orig_loop is None:
        return

    def _patched_loop(client, system_prompt, user_input, handler, tools_schema, *a, **kw):
        _ensure_tracer()
        if _tracer is None:
            yield from _orig_loop(client, system_prompt, user_input, handler, tools_schema, *a, **kw)
            return

        with _tracer.start_as_current_span(
            name="agent.task",
            attributes={
                "agent.operation": "run",
                "agent.input": _safe_json(user_input, max_len=4000),
            }
        ) as span:
            start_time = time.time()
            try:
                result = yield from _orig_loop(client, system_prompt, user_input, handler, tools_schema, *a, **kw)
                duration_ms = (time.time() - start_time) * 1000
                span.set_attribute("agent.duration_ms", duration_ms)
                span.set_attribute("agent.status", "ok")
                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                span.set_attribute("agent.duration_ms", duration_ms)
                span.set_attribute("agent.status", "error")
                span.set_attribute("agent.error", str(e))
                raise

    agent_loop.agent_runner_loop = _patched_loop
    logger.info("otel_auto_trace: patched agent_runner_loop")


# ── Auto-activate on import ───────────────────────────────────────────────────

def activate():
    """手动激活所有 hooks（如果 mykey 中有 otel_config）"""
    _try_setup_tracer()
    if _tracer is None:
        return
    _patch_write_llm_log()
    _patch_raw_ask()
    _patch_tool_callbacks()
    _patch_agent_loop()
    logger.info("otel_auto_trace: all hooks activated")


# 导入时自动尝试激活（延迟到第一次 _ensure_tracer 调用时检查 mykey）
# 不立即 patch，等 llmcore.reload_mykeys 后由 activate() 或首次 LLM 调用触发
