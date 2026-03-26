import os
from typing import Any, Callable, Optional, Dict

try:
    from opentelemetry import trace as ot_trace
except Exception:
    ot_trace = None
try:
    from cozeloop.decorator import observe as cozeloop_observe
    from cozeloop import get_span_from_context as cozeloop_get_span_from_context
except Exception:
    cozeloop_observe = None
    cozeloop_get_span_from_context = None

try:
    from miscellaneous.pp.observe import observe as pp_observe
except Exception:
    pp_observe = None


class _SpanAdapter:
    def __init__(self, span: Any) -> None:
        self._span = span

    def set_attribute(self, key: str, value: Any) -> None:
        if hasattr(self._span, "set_attribute"):
            self._span.set_attribute(key, value)
            return
        if hasattr(self._span, "set_tags"):
            self._span.set_tags({key: value})
            return

    def __getattr__(self, name: str) -> Any:
        return getattr(self._span, name)
    

class _NoopSpanContext:
    @property
    def is_valid(self) -> bool:
        return False

    @property
    def trace_id(self) -> int:
        return 0


class _NoopSpan:
    def set_attribute(self, key: str, value: Any) -> None:
        return

    def get_span_context(self) -> Any:
        return _NoopSpanContext()



def _trace_provider() -> str:
    provider = os.getenv("AUTOMAS_TRACE_PROVIDER", "promptpilot")
    provider = provider.lower().strip()
    if provider == "promptpliot":
        provider = "promptpilot"
    return provider


def observe(*args, **kwargs):
    provider = _trace_provider()
    if provider == "cozeloop":
        if cozeloop_observe is None:
            raise RuntimeError("AUTOMAS_TRACE_PROVIDER=cozeloop but cozeloop is not installed")
        return cozeloop_observe(*args, **kwargs)

    if pp_observe is None:
        raise RuntimeError("AUTOMAS_TRACE_PROVIDER=promptpilot but pp observe is not available")

    filtered = dict(kwargs)
    filtered.pop("baggage", None)
    filtered.pop("process_iterator_outputs", None)
    filtered.pop("client", None)
    return pp_observe(*args, **filtered)


def get_span_from_context() -> Any:
    provider = _trace_provider()
    if provider == "cozeloop":
        if cozeloop_get_span_from_context is None:
            raise RuntimeError("AUTOMAS_TRACE_PROVIDER=cozeloop but cozeloop is not installed")
        return _SpanAdapter(cozeloop_get_span_from_context())
    if ot_trace is None:
        return _NoopSpan()
    return ot_trace.get_current_span()


def get_trace_id() -> str:
    provider = _trace_provider()
    span = get_span_from_context()
    if provider == "cozeloop":
        header = span.to_header()
        traceparent = header.get("X-Cozeloop-Traceparent", "")
        parts = traceparent.split("-")
        if len(parts) >= 2:
            return parts[1]
        return ""

    ctx = span.get_span_context()
    if not ctx.is_valid:
        return ""
    return f"{ctx.trace_id:032x}"
