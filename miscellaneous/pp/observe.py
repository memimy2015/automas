import json
import os
import time
from functools import wraps
from typing import Any, Callable, Dict, Optional

from opentelemetry import trace

from .telemetry import get_tracer, init_tracing


def _jsonify(value: Any) -> str:
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False, default=str)
    except Exception:
        return json.dumps(str(value), ensure_ascii=False)


def _set_metadata(span: trace.Span, data: Optional[Dict[str, Any]]) -> None:
    if not data:
        return
    for k, v in data.items():
        span.set_attribute(f"metadata.{k}", _jsonify(v))

def _default_process_inputs(inputs: dict) -> dict:
    return inputs

def _default_process_outputs(outputs: Any) -> Any:
    return outputs

def observe(
    func: Optional[Callable] = None,
    *,
    name: Optional[str] = None,
    span_type: Optional[str] = None, # metadata
    tags: Optional[Dict[str, Any]] = None, # metadata
    process_inputs: Optional[Callable[[dict], Any]] = None, 
    process_outputs: Optional[Callable[[Any], Any]] = None,
    **_unused: Any,
) -> Callable:
    name = name or "default_name"
    span_type = span_type or "custom"
    process_inputs = process_inputs or _default_process_inputs
    process_outputs = process_outputs or _default_process_outputs
    
    def decorator(f: Callable):
        enabled_wrapper = None

        def build_enabled_wrapper():
            init_tracing()

            @wraps(f)
            def wrapped(*args: Any, **kwargs: Any):
                tracer = get_tracer()
                with tracer.start_as_current_span(name) as span:
                    start_ts = time.perf_counter()
                    _set_metadata(span, tags)
                    _set_metadata(span, {"span_type": span_type, "name": name})

                    if process_inputs:
                        inputs = process_inputs({"args": args, "kwargs": kwargs})
                        span.set_attribute("input.value", _jsonify(inputs))

                    try:
                        res = f(*args, **kwargs)
                    finally:
                        delta_minutes = (time.perf_counter() - start_ts) / 60.0
                        span.set_attribute("metadata.time_delta(min)", f"{delta_minutes:.4f}")

                    if process_outputs:
                        outputs = process_outputs(res)
                        span.set_attribute("output.value", _jsonify(outputs))

                    return res

            return wrapped

        @wraps(f)
        def call(*args: Any, **kwargs: Any):
            nonlocal enabled_wrapper
            if os.getenv("AUTOMAS_ENABLE_OBSERVE", "0") == "1":
                if enabled_wrapper is None:
                    enabled_wrapper = build_enabled_wrapper()
                return enabled_wrapper(*args, **kwargs)
            return f(*args, **kwargs)

        return call

    return decorator(func) if func is not None else decorator
