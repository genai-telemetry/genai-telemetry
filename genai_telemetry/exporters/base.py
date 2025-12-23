"""
Base exporter interface for all telemetry exporters.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class BaseExporter(ABC):
    """Abstract base class for all exporters."""
    
    @abstractmethod
    def export(self, span_data: Dict[str, Any]) -> bool:
        """
        Export a single span.
        
        Args:
            span_data: Dictionary containing span data
            
        Returns:
            bool: True if export was successful
        """
        pass
    
    def export_batch(self, spans: List[Dict[str, Any]]) -> bool:
        """
        Export multiple spans. Override for batch optimization.
        
        Args:
            spans: List of span data dictionaries
            
        Returns:
            bool: True if all exports were successful
        """
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
        """
        Check if the exporter is healthy.
        
        Returns:
            bool: True if the exporter is healthy
        """
        return True
