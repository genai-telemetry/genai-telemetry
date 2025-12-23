"""
Span class representing a single span in a trace.
"""

import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional


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
        self.end_time: Optional[float] = None
        self.duration_ms: Optional[float] = None
        self.status = "OK"
        self.is_error = 0
        self.error_message: Optional[str] = None
        self.error_type: Optional[str] = None
        
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
        self.attributes: Dict[str, Any] = {}
    
    def set_attribute(self, key: str, value: Any) -> None:
        """Set a custom attribute."""
        self.attributes[key] = value
    
    def set_error(self, error: Exception) -> None:
        """Set error information."""
        self.status = "ERROR"
        self.is_error = 1
        self.error_message = str(error)
        self.error_type = type(error).__name__
    
    def finish(self, error: Exception = None) -> None:
        """Complete the span."""
        self.end_time = time.time()
        self.duration_ms = round((self.end_time - self.start_time) * 1000, 2)
        if error:
            self.set_error(error)
    
    def to_dict(self) -> Dict[str, Any]:
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
