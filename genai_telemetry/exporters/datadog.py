"""
Datadog exporter for direct API integration.
"""

import atexit
import json
import logging
import threading
import time
import uuid
import urllib.request
from typing import Any, Dict, List, Optional

from genai_telemetry.exporters.base import BaseExporter

logger = logging.getLogger("genai_telemetry.exporters.datadog")


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
        """
        Initialize Datadog exporter.
        
        Args:
            api_key: Datadog API key
            site: Datadog site (e.g., datadoghq.com, datadoghq.eu)
            service_name: Service name for traces
            env: Environment name
            batch_size: Number of spans to batch before sending
            flush_interval: Seconds between automatic flushes
        """
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
        """Send a batch of spans to Datadog."""
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
