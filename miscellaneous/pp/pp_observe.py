import inspect
import json
import os
from functools import wraps
from typing import Any, Callable, Dict, Optional
 
 
def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except Exception:
        return default
 
 
_MAX_LEN = _env_int("PP_OBSERVE_MAX_LEN", 8192)
 
 
def _truncate(s: str) -> str:
    if len(s) <= _MAX_LEN:
        return s
    return s[: _MAX_LEN - 12] + "...(truncated)"
 
 
def _to_jsonable(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, "model_dump") and callable(getattr(value, "model_dump")):
        try:
            return value.model_dump()
        except Exception:
            pass
    if hasattr(value, "dict") and callable(getattr(value, "dict")):
        try:
            return value.dict()
        except Exception:
            pass
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    return str(value)
 
 
def _to_attr_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        if isinstance(value, str):
            return _truncate(value)
        return value
    if isinstance(value, (list, tuple)):
        out = []
        for v in value:
            if isinstance(v, (str, int, float, bool)):
                out.append(_truncate(v) if isinstance(v, str) else v)
            else:
                out.append(_truncate(json.dumps(_to_jsonable(v), ensure_ascii=False)))
        return out
    if isinstance(value, dict) or hasattr(value, "model_dump") or hasattr(value, "dict"):
        return _truncate(json.dumps(_to_jsonable(value), ensure_ascii=False))
    return _truncate(str(value))
 
 
class _SpanAdapter:
    def __init__(self, span: Any):
        self._span = span
 
    def set_tags(self, tags: Dict[str, Any]):
        if not tags:
            return
        for k, v in tags.items():
            try:
                self._span.set_attribute(str(k), _to_attr_value(v))
            except Exception:
                continue

    def to_header(self) -> Dict[str, str]:
        try:
            from opentelemetry.propagate import inject

            carrier: Dict[str, str] = {}
            inject(carrier)
            if "traceparent" in carrier:
                carrier["X-Cozeloop-Traceparent"] = carrier["traceparent"]
            return carrier
        except Exception:
            return {}
 
    def __getattr__(self, item: str):
        return getattr(self._span, item)
 
 
def _get_tracer():
    try:
        from opentelemetry import trace
 
        return trace.get_tracer("automas.pp_observe")
    except Exception:
        return None
 
 
def get_span_from_context():
    try:
        try:
            from .pp_tracing import init_tracing
 
            init_tracing()
        except Exception:
            pass
        from opentelemetry import trace
 
        return _SpanAdapter(trace.get_current_span())
    except Exception:
        return _SpanAdapter(_NoopSpan())
 
 
def flush():
    try:
        try:
            from .pp_tracing import force_flush
 
            force_flush()
            return
        except Exception:
            pass
        from opentelemetry import trace
 
        provider = trace.get_tracer_provider()
        force_flush = getattr(provider, "force_flush", None)
        if callable(force_flush):
            force_flush()
    except Exception:
        return
 
 
class _NoopSpan:
    def set_attribute(self, *args, **kwargs):
        return
 
    def add_event(self, *args, **kwargs):
        return
 
    def record_exception(self, *args, **kwargs):
        return
 
    def set_status(self, *args, **kwargs):
        return
 
 
def observe(
    func: Callable = None,
    *,
    name: Optional[str] = None,
    span_type: Optional[str] = None,
    tags: Optional[Dict[str, Any]] = None,
    baggage: Optional[Dict[str, str]] = None,
    client: Any = None,
    process_inputs: Optional[Callable[[dict], Any]] = None,
    process_outputs: Optional[Callable[[Any], Any]] = None,
    process_iterator_outputs: Optional[Callable[[Any], Any]] = None,
):
    span_type = span_type or "custom"

    def decorator(target: Callable):
        enabled_wrapper = None

        def _build_wrapper():
            tracer = None
            if client is not None and hasattr(client, "start_as_current_span"):
                tracer = client
            if tracer is None:
                tracer = _get_tracer()
            if tracer is None:
                return target

            func_name = name or getattr(target, "__name__", "function")

            span_kind = None
            try:
                from opentelemetry.trace import SpanKind

                span_kind = SpanKind.INTERNAL
            except Exception:
                span_kind = None

            def _is_method_call(call_args: tuple) -> bool:
                if not call_args:
                    return False
                first = call_args[0]
                try:
                    attr = getattr(first, getattr(target, "__name__", ""), None)
                    return callable(attr)
                except Exception:
                    return False

            def _build_input(call_args: tuple, call_kwargs: dict) -> Dict[str, Any]:
                args = call_args
                if _is_method_call(args):
                    args = args[1:]
                return {"args": args, "kwargs": call_kwargs}

            def _set_base_attributes(span_obj: Any):
                try:
                    span_obj.set_attribute("pp.span_type", _to_attr_value(span_type))
                except Exception:
                    pass
                try:
                    span_obj.set_attribute(
                        "pp.func",
                        f"{target.__module__}.{getattr(target, '__qualname__', target.__name__)}",
                    )
                except Exception:
                    pass
                if tags:
                    for k, v in (tags or {}).items():
                        try:
                            span_obj.set_attribute(str(k), _to_attr_value(v))
                        except Exception:
                            continue

            def _set_input(span_obj: Any, call_args: tuple, call_kwargs: dict):
                payload: Any = _build_input(call_args, call_kwargs)
                if process_inputs:
                    payload = process_inputs(payload)
                try:
                    span_obj.set_attribute("pp.input", _to_attr_value(payload))
                except Exception:
                    pass

            def _set_output(span_obj: Any, output: Any, *, iterator_mode: bool = False):
                payload: Any = output
                if iterator_mode and process_iterator_outputs:
                    payload = process_iterator_outputs(payload)
                elif process_outputs:
                    payload = process_outputs(payload)
                try:
                    span_obj.set_attribute("pp.output", _to_attr_value(payload))
                except Exception:
                    pass

            def _mark_trace_id(span_obj: Any):
                try:
                    from .pp_tracing import set_last_trace_id_hex

                    trace_id = getattr(span_obj.get_span_context(), "trace_id", 0)
                    if trace_id:
                        set_last_trace_id_hex(f"{trace_id:032x}")
                except Exception:
                    pass

            def _set_baggage():
                if not baggage:
                    return None
                try:
                    from opentelemetry import baggage as otel_baggage
                    from opentelemetry.context import attach, get_current

                    ctx = get_current()
                    for k, v in (baggage or {}).items():
                        ctx = otel_baggage.set_baggage(str(k), str(v), ctx)
                    return attach(ctx)
                except Exception:
                    return None

            def _detach_baggage(token):
                if token is None:
                    return
                try:
                    from opentelemetry.context import detach

                    detach(token)
                except Exception:
                    return

            class _IteratorTraceWrapper:
                def __init__(self, it, span_obj: Any, ctx_tokens: list[Any]):
                    self._it = it
                    self._span = span_obj
                    self._tokens = [t for t in (ctx_tokens or []) if t is not None]
                    self._items = []
                    self._closed = False

                def __iter__(self):
                    return self

                def __next__(self):
                    try:
                        item = next(self._it)
                        self._items.append(item)
                        return item
                    except StopIteration:
                        self._finish()
                        raise
                    except Exception as e:
                        try:
                            self._span.record_exception(e)
                        except Exception:
                            pass
                        try:
                            from opentelemetry.trace.status import Status, StatusCode

                            self._span.set_status(Status(StatusCode.ERROR))
                        except Exception:
                            pass
                        self._finish(iterator_mode=True)
                        raise

                def close(self):
                    try:
                        close_fn = getattr(self._it, "close", None)
                        if callable(close_fn):
                            close_fn()
                    finally:
                        self._finish()

                def _finish(self, iterator_mode: bool = True):
                    if self._closed:
                        return
                    self._closed = True
                    try:
                        _set_output(self._span, list(self._items), iterator_mode=iterator_mode)
                    finally:
                        try:
                            self._span.end()
                        except Exception:
                            pass
                        try:
                            from opentelemetry.context import detach

                            for token in reversed(self._tokens):
                                detach(token)
                        except Exception:
                            pass

            class _AsyncIteratorTraceWrapper:
                def __init__(self, it, span_obj: Any, ctx_tokens: list[Any]):
                    self._it = it
                    self._span = span_obj
                    self._tokens = [t for t in (ctx_tokens or []) if t is not None]
                    self._items = []
                    self._closed = False

                def __aiter__(self):
                    return self

                async def __anext__(self):
                    try:
                        item = await self._it.__anext__()
                        self._items.append(item)
                        return item
                    except StopAsyncIteration:
                        await self._finish()
                        raise
                    except Exception as e:
                        try:
                            self._span.record_exception(e)
                        except Exception:
                            pass
                        try:
                            from opentelemetry.trace.status import Status, StatusCode

                            self._span.set_status(Status(StatusCode.ERROR))
                        except Exception:
                            pass
                        await self._finish(iterator_mode=True)
                        raise

                async def aclose(self):
                    try:
                        close_fn = getattr(self._it, "aclose", None)
                        if callable(close_fn):
                            await close_fn()
                    finally:
                        await self._finish()

                async def _finish(self, iterator_mode: bool = True):
                    if self._closed:
                        return
                    self._closed = True
                    try:
                        _set_output(self._span, list(self._items), iterator_mode=iterator_mode)
                    finally:
                        try:
                            self._span.end()
                        except Exception:
                            pass
                        try:
                            from opentelemetry.context import detach

                            for token in reversed(self._tokens):
                                detach(token)
                        except Exception:
                            pass

            @wraps(target)
            def sync_wrapper(*args: Any, **kwargs: Any):
                baggage_token = _set_baggage()
                try:
                    if span_kind is None:
                        ctx_mgr = tracer.start_as_current_span(func_name)
                    else:
                        ctx_mgr = tracer.start_as_current_span(func_name, kind=span_kind)
                    with ctx_mgr as span_obj:
                        _mark_trace_id(span_obj)
                        _set_base_attributes(span_obj)
                        res = None
                        try:
                            res = target(*args, **kwargs)
                            _set_output(span_obj, res)
                            return res
                        except StopIteration:
                            return res
                        except Exception as e:
                            try:
                                span_obj.record_exception(e)
                            except Exception:
                                pass
                            try:
                                from opentelemetry.trace.status import Status, StatusCode

                                span_obj.set_status(Status(StatusCode.ERROR))
                            except Exception:
                                pass
                            raise
                        finally:
                            _set_input(span_obj, args, kwargs)
                finally:
                    _detach_baggage(baggage_token)

            @wraps(target)
            async def async_wrapper(*args: Any, **kwargs: Any):
                baggage_token = _set_baggage()
                try:
                    if span_kind is None:
                        ctx_mgr = tracer.start_as_current_span(func_name)
                    else:
                        ctx_mgr = tracer.start_as_current_span(func_name, kind=span_kind)
                    with ctx_mgr as span_obj:
                        _mark_trace_id(span_obj)
                        _set_base_attributes(span_obj)
                        res = None
                        try:
                            res = await target(*args, **kwargs)
                            _set_output(span_obj, res)
                            return res
                        except StopAsyncIteration:
                            return res
                        except Exception as e:
                            if e.args and e.args[0] == "coroutine raised StopIteration":
                                return res
                            try:
                                span_obj.record_exception(e)
                            except Exception:
                                pass
                            try:
                                from opentelemetry.trace.status import Status, StatusCode

                                span_obj.set_status(Status(StatusCode.ERROR))
                            except Exception:
                                pass
                            raise
                        finally:
                            _set_input(span_obj, args, kwargs)
                finally:
                    _detach_baggage(baggage_token)

            @wraps(target)
            def sync_stream_wrapper(*args: Any, **kwargs: Any):
                baggage_token = _set_baggage()
                try:
                    if span_kind is None:
                        span_obj = tracer.start_span(func_name)
                    else:
                        span_obj = tracer.start_span(func_name, kind=span_kind)
                except Exception:
                    _detach_baggage(baggage_token)
                    return sync_wrapper(*args, **kwargs)
                ctx_tokens: list[Any] = []
                try:
                    _mark_trace_id(span_obj)
                    _set_base_attributes(span_obj)
                    _set_input(span_obj, args, kwargs)
                    try:
                        from opentelemetry import trace as otel_trace
                        from opentelemetry.context import attach

                        ctx_tokens.append(attach(otel_trace.set_span_in_context(span_obj)))
                    except Exception:
                        pass
                    res = target(*args, **kwargs)
                    if hasattr(res, "__iter__"):
                        return _IteratorTraceWrapper(iter(res), span_obj, [baggage_token] + ctx_tokens)
                    _set_output(span_obj, res)
                    return res
                except Exception as e:
                    try:
                        span_obj.record_exception(e)
                    except Exception:
                        pass
                    try:
                        from opentelemetry.trace.status import Status, StatusCode

                        span_obj.set_status(Status(StatusCode.ERROR))
                    except Exception:
                        pass
                    raise
                finally:
                    if not hasattr(locals().get("res", None), "__iter__"):
                        try:
                            span_obj.end()
                        except Exception:
                            pass
                        for token in reversed(ctx_tokens):
                            try:
                                from opentelemetry.context import detach

                                detach(token)
                            except Exception:
                                pass
                        _detach_baggage(baggage_token)

            @wraps(target)
            async def async_stream_wrapper(*args: Any, **kwargs: Any):
                baggage_token = _set_baggage()
                try:
                    if span_kind is None:
                        span_obj = tracer.start_span(func_name)
                    else:
                        span_obj = tracer.start_span(func_name, kind=span_kind)
                except Exception:
                    _detach_baggage(baggage_token)
                    return await async_wrapper(*args, **kwargs)
                ctx_tokens: list[Any] = []
                res = None
                try:
                    _mark_trace_id(span_obj)
                    _set_base_attributes(span_obj)
                    _set_input(span_obj, args, kwargs)
                    try:
                        from opentelemetry import trace as otel_trace
                        from opentelemetry.context import attach

                        ctx_tokens.append(attach(otel_trace.set_span_in_context(span_obj)))
                    except Exception:
                        pass
                    res = await target(*args, **kwargs)
                    if hasattr(res, "__aiter__"):
                        return _AsyncIteratorTraceWrapper(res.__aiter__(), span_obj, [baggage_token] + ctx_tokens)
                    _set_output(span_obj, res)
                    return res
                except Exception as e:
                    if e.args and e.args[0] == "coroutine raised StopIteration":
                        return res
                    try:
                        span_obj.record_exception(e)
                    except Exception:
                        pass
                    try:
                        from opentelemetry.trace.status import Status, StatusCode

                        span_obj.set_status(Status(StatusCode.ERROR))
                    except Exception:
                        pass
                    raise
                finally:
                    if not hasattr(res, "__aiter__"):
                        try:
                            span_obj.end()
                        except Exception:
                            pass
                        for token in reversed(ctx_tokens):
                            try:
                                from opentelemetry.context import detach

                                detach(token)
                            except Exception:
                                pass
                        _detach_baggage(baggage_token)

            @wraps(target)
            def gen_wrapper(*args: Any, **kwargs: Any):
                baggage_token = _set_baggage()
                try:
                    if span_kind is None:
                        ctx_mgr = tracer.start_as_current_span(func_name)
                    else:
                        ctx_mgr = tracer.start_as_current_span(func_name, kind=span_kind)
                    with ctx_mgr as span_obj:
                        _mark_trace_id(span_obj)
                        _set_base_attributes(span_obj)
                        items = []
                        try:
                            gen = target(*args, **kwargs)
                            for item in gen:
                                items.append(item)
                                yield item
                        finally:
                            try:
                                _set_output(span_obj, list(items), iterator_mode=False)
                            finally:
                                _set_input(span_obj, args, kwargs)
                finally:
                    _detach_baggage(baggage_token)

            @wraps(target)
            async def async_gen_wrapper(*args: Any, **kwargs: Any):
                baggage_token = _set_baggage()
                try:
                    if span_kind is None:
                        ctx_mgr = tracer.start_as_current_span(func_name)
                    else:
                        ctx_mgr = tracer.start_as_current_span(func_name, kind=span_kind)
                    with ctx_mgr as span_obj:
                        _mark_trace_id(span_obj)
                        _set_base_attributes(span_obj)
                        items = []
                        try:
                            gen = target(*args, **kwargs)
                            async for item in gen:
                                items.append(item)
                                yield item
                        finally:
                            try:
                                _set_output(span_obj, list(items), iterator_mode=False)
                            finally:
                                _set_input(span_obj, args, kwargs)
                finally:
                    _detach_baggage(baggage_token)

            if inspect.isasyncgenfunction(target):
                return async_gen_wrapper
            if inspect.isgeneratorfunction(target):
                return gen_wrapper
            if inspect.iscoroutinefunction(target):
                if process_iterator_outputs:
                    return async_stream_wrapper
                return async_wrapper
            if process_iterator_outputs:
                return sync_stream_wrapper
            return sync_wrapper

        @wraps(target)
        def call(*args: Any, **kwargs: Any):
            nonlocal enabled_wrapper
            if os.getenv("AUTOMAS_ENABLE_OBSERVE", "0") == "1":
                if enabled_wrapper is None:
                    try:
                        from .pp_tracing import init_tracing

                        init_tracing()
                    except Exception:
                        pass
                    enabled_wrapper = _build_wrapper()
                return enabled_wrapper(*args, **kwargs)
            return target(*args, **kwargs)

        return call

    if func is None:
        return decorator
    return decorator(func)
