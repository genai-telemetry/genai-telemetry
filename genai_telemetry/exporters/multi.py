"""
Multi-exporter for sending spans to multiple backends simultaneously.
"""

import logging
from typing import Any, Dict, List

from genai_telemetry.exporters.base import BaseExporter

logger = logging.getLogger("genai_telemetry.exporters.multi")


class MultiExporter(BaseExporter):
    """Sends spans to multiple exporters simultaneously."""
    
    def __init__(self, exporters: List[BaseExporter]):
        """
        Initialize multi-exporter.
        
        Args:
            exporters: List of exporter instances to send spans to
        """
        self.exporters = exporters
    
    def export(self, span_data: Dict[str, Any]) -> bool:
        """
        Export span to all configured exporters.
        
        Returns True if at least one exporter succeeds.
        """
        results = []
        for exp in self.exporters:
            try:
                results.append(exp.export(span_data))
            except Exception as e:
                logger.error(f"Exporter error: {e}")
                results.append(False)
        return any(results)
    
    def start(self) -> None:
        """Start all exporters."""
        for exp in self.exporters:
            exp.start()
    
    def stop(self) -> None:
        """Stop all exporters."""
        for exp in self.exporters:
            exp.stop()
    
    def flush(self) -> None:
        """Flush all exporters."""
        for exp in self.exporters:
            exp.flush()
    
    def health_check(self) -> bool:
        """Check if any exporter is healthy."""
        return any(exp.health_check() for exp in self.exporters)
