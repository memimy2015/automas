import os
import threading
from typing import Optional, Dict
from openinference.instrumentation.openai import OpenAIInstrumentor
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter, SimpleSpanProcessor
from functools import wraps

_lock = threading.Lock()
_initialized = False
_instrumented = False


def init_tracing(
    *,
    endpoint: Optional[str] = None,
    headers: Optional[Dict[str, str]] = None,
    enable_openai_instrumentation: Optional[bool] = None,
) -> None:
    global _initialized, _instrumented

    if _initialized:
        return

    with _lock:
        if _initialized:
            return

        if endpoint is None:
            api_url = os.environ.get("AGENTPILOT_API_URL")
            if not api_url:
                return
            endpoint = f"{api_url}/pilot-studio/telemetry/traces"

        if headers is None:
            headers = {
                "X-Project-Id": os.environ.get("AGENTPILOT_PROJECT_ID", ""),
                "Authorization": f"Bearer {os.environ.get('AGENTPILOT_API_KEY', '')}",
            }

        provider = TracerProvider()
        provider.add_span_processor(
            # BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint, headers=headers))
            SimpleSpanProcessor(OTLPSpanExporter(endpoint=endpoint, headers=headers))
        )

        trace.set_tracer_provider(provider)

        if enable_openai_instrumentation and not _instrumented:
            OpenAIInstrumentor().instrument(tracer_provider=provider)
            _instrumented = True

        _initialized = True


def get_tracer(name: str = "automas.agent"):
    init_tracing()
    return trace.get_tracer(name)


def get_span_from_context():
    return trace.get_current_span()
