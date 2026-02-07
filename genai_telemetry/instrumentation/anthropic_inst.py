"""
Anthropic SDK Auto-Instrumentation.

Automatically traces all Anthropic API calls including:
- Messages (sync and async)
- Streaming messages
"""

import time
import logging
from functools import wraps
from typing import Any, Callable

from genai_telemetry.instrumentation.base import (
    BaseInstrumentor,
    safe_import,
    wrap_method,
    unwrap_method,
)
from genai_telemetry.core.utils import extract_tokens_from_response

logger = logging.getLogger(__name__)


class AnthropicInstrumentor(BaseInstrumentor):
    """Instrumentor for the Anthropic Python SDK."""
    
    _original_methods = {}
    
    @property
    def name(self) -> str:
        return "Anthropic"
    
    def _check_installed(self) -> bool:
        return safe_import("anthropic") is not None
    
    def _get_telemetry(self):
        """Get telemetry instance, handling case where it's not set up."""
        try:
            from genai_telemetry.core.telemetry import get_telemetry
            return get_telemetry()
        except RuntimeError:
            return None
    
    def _create_messages_wrapper(self, original_method: Callable, is_async: bool = False) -> Callable:
        """Create a wrapper for messages.create methods."""
        instrumentor = self
        
        if is_async:
            @wraps(original_method)
            async def async_wrapper(*args, **kwargs):
                telemetry = instrumentor._get_telemetry()
                if telemetry is None:
                    return await original_method(*args, **kwargs)
                
                model = kwargs.get("model", "unknown")
                start_time = time.time()
                error_info = None
                response = None
                
                try:
                    response = await original_method(*args, **kwargs)
                    return response
                except Exception as e:
                    error_info = e
                    raise
                finally:
                    duration_ms = round((time.time() - start_time) * 1000, 2)
                    input_tokens, output_tokens = 0, 0
                    
                    if response is not None:
                        input_tokens, output_tokens = extract_tokens_from_response(response)
                    
                    span_kwargs = {
                        "span_type": "LLM",
                        "name": "anthropic.messages.create",
                        "model_name": model,
                        "model_provider": "anthropic",
                        "duration_ms": duration_ms,
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "total_tokens": input_tokens + output_tokens,
                    }
                    
                    if error_info:
                        span_kwargs["status"] = "ERROR"
                        span_kwargs["is_error"] = 1
                        span_kwargs["error_message"] = str(error_info)
                        span_kwargs["error_type"] = type(error_info).__name__
                    
                    telemetry.send_span(**span_kwargs)
            
            return async_wrapper
        else:
            @wraps(original_method)
            def sync_wrapper(*args, **kwargs):
                telemetry = instrumentor._get_telemetry()
                if telemetry is None:
                    return original_method(*args, **kwargs)
                
                model = kwargs.get("model", "unknown")
                start_time = time.time()
                error_info = None
                response = None
                
                try:
                    response = original_method(*args, **kwargs)
                    return response
                except Exception as e:
                    error_info = e
                    raise
                finally:
                    duration_ms = round((time.time() - start_time) * 1000, 2)
                    input_tokens, output_tokens = 0, 0
                    
                    if response is not None:
                        input_tokens, output_tokens = extract_tokens_from_response(response)
                    
                    span_kwargs = {
                        "span_type": "LLM",
                        "name": "anthropic.messages.create",
                        "model_name": model,
                        "model_provider": "anthropic",
                        "duration_ms": duration_ms,
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "total_tokens": input_tokens + output_tokens,
                    }
                    
                    if error_info:
                        span_kwargs["status"] = "ERROR"
                        span_kwargs["is_error"] = 1
                        span_kwargs["error_message"] = str(error_info)
                        span_kwargs["error_type"] = type(error_info).__name__
                    
                    telemetry.send_span(**span_kwargs)
            
            return sync_wrapper
    
    def _instrument(self) -> None:
        """Apply Anthropic instrumentation."""
        import anthropic
        
        # Instrument sync messages
        if hasattr(anthropic, "resources") and hasattr(anthropic.resources, "messages"):
            from anthropic.resources import messages
            if hasattr(messages, "Messages"):
                wrap_method(
                    messages.Messages,
                    "create",
                    lambda orig: self._create_messages_wrapper(orig, is_async=False),
                    self._original_methods
                )
        
        # Instrument async messages
        if hasattr(anthropic, "resources") and hasattr(anthropic.resources, "messages"):
            from anthropic.resources import messages
            if hasattr(messages, "AsyncMessages"):
                wrap_method(
                    messages.AsyncMessages,
                    "create",
                    lambda orig: self._create_messages_wrapper(orig, is_async=True),
                    self._original_methods
                )
        
        logger.debug(f"Instrumented {len(self._original_methods)} Anthropic methods")
    
    def _uninstrument(self) -> None:
        """Remove Anthropic instrumentation."""
        import anthropic
        
        if hasattr(anthropic, "resources") and hasattr(anthropic.resources, "messages"):
            from anthropic.resources import messages
            if hasattr(messages, "Messages"):
                unwrap_method(messages.Messages, "create", self._original_methods)
            if hasattr(messages, "AsyncMessages"):
                unwrap_method(messages.AsyncMessages, "create", self._original_methods)
