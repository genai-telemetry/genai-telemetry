"""
GenAI Telemetry Auto-Instrumentation Module.

This module provides zero-code instrumentation for popular LLM frameworks.

Supported frameworks:
- OpenAI Python SDK (openai)
- Anthropic Python SDK (anthropic)
- LangChain / LangChain-Core
- LlamaIndex
- CrewAI (coming soon)
- AutoGen (coming soon)
- Haystack (coming soon)

Usage:
    from genai_telemetry import setup_telemetry, auto_instrument

    # 1. Setup telemetry first
    setup_telemetry(
        workflow_name="my-app",
        exporter="splunk",
        splunk_url="http://splunk:8088",
        splunk_token="your-token"
    )

    # 2. Enable auto-instrumentation
    auto_instrument()

    # 3. Use your LLM libraries normally - they're now traced!
    from openai import OpenAI
    client = OpenAI()
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": "Hello!"}]
    )
    # ^ This call is automatically traced and sent to your backend!
"""

from genai_telemetry.instrumentation.auto import (
    auto_instrument,
    uninstrument,
    get_instrumented_frameworks,
    is_instrumented,
    instrument,
    instrument_all,
)

from genai_telemetry.instrumentation.base import BaseInstrumentor

__all__ = [
    # Main functions
    "auto_instrument",
    "uninstrument",
    "get_instrumented_frameworks",
    "is_instrumented",
    
    # Aliases
    "instrument",
    "instrument_all",
    
    # Base class (for custom instrumentors)
    "BaseInstrumentor",
]
