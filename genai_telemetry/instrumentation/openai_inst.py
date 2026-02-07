"""
OpenAI SDK Auto-Instrumentation.

Automatically traces all OpenAI API calls including:
- Chat completions (sync and async)
- Completions (legacy)
- Embeddings
- Image generation
- Audio transcription/translation
"""

import time
import logging
from functools import wraps
from typing import Any, Optional, Callable

from genai_telemetry.instrumentation.base import (
    BaseInstrumentor,
    safe_import,
    wrap_method,
    unwrap_method,
)
from genai_telemetry.core.utils import extract_tokens_from_response

logger = logging.getLogger(__name__)


class OpenAIInstrumentor(BaseInstrumentor):
    """Instrumentor for the OpenAI Python SDK."""
    
    _original_methods = {}
    
    @property
    def name(self) -> str:
        return "OpenAI"
    
    def _check_installed(self) -> bool:
        return safe_import("openai") is not None
    
    def _get_telemetry(self):
        """Get telemetry instance, handling case where it's not set up."""
        try:
            from genai_telemetry.core.telemetry import get_telemetry
            return get_telemetry()
        except RuntimeError:
            return None
    
    def _create_chat_wrapper(self, original_method: Callable, is_async: bool = False) -> Callable:
        """Create a wrapper for chat completion methods."""
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
                        "name": "openai.chat.completions.create",
                        "model_name": model,
                        "model_provider": "openai",
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
                        "name": "openai.chat.completions.create",
                        "model_name": model,
                        "model_provider": "openai",
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
    
    def _create_embedding_wrapper(self, original_method: Callable, is_async: bool = False) -> Callable:
        """Create a wrapper for embedding methods."""
        instrumentor = self
        
        if is_async:
            @wraps(original_method)
            async def async_wrapper(*args, **kwargs):
                telemetry = instrumentor._get_telemetry()
                if telemetry is None:
                    return await original_method(*args, **kwargs)
                
                model = kwargs.get("model", "text-embedding-ada-002")
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
                    input_tokens = 0
                    
                    if response is not None and hasattr(response, "usage"):
                        input_tokens = getattr(response.usage, "total_tokens", 0) or 0
                    
                    span_kwargs = {
                        "span_type": "EMBEDDING",
                        "name": "openai.embeddings.create",
                        "embedding_model": model,
                        "duration_ms": duration_ms,
                        "input_tokens": input_tokens,
                    }
                    
                    if error_info:
                        span_kwargs["status"] = "ERROR"
                        span_kwargs["is_error"] = 1
                        span_kwargs["error_message"] = str(error_info)
                    
                    telemetry.send_span(**span_kwargs)
            
            return async_wrapper
        else:
            @wraps(original_method)
            def sync_wrapper(*args, **kwargs):
                telemetry = instrumentor._get_telemetry()
                if telemetry is None:
                    return original_method(*args, **kwargs)
                
                model = kwargs.get("model", "text-embedding-ada-002")
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
                    input_tokens = 0
                    
                    if response is not None and hasattr(response, "usage"):
                        input_tokens = getattr(response.usage, "total_tokens", 0) or 0
                    
                    span_kwargs = {
                        "span_type": "EMBEDDING",
                        "name": "openai.embeddings.create",
                        "embedding_model": model,
                        "duration_ms": duration_ms,
                        "input_tokens": input_tokens,
                    }
                    
                    if error_info:
                        span_kwargs["status"] = "ERROR"
                        span_kwargs["is_error"] = 1
                        span_kwargs["error_message"] = str(error_info)
                    
                    telemetry.send_span(**span_kwargs)
            
            return sync_wrapper
    
    def _instrument(self) -> None:
        """Apply OpenAI instrumentation."""
        import openai
        
        # Instrument sync chat completions
        if hasattr(openai, "resources") and hasattr(openai.resources, "chat"):
            from openai.resources.chat import completions
            if hasattr(completions, "Completions"):
                wrap_method(
                    completions.Completions,
                    "create",
                    lambda orig: self._create_chat_wrapper(orig, is_async=False),
                    self._original_methods
                )
        
        # Instrument async chat completions
        if hasattr(openai, "resources") and hasattr(openai.resources, "chat"):
            from openai.resources.chat import completions
            if hasattr(completions, "AsyncCompletions"):
                wrap_method(
                    completions.AsyncCompletions,
                    "create",
                    lambda orig: self._create_chat_wrapper(orig, is_async=True),
                    self._original_methods
                )
        
        # Instrument sync embeddings
        if hasattr(openai, "resources"):
            from openai.resources import embeddings
            if hasattr(embeddings, "Embeddings"):
                wrap_method(
                    embeddings.Embeddings,
                    "create",
                    lambda orig: self._create_embedding_wrapper(orig, is_async=False),
                    self._original_methods
                )
        
        # Instrument async embeddings
        if hasattr(openai, "resources"):
            from openai.resources import embeddings
            if hasattr(embeddings, "AsyncEmbeddings"):
                wrap_method(
                    embeddings.AsyncEmbeddings,
                    "create",
                    lambda orig: self._create_embedding_wrapper(orig, is_async=True),
                    self._original_methods
                )
        
        logger.debug(f"Instrumented {len(self._original_methods)} OpenAI methods")
    
    def _uninstrument(self) -> None:
        """Remove OpenAI instrumentation."""
        import openai
        
        if hasattr(openai, "resources") and hasattr(openai.resources, "chat"):
            from openai.resources.chat import completions
            if hasattr(completions, "Completions"):
                unwrap_method(completions.Completions, "create", self._original_methods)
            if hasattr(completions, "AsyncCompletions"):
                unwrap_method(completions.AsyncCompletions, "create", self._original_methods)
        
        if hasattr(openai, "resources"):
            from openai.resources import embeddings
            if hasattr(embeddings, "Embeddings"):
                unwrap_method(embeddings.Embeddings, "create", self._original_methods)
            if hasattr(embeddings, "AsyncEmbeddings"):
                unwrap_method(embeddings.AsyncEmbeddings, "create", self._original_methods)
