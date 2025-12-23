"""
OpenTelemetry Protocol (OTLP) exporter.
Compatible with: Datadog, Jaeger, Zipkin, Tempo, etc.
"""

import atexit
import json
import logging
import ssl
import threading
import time
import uuid
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import genai_telemetry
from genai_telemetry.exporters.base import BaseExporter

logger = logging.getLogger("genai_telemetry.exporters.otlp")


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
        """
        Initialize OTLP exporter.
        
        Args:
            endpoint: OTLP collector endpoint
            headers: Additional headers for authentication
            service_name: Service name for traces
            verify_ssl: Whether to verify SSL certificates
            batch_size: Number of spans to batch before sending
            flush_interval: Seconds between automatic flushes
        """
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
    
    def start(self) -> None:
        """Start the exporter and background flush thread."""
        if self._running:
            return
        self._running = True
        if self.batch_size > 1:
            self._flush_thread = threading.Thread(target=self._flush_loop, daemon=True)
            self._flush_thread.start()
    
    def stop(self) -> None:
        """Stop the exporter and flush remaining data."""
        self._running = False
        self.flush()
    
    def _flush_loop(self) -> None:
        """Background thread for periodic flushing."""
        while self._running:
            time.sleep(self.flush_interval)
            self.flush()
    
    def flush(self) -> None:
        """Flush any buffered spans."""
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
                    "scope": {"name": "genai-telemetry", "version": genai_telemetry.__version__},
                    "spans": otlp_spans
                }]
            }]
        }
    
    def _send_batch(self, batch: List[dict]) -> bool:
        """Send a batch of spans to OTLP collector."""
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
    
    def export(self, span_data: Dict[str, Any]) -> bool:
        """Export a single span."""
        if self.batch_size <= 1:
            return self._send_batch([span_data])
        
        with self._lock:
            self._batch.append(span_data)
            should_flush = len(self._batch) >= self.batch_size
        
        if should_flush:
            self.flush()
        return True
