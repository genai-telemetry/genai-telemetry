"""
Grafana Loki exporter.
"""

import atexit
import base64
import json
import logging
import threading
import time
import urllib.request
from typing import Any, Dict, List, Optional

from genai_telemetry.exporters.base import BaseExporter

logger = logging.getLogger("genai_telemetry.exporters.loki")


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
        """
        Initialize Loki exporter.
        
        Args:
            url: Loki server URL
            tenant_id: Multi-tenant organization ID
            username: Username for basic auth
            password: Password for basic auth
            labels: Default labels for all log streams
            batch_size: Number of logs to batch before sending
            flush_interval: Seconds between automatic flushes
        """
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
        """Flush any buffered logs."""
        with self._lock:
            if not self._batch:
                return
            batch = self._batch.copy()
            self._batch = []
        self._send_batch(batch)
    
    def _get_headers(self) -> dict:
        """Build authentication headers."""
        headers = {"Content-Type": "application/json"}
        if self.tenant_id:
            headers["X-Scope-OrgID"] = self.tenant_id
        if self.username and self.password:
            credentials = base64.b64encode(f"{self.username}:{self.password}".encode()).decode()
            headers["Authorization"] = f"Basic {credentials}"
        return headers
    
    def _send_batch(self, batch: List[dict]) -> bool:
        """Send a batch of logs to Loki."""
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
    
    def export(self, span_data: Dict[str, Any]) -> bool:
        """Export a single span as a log entry."""
        if self.batch_size <= 1:
            return self._send_batch([span_data])
        
        with self._lock:
            self._batch.append(span_data)
            should_flush = len(self._batch) >= self.batch_size
        
        if should_flush:
            self.flush()
        return True
