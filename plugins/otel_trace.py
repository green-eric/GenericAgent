"""
OpenTelemetry LLM Call Tracer - @trace_llm_call decorator.

Usage:
    from plugins.otel_trace import trace_llm_call, setup_tracer

    setup_tracer(service_name="my-agent")

    @trace_llm_call(model="gpt-4o", operation="chat")
    def my_llm_call(messages, **kwargs):
        return openai.chat.completions.create(messages=messages, **kwargs)

Spans capture:
  - llm.model, llm.operation, llm.input.messages, llm.output.content
  - llm.usage.input_tokens/output_tokens/total_tokens
  - llm.error, duration_ms
"""

import time
import json
import functools
import logging
from typing import Optional, Callable, Any

logger = logging.getLogger(__name__)

_tracer_provider = None
_tracer = None
_initialized = False


def setup_tracer(service_name="ga-agent", exporter=None, resource_attrs=None):
    global _tracer_provider, _tracer, _initialized
    if _initialized:
        return
    try:
        from opentelemetry import trace as otel_trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.resources import Resource

        resource = Resource(attributes={"service.name": service_name})
        if resource_attrs:
            resource = resource.merge(Resource(attributes=resource_attrs))
        _tracer_provider = TracerProvider(resource=resource)
        if exporter is None:
            from opentelemetry.sdk.trace.export import ConsoleSpanExporter
            exporter = ConsoleSpanExporter()
        _tracer_provider.add_span_processor(BatchSpanProcessor(exporter))
        otel_trace.set_tracer_provider(_tracer_provider)
        _tracer = otel_trace.get_tracer(service_name)
        _initialized = True
        logger.info("OTel tracer initialized: service=%s", service_name)
    except ImportError as e:
        logger.warning("OTel SDK not available: %s. Tracing disabled.", e)
    except Exception as e:
        logger.error("OTel tracer init failed: %s", e)


def _ensure_tracer():
    global _initialized
    if not _initialized:
        setup_tracer()


def _safe_serialize(obj, max_len=2000):
    try:
        s = json.dumps(obj, ensure_ascii=False, default=str)
    except Exception:
        s = str(obj)
    if len(s) > max_len:
        s = s[:max_len] + "...[truncated]"
    return s


def _extract_usage(result):
    usage = {}
    try:
        u = getattr(result, "usage", None)
        if u:
            if hasattr(u, "prompt_tokens"):
                usage["input_tokens"] = u.prompt_tokens
                usage["output_tokens"] = u.completion_tokens
                usage["total_tokens"] = u.total_tokens
            elif isinstance(u, dict):
                usage["input_tokens"] = u.get("input_tokens", u.get("prompt_tokens", 0))
                usage["output_tokens"] = u.get("output_tokens", u.get("completion_tokens", 0))
                usage["total_tokens"] = u.get("total_tokens", 0)
    except Exception:
        pass
    return usage


def _extract_content(result):
    try:
        choices = getattr(result, "choices", None)
        if choices:
            msg = getattr(choices[0], "message", None)
            if msg:
                return getattr(msg, "content", "") or ""
        if isinstance(result, str):
            return result
        if isinstance(result, dict):
            return result.get("content", result.get("text", str(result)))
    except Exception:
        pass
    return str(result) if result else ""


def trace_llm_call(model="unknown", operation="chat", capture_input=True,
                   capture_output=True, max_field_len=2000):
    """Decorator that wraps an LLM call with an OpenTelemetry span."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            _ensure_tracer()
            if not _tracer:
                return func(*args, **kwargs)

            span_attrs = {
                "llm.model": model,
                "llm.operation": operation,
                "function.name": func.__qualname__,
            }
            if capture_input:
                input_data = args[0] if args else kwargs.get("messages", kwargs.get("prompt", ""))
                span_attrs["llm.input.messages"] = _safe_serialize(input_data, max_field_len)

            start = time.monotonic()
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.monotonic() - start) * 1000
                if capture_output:
                    span_attrs["llm.output.content"] = _safe_serialize(_extract_content(result), max_field_len)
                for k, v in _extract_usage(result).items():
                    span_attrs["llm.usage.{}".format(k)] = v
                span_attrs["duration_ms"] = round(duration_ms, 2)
                with _tracer.start_as_current_span("llm.{}.{}".format(operation, model),
                                                   attributes=span_attrs) as span:
                    span.set_attribute("llm.success", True)
                return result
            except Exception as e:
                duration_ms = (time.monotonic() - start) * 1000
                span_attrs["llm.error"] = "{}: {}".format(type(e).__name__, e)
                span_attrs["llm.success"] = False
                span_attrs["duration_ms"] = round(duration_ms, 2)
                with _tracer.start_as_current_span("llm.{}.{}".format(operation, model),
                                                   attributes=span_attrs) as span:
                    span.set_attribute("llm.success", False)
                    span.set_attribute("llm.error", str(e))
                raise
        return wrapper
    return decorator


def get_tracer():
    _ensure_tracer()
    return _tracer


def get_tracer_provider():
    return _tracer_provider


def shutdown():
    global _initialized
    if _tracer_provider and _initialized:
        try:
            _tracer_provider.force_flush(timeout_millis=5000)
            _tracer_provider.shutdown()
            logger.info("OTel tracer shutdown complete.")
        except Exception as e:
            logger.error("OTel shutdown error: %s", e)
    _initialized = False


class llm_span:
    """Context manager for manual LLM span creation."""
    def __init__(self, model="unknown", operation="chat", **attrs):
        self.model = model
        self.operation = operation
        self.attrs = attrs
        self._span = None
        self._ctx = None

    def __enter__(self):
        _ensure_tracer()
        if _tracer:
            all_attrs = {"llm.model": self.model, "llm.operation": self.operation}
            all_attrs.update(self.attrs)
            self._ctx = _tracer.start_as_current_span(
                "llm.{}.{}".format(self.operation, self.model),
                attributes=all_attrs)
            self._span = self._ctx.__enter__()
        return self._span

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._ctx:
            if exc_val:
                self._span.set_attribute("llm.error", str(exc_val))
                self._span.set_attribute("llm.success", False)
            else:
                self._span.set_attribute("llm.success", True)
            return self._ctx.__exit__(exc_type, exc_val, exc_tb)
        return False
