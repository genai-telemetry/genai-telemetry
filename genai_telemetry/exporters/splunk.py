"""
Splunk HTTP Event Collector (HEC) exporter.
"""

import atexit
import json
import logging
import ssl
import threading
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from genai_telemetry.exporters.base import BaseExporter

logger = logging.getLogger("genai_telemetry.exporters.splunk")


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
        """
        Initialize Splunk HEC exporter.
        
        Args:
            hec_url: Splunk HEC URL (e.g., http://splunk:8088)
            hec_token: HEC authentication token
            index: Splunk index to write to
            sourcetype: Splunk sourcetype for events
            verify_ssl: Whether to verify SSL certificates
            batch_size: Number of events to batch before sending
            flush_interval: Seconds between automatic flushes
        """
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
        """Send a batch of spans to Splunk HEC."""
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
        """Send payload to Splunk HEC."""
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
    
    def health_check(self) -> bool:
        """Check if Splunk HEC is reachable."""
        try:
            test_event = {"event": "health_check", "sourcetype": "genai:health"}
            return self._send_batch([test_event])
        except:
            return False
