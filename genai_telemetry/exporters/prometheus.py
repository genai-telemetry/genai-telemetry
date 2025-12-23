"""
Prometheus Push Gateway exporter.
"""

import base64
import logging
import threading
import urllib.request
from typing import Any, Dict

from genai_telemetry.exporters.base import BaseExporter

logger = logging.getLogger("genai_telemetry.exporters.prometheus")


class PrometheusExporter(BaseExporter):
    """Sends metrics to Prometheus Push Gateway."""
    
    def __init__(
        self,
        pushgateway_url: str = "http://localhost:9091",
        job_name: str = "genai_telemetry",
        username: str = None,
        password: str = None
    ):
        """
        Initialize Prometheus exporter.
        
        Args:
            pushgateway_url: URL of the Prometheus Push Gateway
            job_name: Job name for metrics grouping
            username: Username for basic auth (optional)
            password: Password for basic auth (optional)
        """
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
        """Build authentication headers."""
        headers = {"Content-Type": "text/plain"}
        if self.username and self.password:
            credentials = base64.b64encode(f"{self.username}:{self.password}".encode()).decode()
            headers["Authorization"] = f"Basic {credentials}"
        return headers
    
    def export(self, span_data: Dict[str, Any]) -> bool:
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
    
    def _push_metrics(self, span_data: Dict[str, Any]) -> bool:
        """Push metrics to Prometheus Push Gateway."""
        model = span_data.get("model_name", "unknown")
        provider = span_data.get("model_provider", "unknown")
        workflow = span_data.get("workflow_name", "unknown")
        
        # Build Prometheus text format
        lines = []
        
        with self._lock:
            # Counter: requests
            lines.append('# TYPE llm_requests_total counter')
            lines.append(f'llm_requests_total{{model="{model}",provider="{provider}",workflow="{workflow}"}} {self._metrics["llm_requests_total"]["value"]}')
            
            # Counter: errors
            lines.append('# TYPE llm_errors_total counter')
            lines.append(f'llm_errors_total{{model="{model}",provider="{provider}",workflow="{workflow}"}} {self._metrics["llm_errors_total"]["value"]}')
            
            # Counter: tokens
            lines.append('# TYPE llm_input_tokens_total counter')
            lines.append(f'llm_input_tokens_total{{model="{model}",provider="{provider}"}} {self._metrics["llm_tokens_total"]["input"]}')
            lines.append('# TYPE llm_output_tokens_total counter')
            lines.append(f'llm_output_tokens_total{{model="{model}",provider="{provider}"}} {self._metrics["llm_tokens_total"]["output"]}')
            
            # Gauge: last duration
            duration_sec = span_data.get("duration_ms", 0) / 1000
            lines.append('# TYPE llm_duration_seconds gauge')
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
