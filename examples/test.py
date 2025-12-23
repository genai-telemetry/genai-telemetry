#!/usr/bin/env python3
"""
GenAI Telemetry - Observability SDK for LLM Applications
===================================================================

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
License: MIT

CHANGELOG v1.0.3:
    - Fixed token extraction to work even when returning response.choices[0].message.content
    - Added automatic OpenAI/Anthropic client response interception
    - Added extract_content parameter to automatically extract content while preserving token counts
"""

__version__ = "1.0.3"
__author__ = "Kamal Singh Bisht"

import json
import time
import uuid
import urllib.request
import urllib.error
import ssl
import threading
import logging
import atexit
import os
from functools import wraps
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Callable, Union
from contextlib import contextmanager
from abc import ABC, abstractmethod

logger = logging.getLogger("genai_telemetry")


# =============================================================================
# TOKEN EXTRACTION HELPERS
# =============================================================================

def _extract_tokens_from_response(response: Any) -> tuple:
    """
    Extract input/output tokens from various LLM response formats.
    
    Supports:
    - OpenAI ChatCompletion responses
    - OpenAI Completion responses
    - Anthropic Message responses
    - Dict responses
    
    Returns:
        tuple: (input_tokens, output_tokens)
    """
    input_tokens = 0
    output_tokens = 0
    
    # OpenAI ChatCompletion / Completion response object
    if hasattr(response, "usage") and response.usage is not None:
        input_tokens = getattr(response.usage, "prompt_tokens", 0) or 0
        output_tokens = getattr(response.usage, "completion_tokens", 0) or 0
        return (input_tokens, output_tokens)
    
    # Anthropic Message response
    if hasattr(response, "usage"):
        usage = response.usage
        if hasattr(usage, "input_tokens"):
            input_tokens = getattr(usage, "input_tokens", 0) or 0
            output_tokens = getattr(usage, "output_tokens", 0) or 0
            return (input_tokens, output_tokens)
    
    # Dict response (some libraries return this)
    if isinstance(response, dict):
        usage = response.get("usage", {})
        if usage:
            # OpenAI style
            if "prompt_tokens" in usage:
                input_tokens = usage.get("prompt_tokens", 0) or 0
                output_tokens = usage.get("completion_tokens", 0) or 0
            # Anthropic style
            elif "input_tokens" in usage:
                input_tokens = usage.get("input_tokens", 0) or 0
                output_tokens = usage.get("output_tokens", 0) or 0
            return (input_tokens, output_tokens)
    
    return (input_tokens, output_tokens)


def _extract_content_from_response(response: Any, model_provider: str = "openai") -> str:
    """
    Extract text content from various LLM response formats.
    
    Args:
        response: The LLM response object
        model_provider: The provider name (openai, anthropic, etc.)
    
    Returns:
        str: The extracted text content
    """
    # Already a string
    if isinstance(response, str):
        return response
    
    # OpenAI ChatCompletion
    if hasattr(response, "choices") and response.choices:
        choice = response.choices[0]
        if hasattr(choice, "message") and hasattr(choice.message, "content"):
            return choice.message.content or ""
        # Legacy completion format
        if hasattr(choice, "text"):
            return choice.text or ""
    
    # Anthropic Message
    if hasattr(response, "content") and isinstance(response.content, list):
        texts = []
        for block in response.content:
            if hasattr(block, "text"):
                texts.append(block.text)
        return "".join(texts)
    
    # Dict response
    if isinstance(response, dict):
        # OpenAI style
        if "choices" in response and response["choices"]:
            choice = response["choices"][0]
            if "message" in choice:
                return choice["message"].get("content", "")
            if "text" in choice:
                return choice.get("text", "")
        # Anthropic style
        if "content" in response and isinstance(response["content"], list):
            texts = []
            for block in response["content"]:
                if isinstance(block, dict) and "text" in block:
                    texts.append(block["text"])
            return "".join(texts)
    
    return str(response)


# =============================================================================
# BASE EXPORTER INTERFACE
# =============================================================================

class BaseExporter(ABC):
    """Abstract base class for all exporters."""
    
    @abstractmethod
    def export(self, span_data: Dict[str, Any]) -> bool:
        """Export a single span."""
        pass
    
    def export_batch(self, spans: List[Dict[str, Any]]) -> bool:
        """Export multiple spans. Override for batch optimization."""
        return all(self.export(span) for span in spans)
    
    def start(self) -> None:
        """Start the exporter."""
        pass
    
    def stop(self) -> None:
        """Stop the exporter and flush pending data."""
        pass
    
    def flush(self) -> None:
        """Flush any buffered data."""
        pass
    
    def health_check(self) -> bool:
        """Check if the exporter is healthy."""
        return True


# =============================================================================
# SPLUNK EXPORTER
# =============================================================================

class SplunkHECExporter(BaseExporter):
    """Sends spans to Splunk via HTTP Event Collector (HEC)."""
    
    def __init__(
        self,
        hec_url: str,
        hec_token: str,
        index: str = "genai_traces",
        sourcetype: str = "genai:trace",
        verify_ssl: bool = False,
        batch_size: int = 1,
        flush_interval: float = 5.0
    ):
        self.hec_url = hec_url.rstrip("/")
        if not self.hec_url.endswith("/services/collector/event"):
            self.hec_url += "/services/collector/event"
        
        self.hec_token = hec_token
        self.index = index
        self.sourcetype = sourcetype
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        
        self.ssl_context = ssl.create_default_context()
        if not verify_ssl:
            self.ssl_context.check_hostname = False
            self.ssl_context.verify_mode = ssl.CERT_NONE
        
        self._batch: List[dict] = []
        self._lock = threading.Lock()
        self._flush_thread: Optional[threading.Thread] = None
        self._running = False
        
        atexit.register(self.stop)
    
    def start(self):
        if self._running:
            return
        self._running = True
        if self.batch_size > 1:
            self._flush_thread = threading.Thread(target=self._flush_loop, daemon=True)
            self._flush_thread.start()
    
    def stop(self):
        self._running = False
        self.flush()
    
    def _flush_loop(self):
        while self._running:
            time.sleep(self.flush_interval)
            self.flush()
    
    def flush(self):
        with self._lock:
            if not self._batch:
                return
            batch = self._batch.copy()
            self._batch = []
        self._send_batch(batch)
    
    def _send_batch(self, batch: List[dict]) -> bool:
        if not batch:
            return True
        
        lines = []
        for span in batch:
            event = {
                "index": self.index,
                "sourcetype": self.sourcetype,
                "source": "genai-telemetry",
                "event": span
            }
            lines.append(json.dumps(event))
        
        payload = "\n".join(lines)
        return self._send(payload)
    
    def _send(self, payload: str) -> bool:
        data = payload.encode("utf-8")
        req = urllib.request.Request(
            self.hec_url,
            data=data,
            headers={
                "Authorization": f"Splunk {self.hec_token}",
                "Content-Type": "application/json"
            },
            method="POST"
        )
        
        try:
            with urllib.request.urlopen(req, context=self.ssl_context, timeout=10) as resp:
                return resp.status == 200
        except Exception as e:
            logger.error(f"Splunk HEC Error: {e}")
            return False
    
    def export(self, span_data: dict) -> bool:
        if self.batch_size <= 1:
            return self._send_batch([span_data])
        
        with self._lock:
            self._batch.append(span_data)
            should_flush = len(self._batch) >= self.batch_size
        
        if should_flush:
            self.flush()
        return True
    
    def health_check(self) -> bool:
        try:
            test_event = {"event": "health_check", "sourcetype": "genai:health"}
            return self._send_batch([test_event])
        except:
            return False


# =============================================================================
# ELASTICSEARCH EXPORTER
# =============================================================================

class ElasticsearchExporter(BaseExporter):
    """Sends spans to Elasticsearch."""
    
    def __init__(
        self,
        hosts: List[str] = None,
        index: str = "genai-traces",
        api_key: str = None,
        username: str = None,
        password: str = None,
        verify_ssl: bool = True,
        batch_size: int = 1,
        flush_interval: float = 5.0
    ):
        self.hosts = hosts or ["http://localhost:9200"]
        self.index = index
        self.api_key = api_key
        self.username = username
        self.password = password
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        
        self.ssl_context = ssl.create_default_context()
        if not verify_ssl:
            self.ssl_context.check_hostname = False
            self.ssl_context.verify_mode = ssl.CERT_NONE
        
        self._batch: List[dict] = []
        self._lock = threading.Lock()
        self._flush_thread: Optional[threading.Thread] = None
        self._running = False
        self._host_index = 0
        
        atexit.register(self.stop)
    
    def _get_host(self) -> str:
        """Round-robin host selection."""
        host = self.hosts[self._host_index % len(self.hosts)]
        self._host_index += 1
        return host.rstrip("/")
    
    def _get_headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"ApiKey {self.api_key}"
        elif self.username and self.password:
            import base64
            credentials = base64.b64encode(f"{self.username}:{self.password}".encode()).decode()
            headers["Authorization"] = f"Basic {credentials}"
        return headers
    
    def start(self):
        if self._running:
            return
        self._running = True
        if self.batch_size > 1:
            self._flush_thread = threading.Thread(target=self._flush_loop, daemon=True)
            self._flush_thread.start()
    
    def stop(self):
        self._running = False
        self.flush()
    
    def _flush_loop(self):
        while self._running:
            time.sleep(self.flush_interval)
            self.flush()
    
    def flush(self):
        with self._lock:
            if not self._batch:
                return
            batch = self._batch.copy()
            self._batch = []
        self._send_batch(batch)
    
    def _send_batch(self, batch: List[dict]) -> bool:
        if not batch:
            return True
        
        # Build bulk request
        lines = []
        for span in batch:
            # Index action
            index_date = datetime.now().strftime("%Y.%m.%d")
            index_name = f"{self.index}-{index_date}"
            action = {"index": {"_index": index_name}}
            lines.append(json.dumps(action))
            lines.append(json.dumps(span))
        
        payload = "\n".join(lines) + "\n"
        return self._send(payload, "/_bulk")
    
    def _send(self, payload: str, endpoint: str = "") -> bool:
        host = self._get_host()
        url = f"{host}{endpoint}"
        data = payload.encode("utf-8")
        
        req = urllib.request.Request(
            url,
            data=data,
            headers=self._get_headers(),
            method="POST"
        )
        
        try:
            ctx = self.ssl_context if url.startswith("https") else None
            with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
                return resp.status in (200, 201)
        except Exception as e:
            logger.error(f"Elasticsearch Error: {e}")
            return False
    
    def export(self, span_data: dict) -> bool:
        # Add @timestamp for Elasticsearch
        if "@timestamp" not in span_data:
            span_data["@timestamp"] = span_data.get("timestamp", datetime.now(timezone.utc).isoformat())
        
        if self.batch_size <= 1:
            return self._send_batch([span_data])
        
        with self._lock:
            self._batch.append(span_data)
            should_flush = len(self._batch) >= self.batch_size
        
        if should_flush:
            self.flush()
        return True
    
    def health_check(self) -> bool:
        try:
            host = self._get_host()
            req = urllib.request.Request(f"{host}/_cluster/health", headers=self._get_headers())
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status == 200
        except:
            return False


# =============================================================================
# OPENTELEMETRY EXPORTER (OTLP)
# =============================================================================

class OTLPExporter(BaseExporter):
    """
    Sends spans to OpenTelemetry Collector via OTLP HTTP.
    Compatible with: Datadog, Jaeger, Zipkin, Tempo, etc.
    """
    
    def __init__(
        self,
        endpoint: str = "http://localhost:4318",
        headers: Dict[str, str] = None,
        service_name: str = "genai-app",
        verify_ssl: bool = True,
        batch_size: int = 10,
        flush_interval: float = 5.0
    ):
        self.endpoint = endpoint.rstrip("/")
        if not self.endpoint.endswith("/v1/traces"):
            self.endpoint += "/v1/traces"
        
        self.headers = headers or {}
        self.service_name = service_name
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        
        self.ssl_context = ssl.create_default_context()
        if not verify_ssl:
            self.ssl_context.check_hostname = False
            self.ssl_context.verify_mode = ssl.CERT_NONE
        
        self._batch: List[dict] = []
        self._lock = threading.Lock()
        self._flush_thread: Optional[threading.Thread] = None
        self._running = False
        
        atexit.register(self.stop)
    
    def start(self):
        if self._running:
            return
        self._running = True
        if self.batch_size > 1:
            self._flush_thread = threading.Thread(target=self._flush_loop, daemon=True)
            self._flush_thread.start()
    
    def stop(self):
        self._running = False
        self.flush()
    
    def _flush_loop(self):
        while self._running:
            time.sleep(self.flush_interval)
            self.flush()
    
    def flush(self):
        with self._lock:
            if not self._batch:
                return
            batch = self._batch.copy()
            self._batch = []
        self._send_batch(batch)
    
    def _convert_to_otlp(self, spans: List[dict]) -> dict:
        """Convert internal span format to OTLP format."""
        otlp_spans = []
        
        for span in spans:
            # Convert timestamp to nanoseconds
            ts = span.get("timestamp", datetime.now(timezone.utc).isoformat())
            if isinstance(ts, str):
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                start_time_ns = int(dt.timestamp() * 1e9)
            else:
                start_time_ns = int(time.time() * 1e9)
            
            duration_ms = span.get("duration_ms", 0)
            end_time_ns = start_time_ns + int(duration_ms * 1e6)
            
            # Build attributes
            attributes = []
            for key, value in span.items():
                if key in ("trace_id", "span_id", "parent_span_id", "timestamp", "duration_ms", "name", "status"):
                    continue
                
                attr = {"key": key}
                if isinstance(value, bool):
                    attr["value"] = {"boolValue": value}
                elif isinstance(value, int):
                    attr["value"] = {"intValue": str(value)}
                elif isinstance(value, float):
                    attr["value"] = {"doubleValue": value}
                else:
                    attr["value"] = {"stringValue": str(value)}
                attributes.append(attr)
            
            otlp_span = {
                "traceId": span.get("trace_id", uuid.uuid4().hex),
                "spanId": span.get("span_id", uuid.uuid4().hex[:16]),
                "name": span.get("name", "unknown"),
                "kind": 1,  # INTERNAL
                "startTimeUnixNano": str(start_time_ns),
                "endTimeUnixNano": str(end_time_ns),
                "attributes": attributes,
                "status": {
                    "code": 2 if span.get("is_error") else 1  # ERROR or OK
                }
            }
            
            if span.get("parent_span_id"):
                otlp_span["parentSpanId"] = span["parent_span_id"]
            
            otlp_spans.append(otlp_span)
        
        return {
            "resourceSpans": [{
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": self.service_name}}
                    ]
                },
                "scopeSpans": [{
                    "scope": {"name": "genai-telemetry", "version": __version__},
                    "spans": otlp_spans
                }]
            }]
        }
    
    def _send_batch(self, batch: List[dict]) -> bool:
        if not batch:
            return True
        
        otlp_payload = self._convert_to_otlp(batch)
        payload = json.dumps(otlp_payload)
        data = payload.encode("utf-8")
        
        headers = {
            "Content-Type": "application/json",
            **self.headers
        }
        
        req = urllib.request.Request(
            self.endpoint,
            data=data,
            headers=headers,
            method="POST"
        )
        
        try:
            ctx = self.ssl_context if self.endpoint.startswith("https") else None
            with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
                return resp.status == 200
        except Exception as e:
            logger.error(f"OTLP Error: {e}")
            return False
    
    def export(self, span_data: dict) -> bool:
        if self.batch_size <= 1:
            return self._send_batch([span_data])
        
        with self._lock:
            self._batch.append(span_data)
            should_flush = len(self._batch) >= self.batch_size
        
        if should_flush:
            self.flush()
        return True


# =============================================================================
# DATADOG EXPORTER
# =============================================================================

class DatadogExporter(BaseExporter):
    """Sends spans directly to Datadog API."""
    
    def __init__(
        self,
        api_key: str,
        site: str = "datadoghq.com",
        service_name: str = "genai-app",
        env: str = "production",
        batch_size: int = 10,
        flush_interval: float = 5.0
    ):
        self.api_key = api_key
        self.site = site
        self.service_name = service_name
        self.env = env
        self.endpoint = f"https://trace.agent.{site}/api/v0.2/traces"
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        
        self._batch: List[dict] = []
        self._lock = threading.Lock()
        self._flush_thread: Optional[threading.Thread] = None
        self._running = False
        
        atexit.register(self.stop)
    
    def start(self):
        if self._running:
            return
        self._running = True
        if self.batch_size > 1:
            self._flush_thread = threading.Thread(target=self._flush_loop, daemon=True)
            self._flush_thread.start()
    
    def stop(self):
        self._running = False
        self.flush()
    
    def _flush_loop(self):
        while self._running:
            time.sleep(self.flush_interval)
            self.flush()
    
    def flush(self):
        with self._lock:
            if not self._batch:
                return
            batch = self._batch.copy()
            self._batch = []
        self._send_batch(batch)
    
    def _convert_to_datadog(self, spans: List[dict]) -> List[List[dict]]:
        """Convert to Datadog trace format."""
        dd_traces = []
        
        for span in spans:
            start_ns = int(time.time() * 1e9)
            duration_ns = int(span.get("duration_ms", 0) * 1e6)
            
            dd_span = {
                "trace_id": int(span.get("trace_id", uuid.uuid4().hex)[:16], 16),
                "span_id": int(span.get("span_id", uuid.uuid4().hex[:16])[:16], 16),
                "name": span.get("name", "unknown"),
                "resource": span.get("name", "unknown"),
                "service": self.service_name,
                "type": "custom",
                "start": start_ns,
                "duration": duration_ns,
                "meta": {
                    "env": self.env,
                    "span_type": span.get("span_type", "UNKNOWN"),
                    "model_name": span.get("model_name", ""),
                    "model_provider": span.get("model_provider", ""),
                    "workflow_name": span.get("workflow_name", ""),
                },
                "metrics": {
                    "input_tokens": span.get("input_tokens", 0),
                    "output_tokens": span.get("output_tokens", 0),
                    "duration_ms": span.get("duration_ms", 0),
                }
            }
            
            if span.get("is_error"):
                dd_span["error"] = 1
                dd_span["meta"]["error.message"] = span.get("error_message", "")
                dd_span["meta"]["error.type"] = span.get("error_type", "")
            
            if span.get("parent_span_id"):
                dd_span["parent_id"] = int(span["parent_span_id"][:16], 16)
            
            dd_traces.append([dd_span])
        
        return dd_traces
    
    def _send_batch(self, batch: List[dict]) -> bool:
        if not batch:
            return True
        
        dd_payload = self._convert_to_datadog(batch)
        payload = json.dumps(dd_payload)
        data = payload.encode("utf-8")
        
        req = urllib.request.Request(
            self.endpoint,
            data=data,
            headers={
                "Content-Type": "application/json",
                "DD-API-KEY": self.api_key,
            },
            method="PUT"
        )
        
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status == 200
        except Exception as e:
            logger.error(f"Datadog Error: {e}")
            return False
    
    def export(self, span_data: dict) -> bool:
        if self.batch_size <= 1:
            return self._send_batch([span_data])
        
        with self._lock:
            self._batch.append(span_data)
            should_flush = len(self._batch) >= self.batch_size
        
        if should_flush:
            self.flush()
        return True


# =============================================================================
# PROMETHEUS EXPORTER (Push Gateway)
# =============================================================================

class PrometheusExporter(BaseExporter):
    """Sends metrics to Prometheus Push Gateway."""
    
    def __init__(
        self,
        pushgateway_url: str = "http://localhost:9091",
        job_name: str = "genai_telemetry",
        username: str = None,
        password: str = None
    ):
        self.pushgateway_url = pushgateway_url.rstrip("/")
        self.job_name = job_name
        self.username = username
        self.password = password
        
        # Metrics storage
        self._metrics: Dict[str, Dict] = {
            "llm_requests_total": {"type": "counter", "value": 0},
            "llm_duration_seconds": {"type": "histogram", "values": []},
            "llm_tokens_total": {"type": "counter", "input": 0, "output": 0},
            "llm_errors_total": {"type": "counter", "value": 0},
        }
        self._lock = threading.Lock()
    
    def _get_headers(self) -> dict:
        headers = {"Content-Type": "text/plain"}
        if self.username and self.password:
            import base64
            credentials = base64.b64encode(f"{self.username}:{self.password}".encode()).decode()
            headers["Authorization"] = f"Basic {credentials}"
        return headers
    
    def export(self, span_data: dict) -> bool:
        """Update metrics and push to gateway."""
        with self._lock:
            # Update counters
            self._metrics["llm_requests_total"]["value"] += 1
            
            if span_data.get("is_error"):
                self._metrics["llm_errors_total"]["value"] += 1
            
            # Update tokens
            self._metrics["llm_tokens_total"]["input"] += span_data.get("input_tokens", 0)
            self._metrics["llm_tokens_total"]["output"] += span_data.get("output_tokens", 0)
            
            # Update duration histogram
            duration_sec = span_data.get("duration_ms", 0) / 1000
            self._metrics["llm_duration_seconds"]["values"].append(duration_sec)
        
        return self._push_metrics(span_data)
    
    def _push_metrics(self, span_data: dict) -> bool:
        """Push metrics to Prometheus Push Gateway."""
        model = span_data.get("model_name", "unknown")
        provider = span_data.get("model_provider", "unknown")
        workflow = span_data.get("workflow_name", "unknown")
        
        # Build Prometheus text format
        lines = []
        
        with self._lock:
            # Counter: requests
            lines.append(f'# TYPE llm_requests_total counter')
            lines.append(f'llm_requests_total{{model="{model}",provider="{provider}",workflow="{workflow}"}} {self._metrics["llm_requests_total"]["value"]}')
            
            # Counter: errors
            lines.append(f'# TYPE llm_errors_total counter')
            lines.append(f'llm_errors_total{{model="{model}",provider="{provider}",workflow="{workflow}"}} {self._metrics["llm_errors_total"]["value"]}')
            
            # Counter: tokens
            lines.append(f'# TYPE llm_input_tokens_total counter')
            lines.append(f'llm_input_tokens_total{{model="{model}",provider="{provider}"}} {self._metrics["llm_tokens_total"]["input"]}')
            lines.append(f'# TYPE llm_output_tokens_total counter')
            lines.append(f'llm_output_tokens_total{{model="{model}",provider="{provider}"}} {self._metrics["llm_tokens_total"]["output"]}')
            
            # Gauge: last duration
            duration_sec = span_data.get("duration_ms", 0) / 1000
            lines.append(f'# TYPE llm_duration_seconds gauge')
            lines.append(f'llm_duration_seconds{{model="{model}",provider="{provider}"}} {duration_sec}')
        
        payload = "\n".join(lines) + "\n"
        
        url = f"{self.pushgateway_url}/metrics/job/{self.job_name}"
        data = payload.encode("utf-8")
        
        req = urllib.request.Request(
            url,
            data=data,
            headers=self._get_headers(),
            method="POST"
        )
        
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status in (200, 202)
        except Exception as e:
            logger.error(f"Prometheus Push Error: {e}")
            return False


# =============================================================================
# GRAFANA LOKI EXPORTER
# =============================================================================

class LokiExporter(BaseExporter):
    """Sends logs to Grafana Loki."""
    
    def __init__(
        self,
        url: str = "http://localhost:3100",
        tenant_id: str = None,
        username: str = None,
        password: str = None,
        labels: Dict[str, str] = None,
        batch_size: int = 10,
        flush_interval: float = 5.0
    ):
        self.url = url.rstrip("/") + "/loki/api/v1/push"
        self.tenant_id = tenant_id
        self.username = username
        self.password = password
        self.labels = labels or {"job": "genai-telemetry"}
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        
        self._batch: List[dict] = []
        self._lock = threading.Lock()
        self._flush_thread: Optional[threading.Thread] = None
        self._running = False
        
        atexit.register(self.stop)
    
    def start(self):
        if self._running:
            return
        self._running = True
        if self.batch_size > 1:
            self._flush_thread = threading.Thread(target=self._flush_loop, daemon=True)
            self._flush_thread.start()
    
    def stop(self):
        self._running = False
        self.flush()
    
    def _flush_loop(self):
        while self._running:
            time.sleep(self.flush_interval)
            self.flush()
    
    def flush(self):
        with self._lock:
            if not self._batch:
                return
            batch = self._batch.copy()
            self._batch = []
        self._send_batch(batch)
    
    def _get_headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.tenant_id:
            headers["X-Scope-OrgID"] = self.tenant_id
        if self.username and self.password:
            import base64
            credentials = base64.b64encode(f"{self.username}:{self.password}".encode()).decode()
            headers["Authorization"] = f"Basic {credentials}"
        return headers
    
    def _send_batch(self, batch: List[dict]) -> bool:
        if not batch:
            return True
        
        # Group by labels
        streams = {}
        for span in batch:
            # Build labels for this span
            labels = {
                **self.labels,
                "span_type": span.get("span_type", "UNKNOWN"),
                "model_name": span.get("model_name", "unknown"),
                "workflow_name": span.get("workflow_name", "unknown"),
            }
            label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
            
            if label_str not in streams:
                streams[label_str] = {"stream": labels, "values": []}
            
            # Timestamp in nanoseconds
            ts_ns = str(int(time.time() * 1e9))
            log_line = json.dumps(span)
            streams[label_str]["values"].append([ts_ns, log_line])
        
        payload = {"streams": list(streams.values())}
        data = json.dumps(payload).encode("utf-8")
        
        req = urllib.request.Request(
            self.url,
            data=data,
            headers=self._get_headers(),
            method="POST"
        )
        
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status in (200, 204)
        except Exception as e:
            logger.error(f"Loki Error: {e}")
            return False
    
    def export(self, span_data: dict) -> bool:
        if self.batch_size <= 1:
            return self._send_batch([span_data])
        
        with self._lock:
            self._batch.append(span_data)
            should_flush = len(self._batch) >= self.batch_size
        
        if should_flush:
            self.flush()
        return True


# =============================================================================
# AWS CLOUDWATCH EXPORTER
# =============================================================================

class CloudWatchExporter(BaseExporter):
    """Sends logs to AWS CloudWatch Logs."""
    
    def __init__(
        self,
        log_group: str = "/genai/traces",
        log_stream: str = None,
        region: str = "us-east-1",
        access_key_id: str = None,
        secret_access_key: str = None,
        batch_size: int = 10,
        flush_interval: float = 5.0
    ):
        self.log_group = log_group
        self.log_stream = log_stream or f"genai-{datetime.now().strftime('%Y-%m-%d')}"
        self.region = region
        self.access_key_id = access_key_id or os.environ.get("AWS_ACCESS_KEY_ID")
        self.secret_access_key = secret_access_key or os.environ.get("AWS_SECRET_ACCESS_KEY")
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        
        self._batch: List[dict] = []
        self._lock = threading.Lock()
        self._flush_thread: Optional[threading.Thread] = None
        self._running = False
        self._sequence_token = None
        
        atexit.register(self.stop)
    
    def start(self):
        if self._running:
            return
        self._running = True
        if self.batch_size > 1:
            self._flush_thread = threading.Thread(target=self._flush_loop, daemon=True)
            self._flush_thread.start()
    
    def stop(self):
        self._running = False
        self.flush()
    
    def _flush_loop(self):
        while self._running:
            time.sleep(self.flush_interval)
            self.flush()
    
    def flush(self):
        with self._lock:
            if not self._batch:
                return
            batch = self._batch.copy()
            self._batch = []
        self._send_batch(batch)
    
    def _send_batch(self, batch: List[dict]) -> bool:
        """Send batch to CloudWatch (requires boto3 or manual signing)."""
        if not batch:
            return True
        
        # Try using boto3 if available
        try:
            import boto3
            client = boto3.client(
                "logs",
                region_name=self.region,
                aws_access_key_id=self.access_key_id,
                aws_secret_access_key=self.secret_access_key
            )
            
            log_events = []
            for span in batch:
                log_events.append({
                    "timestamp": int(time.time() * 1000),
                    "message": json.dumps(span)
                })
            
            kwargs = {
                "logGroupName": self.log_group,
                "logStreamName": self.log_stream,
                "logEvents": log_events
            }
            
            if self._sequence_token:
                kwargs["sequenceToken"] = self._sequence_token
            
            try:
                response = client.put_log_events(**kwargs)
                self._sequence_token = response.get("nextSequenceToken")
                return True
            except client.exceptions.ResourceNotFoundException:
                # Create log group and stream
                try:
                    client.create_log_group(logGroupName=self.log_group)
                except:
                    pass
                try:
                    client.create_log_stream(logGroupName=self.log_group, logStreamName=self.log_stream)
                except:
                    pass
                response = client.put_log_events(**kwargs)
                self._sequence_token = response.get("nextSequenceToken")
                return True
                
        except ImportError:
            logger.warning("boto3 not installed. Install with: pip install boto3")
            return False
        except Exception as e:
            logger.error(f"CloudWatch Error: {e}")
            return False
    
    def export(self, span_data: dict) -> bool:
        if self.batch_size <= 1:
            return self._send_batch([span_data])
        
        with self._lock:
            self._batch.append(span_data)
            should_flush = len(self._batch) >= self.batch_size
        
        if should_flush:
            self.flush()
        return True


# =============================================================================
# CONSOLE EXPORTER (for debugging)
# =============================================================================

class ConsoleExporter(BaseExporter):
    """Prints spans to console."""
    
    def __init__(self, colored: bool = True, verbose: bool = False):
        self.colored = colored
        self.verbose = verbose
    
    def export(self, span_data: dict) -> bool:
        span_type = span_data.get('span_type', 'UNKNOWN')
        name = span_data.get('name', 'unknown')
        duration = span_data.get('duration_ms', 0)
        status = span_data.get('status', 'OK')
        model = span_data.get('model_name', '')
        input_tokens = span_data.get('input_tokens', 0)
        output_tokens = span_data.get('output_tokens', 0)
        total_tokens = input_tokens + output_tokens
        
        if self.colored:
            # ANSI colors
            colors = {
                "LLM": "\033[94m",      # Blue
                "EMBEDDING": "\033[95m", # Magenta
                "RETRIEVER": "\033[96m", # Cyan
                "TOOL": "\033[93m",      # Yellow
                "CHAIN": "\033[92m",     # Green
                "AGENT": "\033[91m",     # Red
                "ERROR": "\033[91m",     # Red
            }
            reset = "\033[0m"
            color = colors.get(span_type, "\033[0m")
            status_color = "\033[91m" if status == "ERROR" else "\033[92m"
            
            print(f"{color}[{span_type:12}]{reset} {name:30} | {duration:>8.1f}ms | {status_color}{status:5}{reset} | {model} | in:{input_tokens} out:{output_tokens} total:{total_tokens}")
        else:
            print(f"[{span_type:12}] {name:30} | {duration:>8.1f}ms | {status:5} | {model} | in:{input_tokens} out:{output_tokens} total:{total_tokens}")
        
        if self.verbose:
            print(f"    {json.dumps(span_data, indent=2)}")
        
        return True


# =============================================================================
# FILE EXPORTER
# =============================================================================

class FileExporter(BaseExporter):
    """Writes spans to a JSONL file."""
    
    def __init__(self, file_path: str, rotate_size_mb: int = 100):
        self.file_path = file_path
        self.rotate_size_mb = rotate_size_mb
        self._lock = threading.Lock()
    
    def export(self, span_data: dict) -> bool:
        try:
            with self._lock:
                # Check for rotation
                if os.path.exists(self.file_path):
                    size_mb = os.path.getsize(self.file_path) / (1024 * 1024)
                    if size_mb >= self.rotate_size_mb:
                        rotated = f"{self.file_path}.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                        os.rename(self.file_path, rotated)
                
                with open(self.file_path, "a") as f:
                    f.write(json.dumps(span_data) + "\n")
            return True
        except Exception as e:
            logger.error(f"File write error: {e}")
            return False


# =============================================================================
# MULTI-EXPORTER
# =============================================================================

class MultiExporter(BaseExporter):
    """Sends spans to multiple exporters simultaneously."""
    
    def __init__(self, exporters: List[BaseExporter]):
        self.exporters = exporters
    
    def export(self, span_data: dict) -> bool:
        results = []
        for exp in self.exporters:
            try:
                results.append(exp.export(span_data))
            except Exception as e:
                logger.error(f"Exporter error: {e}")
                results.append(False)
        return any(results)
    
    def start(self):
        for exp in self.exporters:
            exp.start()
    
    def stop(self):
        for exp in self.exporters:
            exp.stop()
    
    def flush(self):
        for exp in self.exporters:
            exp.flush()


# =============================================================================
# SPAN CLASS
# =============================================================================

class Span:
    """Represents a single span in a trace."""
    
    def __init__(
        self,
        trace_id: str,
        span_id: str,
        name: str,
        span_type: str,
        workflow_name: str = None,
        parent_span_id: str = None,
        **kwargs
    ):
        self.trace_id = trace_id
        self.span_id = span_id
        self.name = name
        self.span_type = span_type
        self.workflow_name = workflow_name
        self.parent_span_id = parent_span_id
        self.start_time = time.time()
        self.end_time = None
        self.duration_ms = None
        self.status = "OK"
        self.is_error = 0
        self.error_message = None
        self.error_type = None
        
        # LLM fields
        self.model_name = kwargs.get("model_name")
        self.model_provider = kwargs.get("model_provider")
        self.input_tokens = kwargs.get("input_tokens", 0)
        self.output_tokens = kwargs.get("output_tokens", 0)
        self.temperature = kwargs.get("temperature")
        self.max_tokens = kwargs.get("max_tokens")
        
        # Embedding fields
        self.embedding_model = kwargs.get("embedding_model")
        self.embedding_dimensions = kwargs.get("embedding_dimensions")
        
        # Retrieval fields
        self.vector_store = kwargs.get("vector_store")
        self.documents_retrieved = kwargs.get("documents_retrieved", 0)
        self.relevance_score = kwargs.get("relevance_score")
        
        # Tool fields
        self.tool_name = kwargs.get("tool_name")
        
        # Agent fields
        self.agent_name = kwargs.get("agent_name")
        self.agent_type = kwargs.get("agent_type")
        
        # Custom attributes
        self.attributes = {}
    
    def set_attribute(self, key: str, value: Any):
        """Set a custom attribute."""
        self.attributes[key] = value
    
    def set_error(self, error: Exception):
        """Set error information."""
        self.status = "ERROR"
        self.is_error = 1
        self.error_message = str(error)
        self.error_type = type(error).__name__
    
    def finish(self, error: Exception = None):
        """Complete the span."""
        self.end_time = time.time()
        self.duration_ms = round((self.end_time - self.start_time) * 1000, 2)
        if error:
            self.set_error(error)
    
    def to_dict(self) -> dict:
        """Convert span to dictionary."""
        data = {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "name": self.name,
            "span_type": self.span_type,
            "timestamp": datetime.fromtimestamp(self.start_time, tz=timezone.utc).isoformat(),
            "duration_ms": self.duration_ms or 0,
            "status": self.status,
            "is_error": self.is_error,
        }
        
        optional_fields = [
            "workflow_name", "parent_span_id", "error_message", "error_type",
            "model_name", "model_provider", "input_tokens", "output_tokens",
            "temperature", "max_tokens", "embedding_model", "embedding_dimensions",
            "vector_store", "documents_retrieved", "relevance_score",
            "tool_name", "agent_name", "agent_type"
        ]
        
        for field in optional_fields:
            value = getattr(self, field, None)
            if value is not None and value != "" and value != 0:
                data[field] = value
        
        if self.span_type == "LLM":
            data["input_tokens"] = self.input_tokens or 0
            data["output_tokens"] = self.output_tokens or 0
        
        if self.attributes:
            data.update(self.attributes)
        
        return data


# =============================================================================
# TELEMETRY MANAGER
# =============================================================================

class GenAITelemetry:
    """Main telemetry manager."""
    
    def __init__(
        self,
        workflow_name: str,
        exporter: BaseExporter,
        service_name: str = None
    ):
        self.workflow_name = workflow_name
        self.service_name = service_name or workflow_name
        self.exporter = exporter
        self._trace_id = threading.local()
        self._span_stack = threading.local()
    
    @property
    def trace_id(self) -> str:
        if not hasattr(self._trace_id, "value") or self._trace_id.value is None:
            self._trace_id.value = uuid.uuid4().hex
        return self._trace_id.value
    
    @trace_id.setter
    def trace_id(self, value: str):
        self._trace_id.value = value
    
    @property
    def span_stack(self) -> List[Span]:
        if not hasattr(self._span_stack, "stack"):
            self._span_stack.stack = []
        return self._span_stack.stack
    
    def new_trace(self) -> str:
        """Start a new trace."""
        self._trace_id.value = uuid.uuid4().hex
        return self._trace_id.value
    
    def current_span(self) -> Optional[Span]:
        """Get the current span."""
        return self.span_stack[-1] if self.span_stack else None
    
    @contextmanager
    def start_span(self, name: str, span_type: str, **kwargs):
        """Context manager for creating spans."""
        parent_id = self.span_stack[-1].span_id if self.span_stack else None
        
        span = Span(
            trace_id=self.trace_id,
            span_id=uuid.uuid4().hex[:16],
            name=name,
            span_type=span_type,
            workflow_name=self.workflow_name,
            parent_span_id=parent_id,
            **kwargs
        )
        
        self.span_stack.append(span)
        
        try:
            yield span
            span.finish()
        except Exception as e:
            span.finish(error=e)
            raise
        finally:
            self.span_stack.pop()
            self.exporter.export(span.to_dict())
    
    def send_span(self, span_type: str, name: str, duration_ms: float = None, **kwargs) -> bool:
        """Send a span directly."""
        parent_id = self.span_stack[-1].span_id if self.span_stack else None
        
        span_data = {
            "trace_id": self.trace_id,
            "span_id": uuid.uuid4().hex[:16],
            "parent_span_id": parent_id,
            "span_type": span_type,
            "name": name,
            "workflow_name": self.workflow_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "duration_ms": duration_ms or 0,
            "status": kwargs.pop("status", "OK"),
            "is_error": kwargs.pop("is_error", 0),
        }
        
        for key, value in kwargs.items():
            if value is not None and value != "":
                span_data[key] = value
        
        return self.exporter.export(span_data)


# =============================================================================
# GLOBAL INSTANCE & SETUP
# =============================================================================

_telemetry: Optional[GenAITelemetry] = None


def setup_telemetry(
    workflow_name: str,
    exporter: Union[str, BaseExporter, List[Dict]] = "console",
    service_name: str = None,
    # Splunk options
    splunk_url: str = None,
    splunk_token: str = None,
    splunk_index: str = "genai_traces",
    # Elasticsearch options
    es_hosts: List[str] = None,
    es_index: str = "genai-traces",
    es_api_key: str = None,
    es_username: str = None,
    es_password: str = None,
    # OpenTelemetry options
    otlp_endpoint: str = None,
    otlp_headers: Dict[str, str] = None,
    # Datadog options
    datadog_api_key: str = None,
    datadog_site: str = "datadoghq.com",
    # Prometheus options
    prometheus_gateway: str = None,
    # Loki options
    loki_url: str = None,
    loki_tenant_id: str = None,
    # CloudWatch options
    cloudwatch_log_group: str = None,
    cloudwatch_region: str = "us-east-1",
    # File options
    file_path: str = None,
    # Common options
    console: bool = False,
    verify_ssl: bool = False,
    batch_size: int = 1,
    flush_interval: float = 5.0
) -> GenAITelemetry:
    """
    Initialize GenAI telemetry with the specified exporter(s).
    
    Args:
        workflow_name: Name of your application/workflow
        exporter: Exporter type or instance. Options:
            - "splunk": Splunk HEC
            - "elasticsearch" / "es": Elasticsearch
            - "otlp" / "opentelemetry": OpenTelemetry Collector
            - "datadog": Datadog
            - "prometheus": Prometheus Push Gateway
            - "loki": Grafana Loki
            - "cloudwatch": AWS CloudWatch
            - "console": Console output
            - "file": File output
            - BaseExporter instance
            - List of exporter configs for multiple exporters
        
    Returns:
        GenAITelemetry instance
    
    Examples:
        # Splunk
        setup_telemetry("my-app", exporter="splunk", 
                       splunk_url="http://splunk:8088", splunk_token="xxx")
        
        # Elasticsearch
        setup_telemetry("my-app", exporter="elasticsearch",
                       es_hosts=["http://localhost:9200"])
        
        # Multiple exporters
        setup_telemetry("my-app", exporter=[
            {"type": "splunk", "url": "...", "token": "..."},
            {"type": "elasticsearch", "hosts": ["..."]},
            {"type": "console"}
        ])
    """
    global _telemetry
    
    exporters = []
    
    # Handle list of exporters
    if isinstance(exporter, list):
        for exp_config in exporter:
            exp_type = exp_config.get("type", "console")
            exp_instance = _create_exporter(exp_type, exp_config)
            if exp_instance:
                exporters.append(exp_instance)
    
    # Handle string exporter type
    elif isinstance(exporter, str):
        config = {
            "splunk_url": splunk_url,
            "splunk_token": splunk_token,
            "splunk_index": splunk_index,
            "es_hosts": es_hosts,
            "es_index": es_index,
            "es_api_key": es_api_key,
            "es_username": es_username,
            "es_password": es_password,
            "otlp_endpoint": otlp_endpoint,
            "otlp_headers": otlp_headers,
            "datadog_api_key": datadog_api_key,
            "datadog_site": datadog_site,
            "prometheus_gateway": prometheus_gateway,
            "loki_url": loki_url,
            "loki_tenant_id": loki_tenant_id,
            "cloudwatch_log_group": cloudwatch_log_group,
            "cloudwatch_region": cloudwatch_region,
            "file_path": file_path,
            "verify_ssl": verify_ssl,
            "batch_size": batch_size,
            "flush_interval": flush_interval,
            "service_name": service_name or workflow_name,
        }
        exp_instance = _create_exporter(exporter, config)
        if exp_instance:
            exporters.append(exp_instance)
    
    # Handle direct exporter instance
    elif isinstance(exporter, BaseExporter):
        exporters.append(exporter)
    
    # Add console if requested
    if console and not any(isinstance(e, ConsoleExporter) for e in exporters):
        exporters.append(ConsoleExporter())
    
    # Add file if requested
    if file_path and not any(isinstance(e, FileExporter) for e in exporters):
        exporters.append(FileExporter(file_path))
    
    if not exporters:
        exporters.append(ConsoleExporter())
    
    # Create final exporter
    final_exporter = MultiExporter(exporters) if len(exporters) > 1 else exporters[0]
    final_exporter.start()
    
    _telemetry = GenAITelemetry(
        workflow_name=workflow_name,
        exporter=final_exporter,
        service_name=service_name
    )
    
    return _telemetry


def _create_exporter(exporter_type: str, config: dict) -> Optional[BaseExporter]:
    """Create an exporter instance from type and config."""
    exporter_type = exporter_type.lower()
    
    if exporter_type == "splunk":
        url = config.get("splunk_url") or config.get("url")
        token = config.get("splunk_token") or config.get("token")
        if not url or not token:
            raise ValueError("Splunk requires splunk_url and splunk_token")
        return SplunkHECExporter(
            hec_url=url,
            hec_token=token,
            index=config.get("splunk_index") or config.get("index", "genai_traces"),
            verify_ssl=config.get("verify_ssl", False),
            batch_size=config.get("batch_size", 1),
            flush_interval=config.get("flush_interval", 5.0)
        )
    
    elif exporter_type in ("elasticsearch", "es", "elastic"):
        hosts = config.get("es_hosts") or config.get("hosts")
        if not hosts:
            hosts = ["http://localhost:9200"]
        return ElasticsearchExporter(
            hosts=hosts,
            index=config.get("es_index") or config.get("index", "genai-traces"),
            api_key=config.get("es_api_key") or config.get("api_key"),
            username=config.get("es_username") or config.get("username"),
            password=config.get("es_password") or config.get("password"),
            verify_ssl=config.get("verify_ssl", True),
            batch_size=config.get("batch_size", 1),
            flush_interval=config.get("flush_interval", 5.0)
        )
    
    elif exporter_type in ("otlp", "opentelemetry", "otel"):
        endpoint = config.get("otlp_endpoint") or config.get("endpoint", "http://localhost:4318")
        return OTLPExporter(
            endpoint=endpoint,
            headers=config.get("otlp_headers") or config.get("headers"),
            service_name=config.get("service_name", "genai-app"),
            verify_ssl=config.get("verify_ssl", True),
            batch_size=config.get("batch_size", 10),
            flush_interval=config.get("flush_interval", 5.0)
        )
    
    elif exporter_type == "datadog":
        api_key = config.get("datadog_api_key") or config.get("api_key")
        if not api_key:
            raise ValueError("Datadog requires datadog_api_key")
        return DatadogExporter(
            api_key=api_key,
            site=config.get("datadog_site") or config.get("site", "datadoghq.com"),
            service_name=config.get("service_name", "genai-app"),
            batch_size=config.get("batch_size", 10),
            flush_interval=config.get("flush_interval", 5.0)
        )
    
    elif exporter_type == "prometheus":
        gateway = config.get("prometheus_gateway") or config.get("gateway", "http://localhost:9091")
        return PrometheusExporter(
            pushgateway_url=gateway,
            job_name=config.get("job_name", "genai_telemetry")
        )
    
    elif exporter_type == "loki":
        url = config.get("loki_url") or config.get("url", "http://localhost:3100")
        return LokiExporter(
            url=url,
            tenant_id=config.get("loki_tenant_id") or config.get("tenant_id"),
            batch_size=config.get("batch_size", 10),
            flush_interval=config.get("flush_interval", 5.0)
        )
    
    elif exporter_type in ("cloudwatch", "aws"):
        log_group = config.get("cloudwatch_log_group") or config.get("log_group", "/genai/traces")
        return CloudWatchExporter(
            log_group=log_group,
            region=config.get("cloudwatch_region") or config.get("region", "us-east-1"),
            batch_size=config.get("batch_size", 10),
            flush_interval=config.get("flush_interval", 5.0)
        )
    
    elif exporter_type == "file":
        path = config.get("file_path") or config.get("path", "genai_traces.jsonl")
        return FileExporter(file_path=path)
    
    elif exporter_type == "console":
        return ConsoleExporter(
            colored=config.get("colored", True),
            verbose=config.get("verbose", False)
        )
    
    else:
        raise ValueError(f"Unknown exporter type: {exporter_type}")


def get_telemetry() -> GenAITelemetry:
    """Get the telemetry instance."""
    if _telemetry is None:
        raise RuntimeError("Call setup_telemetry() first")
    return _telemetry


# =============================================================================
# DECORATORS - UPDATED WITH TOKEN EXTRACTION FIX
# =============================================================================

def trace_llm(
    model_name: str,
    model_provider: str = "openai",
    extract_content: bool = False
) -> Callable:
    """
    Decorator to trace LLM calls.
    
    IMPORTANT: To capture token usage, you must return the FULL response object
    from the LLM client, not just response.choices[0].message.content.
    
    Args:
        model_name: Name of the model (e.g., "gpt-4o", "claude-3-opus")
        model_provider: Provider name (e.g., "openai", "anthropic")
        extract_content: If True, automatically extract and return just the content
                        string while still capturing token metrics. This allows you
                        to return the full response in your function but get just
                        the content string back.
    
    Example (correct - captures tokens):
        @trace_llm(model_name="gpt-4o", model_provider="openai")
        def chat(message):
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": message}]
            )
            return response  # Return FULL response
        
        answer = chat("Hello")
        print(answer.choices[0].message.content)  # Extract content here
    
    Example (with extract_content=True):
        @trace_llm(model_name="gpt-4o", model_provider="openai", extract_content=True)
        def chat(message):
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": message}]
            )
            return response  # Return FULL response
        
        answer = chat("Hello")  # answer is now just the content string
        print(answer)
    
    Example (WRONG - tokens will be 0):
        @trace_llm(model_name="gpt-4o", model_provider="openai")
        def chat(message):
            response = client.chat.completions.create(...)
            return response.choices[0].message.content  # DON'T DO THIS
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            telemetry = get_telemetry()
            start = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration = round((time.time() - start) * 1000, 2)
                
                # Extract tokens using the helper function
                input_tokens, output_tokens = _extract_tokens_from_response(result)
                
                telemetry.send_span(
                    span_type="LLM",
                    name=func.__name__,
                    model_name=model_name,
                    model_provider=model_provider,
                    duration_ms=duration,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=input_tokens + output_tokens
                )
                
                # If extract_content is True, return just the content string
                if extract_content:
                    return _extract_content_from_response(result, model_provider)
                
                return result
                
            except Exception as e:
                duration = round((time.time() - start) * 1000, 2)
                telemetry.send_span(
                    span_type="LLM",
                    name=func.__name__,
                    model_name=model_name,
                    model_provider=model_provider,
                    duration_ms=duration,
                    status="ERROR",
                    is_error=1,
                    error_message=str(e),
                    error_type=type(e).__name__
                )
                raise
        return wrapper
    return decorator


def trace_embedding(model: str) -> Callable:
    """Decorator to trace embedding calls."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            telemetry = get_telemetry()
            start = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration = round((time.time() - start) * 1000, 2)
                
                # Try to extract token usage from embedding response
                input_tokens = 0
                if hasattr(result, "usage") and result.usage:
                    input_tokens = getattr(result.usage, "prompt_tokens", 0) or 0
                    if not input_tokens:
                        input_tokens = getattr(result.usage, "total_tokens", 0) or 0
                
                telemetry.send_span(
                    span_type="EMBEDDING",
                    name=func.__name__,
                    embedding_model=model,
                    duration_ms=duration,
                    input_tokens=input_tokens
                )
                return result
                
            except Exception as e:
                duration = round((time.time() - start) * 1000, 2)
                telemetry.send_span(
                    span_type="EMBEDDING",
                    name=func.__name__,
                    embedding_model=model,
                    duration_ms=duration,
                    status="ERROR",
                    is_error=1,
                    error_message=str(e)
                )
                raise
        return wrapper
    return decorator


def trace_retrieval(vector_store: str, embedding_model: str = None) -> Callable:
    """Decorator to trace retrieval calls."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            telemetry = get_telemetry()
            start = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration = round((time.time() - start) * 1000, 2)
                
                docs_count = len(result) if isinstance(result, (list, tuple)) else 0
                
                telemetry.send_span(
                    span_type="RETRIEVER",
                    name=func.__name__,
                    vector_store=vector_store,
                    embedding_model=embedding_model,
                    documents_retrieved=docs_count,
                    duration_ms=duration
                )
                return result
                
            except Exception as e:
                duration = round((time.time() - start) * 1000, 2)
                telemetry.send_span(
                    span_type="RETRIEVER",
                    name=func.__name__,
                    vector_store=vector_store,
                    duration_ms=duration,
                    status="ERROR",
                    is_error=1,
                    error_message=str(e)
                )
                raise
        return wrapper
    return decorator


def trace_tool(tool_name: str) -> Callable:
    """Decorator to trace tool calls."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            telemetry = get_telemetry()
            start = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration = round((time.time() - start) * 1000, 2)
                
                telemetry.send_span(
                    span_type="TOOL",
                    name=func.__name__,
                    tool_name=tool_name,
                    duration_ms=duration
                )
                return result
                
            except Exception as e:
                duration = round((time.time() - start) * 1000, 2)
                telemetry.send_span(
                    span_type="TOOL",
                    name=func.__name__,
                    tool_name=tool_name,
                    duration_ms=duration,
                    status="ERROR",
                    is_error=1,
                    error_message=str(e)
                )
                raise
        return wrapper
    return decorator


def trace_chain(name: str) -> Callable:
    """Decorator to trace chain/pipeline calls."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            telemetry = get_telemetry()
            telemetry.new_trace()
            start = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration = round((time.time() - start) * 1000, 2)
                
                telemetry.send_span(
                    span_type="CHAIN",
                    name=name,
                    duration_ms=duration
                )
                return result
                
            except Exception as e:
                duration = round((time.time() - start) * 1000, 2)
                telemetry.send_span(
                    span_type="CHAIN",
                    name=name,
                    duration_ms=duration,
                    status="ERROR",
                    is_error=1,
                    error_message=str(e)
                )
                raise
        return wrapper
    return decorator


def trace_agent(agent_name: str, agent_type: str = None) -> Callable:
    """Decorator to trace agent calls."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            telemetry = get_telemetry()
            telemetry.new_trace()
            start = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration = round((time.time() - start) * 1000, 2)
                
                telemetry.send_span(
                    span_type="AGENT",
                    name=func.__name__,
                    agent_name=agent_name,
                    agent_type=agent_type,
                    duration_ms=duration
                )
                return result
                
            except Exception as e:
                duration = round((time.time() - start) * 1000, 2)
                telemetry.send_span(
                    span_type="AGENT",
                    name=func.__name__,
                    agent_name=agent_name,
                    agent_type=agent_type,
                    duration_ms=duration,
                    status="ERROR",
                    is_error=1,
                    error_message=str(e)
                )
                raise
        return wrapper
    return decorator


# =============================================================================
# PUBLIC API
# =============================================================================

__all__ = [
    # Version
    "__version__",
    
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
    "_extract_tokens_from_response",
    "_extract_content_from_response",
]
