"""
GenAI Telemetry - Observability SDK for LLM Applications
=========================================================

A platform-agnostic telemetry library for tracing GenAI/LLM applications.
Supports multiple backends: Splunk, Elasticsearch, OpenTelemetry, Datadog,
Prometheus, Grafana Loki, AWS CloudWatch, and more.

Usage:
    from genai_telemetry import setup_telemetry, trace_llm
    
    # Splunk
    setup_telemetry(
        workflow_name="my-app",
        exporter="splunk",
        splunk_url="http://splunk:8088",
        splunk_token="your-token"
    )
    
    # Elasticsearch
    setup_telemetry(
        workflow_name="my-app",
        exporter="elasticsearch",
        es_hosts=["http://localhost:9200"]
    )
    
    # OpenTelemetry (Datadog, Jaeger, etc.)
    setup_telemetry(
        workflow_name="my-app",
        exporter="otlp",
        otlp_endpoint="http://localhost:4317"
    )
    
    @trace_llm(model_name="gpt-4o", model_provider="openai")
    def chat(message):
        return client.chat.completions.create(...)

Author: Kamal Singh Bisht
License: Apache-2.0
"""

__version__ = "1.0.3"
__author__ = "Kamal Singh Bisht"

# Core components
from genai_telemetry.core.telemetry import (
    GenAITelemetry,
    setup_telemetry,
    get_telemetry,
)
from genai_telemetry.core.span import Span
from genai_telemetry.core.decorators import (
    trace_llm,
    trace_embedding,
    trace_retrieval,
    trace_tool,
    trace_chain,
    trace_agent,
)
from genai_telemetry.core.utils import (
    extract_tokens_from_response,
    extract_content_from_response,
)

# Base exporter
from genai_telemetry.exporters.base import BaseExporter

# All exporters
from genai_telemetry.exporters.splunk import SplunkHECExporter
from genai_telemetry.exporters.elasticsearch import ElasticsearchExporter
from genai_telemetry.exporters.otlp import OTLPExporter
from genai_telemetry.exporters.datadog import DatadogExporter
from genai_telemetry.exporters.prometheus import PrometheusExporter
from genai_telemetry.exporters.loki import LokiExporter
from genai_telemetry.exporters.cloudwatch import CloudWatchExporter
from genai_telemetry.exporters.console import ConsoleExporter
from genai_telemetry.exporters.file import FileExporter
from genai_telemetry.exporters.multi import MultiExporter

__all__ = [
    # Version
    "__version__",
    "__author__",
    
    # Setup
    "setup_telemetry",
    "get_telemetry",
    "GenAITelemetry",
    "Span",
    
    # Decorators
    "trace_llm",
    "trace_embedding",
    "trace_retrieval",
    "trace_tool",
    "trace_chain",
    "trace_agent",
    
    # Exporters
    "BaseExporter",
    "SplunkHECExporter",
    "ElasticsearchExporter",
    "OTLPExporter",
    "DatadogExporter",
    "PrometheusExporter",
    "LokiExporter",
    "CloudWatchExporter",
    "ConsoleExporter",
    "FileExporter",
    "MultiExporter",
    
    # Helper functions
    "extract_tokens_from_response",
    "extract_content_from_response",
]
