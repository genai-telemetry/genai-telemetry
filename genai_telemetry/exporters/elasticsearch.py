"""
Elasticsearch exporter.
"""

import atexit
import base64
import json
import logging
import ssl
import threading
import time
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from genai_telemetry.exporters.base import BaseExporter

logger = logging.getLogger("genai_telemetry.exporters.elasticsearch")


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
        """
        Initialize Elasticsearch exporter.
        
        Args:
            hosts: List of Elasticsearch host URLs
            index: Index name prefix (date will be appended)
            api_key: Elasticsearch API key for authentication
            username: Username for basic auth
            password: Password for basic auth
            verify_ssl: Whether to verify SSL certificates
            batch_size: Number of events to batch before sending
            flush_interval: Seconds between automatic flushes
        """
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
        """Build authentication headers."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"ApiKey {self.api_key}"
        elif self.username and self.password:
            credentials = base64.b64encode(f"{self.username}:{self.password}".encode()).decode()
            headers["Authorization"] = f"Basic {credentials}"
        return headers
    
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
    
    def _send_batch(self, batch: List[dict]) -> bool:
        """Send a batch using Elasticsearch bulk API."""
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
        """Send payload to Elasticsearch."""
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
    
    def export(self, span_data: Dict[str, Any]) -> bool:
        """Export a single span."""
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
        """Check if Elasticsearch is reachable."""
        try:
            host = self._get_host()
            req = urllib.request.Request(f"{host}/_cluster/health", headers=self._get_headers())
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status == 200
        except:
            return False
