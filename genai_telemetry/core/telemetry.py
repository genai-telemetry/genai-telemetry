"""
Main telemetry manager and setup functions.
"""

import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from genai_telemetry.core.span import Span
from genai_telemetry.exporters.base import BaseExporter


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
    
    # Import exporters here to avoid circular imports
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
    # Import exporters here to avoid circular imports
    from genai_telemetry.exporters.splunk import SplunkHECExporter
    from genai_telemetry.exporters.elasticsearch import ElasticsearchExporter
    from genai_telemetry.exporters.otlp import OTLPExporter
    from genai_telemetry.exporters.datadog import DatadogExporter
    from genai_telemetry.exporters.prometheus import PrometheusExporter
    from genai_telemetry.exporters.loki import LokiExporter
    from genai_telemetry.exporters.cloudwatch import CloudWatchExporter
    from genai_telemetry.exporters.console import ConsoleExporter
    from genai_telemetry.exporters.file import FileExporter
    
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
