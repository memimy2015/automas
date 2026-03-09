import os
from typing import Any, Dict, Optional


_INITIALIZED = False
_LAST_TRACE_ID_HEX: Optional[str] = None


def _parse_headers(raw: Optional[str]) -> Dict[str, str]:
    if not raw:
        return {}
    out: Dict[str, str] = {}
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if "=" in part:
            k, v = part.split("=", 1)
            out[k.strip()] = v.strip()
        elif ":" in part:
            k, v = part.split(":", 1)
            out[k.strip()] = v.strip()
    return out


def init_tracing(
    *,
    service_name: Optional[str] = None,
    endpoint: Optional[str] = None,
    protocol: Optional[str] = None,
    headers: Optional[Dict[str, str]] = None,
) -> bool:
    global _INITIALIZED
    if _INITIALIZED:
        return True
    if os.environ.get("AUTOMAS_ENABLE_OBSERVE", "0") != "1":
        return False
    try:
        from opentelemetry import trace
        from opentelemetry.propagate import set_global_textmap
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
        from opentelemetry.baggage.propagation import W3CBaggagePropagator
        from opentelemetry.propagators.composite import CompositePropagator
    except Exception:
        return False
 
    try:
        from opentelemetry.trace import ProxyTracerProvider
 
        existing = trace.get_tracer_provider()
        if existing is not None and not isinstance(existing, ProxyTracerProvider):
            _INITIALIZED = True
            return True
    except Exception:
        pass

    svc = (
        service_name
        or os.environ.get("OTEL_SERVICE_NAME")
        or os.environ.get("OTEL_RESOURCE_ATTRIBUTES", "").split("service.name=", 1)[-1]
        or "automas"
    )
    res_attrs: Dict[str, Any] = {"service.name": svc}
    resource_attrs_raw = os.environ.get("OTEL_RESOURCE_ATTRIBUTES")
    if resource_attrs_raw:
        for part in resource_attrs_raw.split(","):
            if not part.strip() or "=" not in part:
                continue
            k, v = part.split("=", 1)
            res_attrs[k.strip()] = v.strip()

    provider = TracerProvider(resource=Resource.create(res_attrs))

    proto = (protocol or os.environ.get("OTEL_EXPORTER_OTLP_PROTOCOL") or "grpc").lower()
    ep = endpoint or os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT") or os.environ.get("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT")
    hdrs = dict(headers or {})
    if not hdrs:
        hdrs = _parse_headers(os.environ.get("OTEL_EXPORTER_OTLP_HEADERS") or os.environ.get("OTEL_EXPORTER_OTLP_TRACES_HEADERS"))

    exporter = None
    if proto in ("http/protobuf", "http"):
        try:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

            exporter = OTLPSpanExporter(endpoint=ep, headers=hdrs or None)
        except Exception:
            exporter = None
    else:
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

            exporter = OTLPSpanExporter(endpoint=ep, headers=hdrs or None)
        except Exception:
            exporter = None

    if exporter is None:
        return False

    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    set_global_textmap(CompositePropagator([TraceContextTextMapPropagator(), W3CBaggagePropagator()]))

    _INITIALIZED = True
    return True


def force_flush() -> None:
    try:
        from opentelemetry import trace

        provider = trace.get_tracer_provider()
        fn = getattr(provider, "force_flush", None)
        if callable(fn):
            fn()
    except Exception:
        return


def shutdown() -> None:
    try:
        from opentelemetry import trace

        provider = trace.get_tracer_provider()
        fn = getattr(provider, "shutdown", None)
        if callable(fn):
            fn()
    except Exception:
        return


def set_last_trace_id_hex(trace_id_hex: Optional[str]) -> None:
    global _LAST_TRACE_ID_HEX
    if not trace_id_hex:
        return
    _LAST_TRACE_ID_HEX = trace_id_hex


def get_last_trace_id_hex() -> Optional[str]:
    return _LAST_TRACE_ID_HEX


def get_trace_id_hex() -> Optional[str]:
    global _LAST_TRACE_ID_HEX
    try:
        from opentelemetry import trace

        span = trace.get_current_span()
        ctx = span.get_span_context()
        if not ctx or not getattr(ctx, "is_valid", False):
            return _LAST_TRACE_ID_HEX
        trace_id = f"{ctx.trace_id:032x}"
        _LAST_TRACE_ID_HEX = trace_id
        return trace_id
    except Exception:
        return _LAST_TRACE_ID_HEX
