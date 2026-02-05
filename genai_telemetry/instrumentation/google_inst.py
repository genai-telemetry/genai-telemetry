"""
Google AI / Gemini SDK Auto-Instrumentation.

Automatically traces Google Generative AI API calls including:
- generate_content (sync and async)
- Embeddings
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

logger = logging.getLogger(__name__)


class GoogleAIInstrumentor(BaseInstrumentor):
    """Instrumentor for the Google Generative AI Python SDK."""
    
    _original_methods = {}
    
    @property
    def name(self) -> str:
        return "Google"
    
    def _check_installed(self) -> bool:
        return safe_import("google.generativeai") is not None
    
    def _get_telemetry(self):
        """Get telemetry instance, handling case where it's not set up."""
        try:
            from genai_telemetry.core.telemetry import get_telemetry
            return get_telemetry()
        except RuntimeError:
            return None
    
    def _create_generate_wrapper(self, original_method: Callable, is_async: bool = False) -> Callable:
        """Create a wrapper for generate_content methods."""
        instrumentor = self
        
        if is_async:
            @wraps(original_method)
            async def async_wrapper(self_instance, *args, **kwargs):
                telemetry = instrumentor._get_telemetry()
                if telemetry is None:
                    return await original_method(self_instance, *args, **kwargs)
                
                model_name = getattr(self_instance, "model_name", "gemini")
                start_time = time.time()
                error_info = None
                response = None
                
                try:
                    response = await original_method(self_instance, *args, **kwargs)
                    return response
                except Exception as e:
                    error_info = e
                    raise
                finally:
                    duration_ms = round((time.time() - start_time) * 1000, 2)
                    input_tokens, output_tokens = 0, 0
                    
                    # Extract token usage from Gemini response
                    if response is not None and hasattr(response, "usage_metadata"):
                        usage = response.usage_metadata
                        input_tokens = getattr(usage, "prompt_token_count", 0) or 0
                        output_tokens = getattr(usage, "candidates_token_count", 0) or 0
                    
                    span_kwargs = {
                        "span_type": "LLM",
                        "name": "google.generate_content",
                        "model_name": model_name,
                        "model_provider": "google",
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
            def sync_wrapper(self_instance, *args, **kwargs):
                telemetry = instrumentor._get_telemetry()
                if telemetry is None:
                    return original_method(self_instance, *args, **kwargs)
                
                model_name = getattr(self_instance, "model_name", "gemini")
                start_time = time.time()
                error_info = None
                response = None
                
                try:
                    response = original_method(self_instance, *args, **kwargs)
                    return response
                except Exception as e:
                    error_info = e
                    raise
                finally:
                    duration_ms = round((time.time() - start_time) * 1000, 2)
                    input_tokens, output_tokens = 0, 0
                    
                    # Extract token usage from Gemini response
                    if response is not None and hasattr(response, "usage_metadata"):
                        usage = response.usage_metadata
                        input_tokens = getattr(usage, "prompt_token_count", 0) or 0
                        output_tokens = getattr(usage, "candidates_token_count", 0) or 0
                    
                    span_kwargs = {
                        "span_type": "LLM",
                        "name": "google.generate_content",
                        "model_name": model_name,
                        "model_provider": "google",
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
    
    def _create_embed_wrapper(self, original_method: Callable) -> Callable:
        """Create a wrapper for embed_content methods."""
        instrumentor = self
        
        @wraps(original_method)
        def wrapper(*args, **kwargs):
            telemetry = instrumentor._get_telemetry()
            if telemetry is None:
                return original_method(*args, **kwargs)
            
            model = kwargs.get("model", "embedding-001")
            start_time = time.time()
            error_info = None
            
            try:
                result = original_method(*args, **kwargs)
                return result
            except Exception as e:
                error_info = e
                raise
            finally:
                duration_ms = round((time.time() - start_time) * 1000, 2)
                
                span_kwargs = {
                    "span_type": "EMBEDDING",
                    "name": "google.embed_content",
                    "embedding_model": model,
                    "duration_ms": duration_ms,
                }
                
                if error_info:
                    span_kwargs["status"] = "ERROR"
                    span_kwargs["is_error"] = 1
                    span_kwargs["error_message"] = str(error_info)
                
                telemetry.send_span(**span_kwargs)
        
        return wrapper
    
    def _instrument(self) -> None:
        """Apply Google AI instrumentation."""
        import google.generativeai as genai
        
        # Instrument GenerativeModel.generate_content
        try:
            from google.generativeai import GenerativeModel
            wrap_method(
                GenerativeModel,
                "generate_content",
                lambda orig: self._create_generate_wrapper(orig, is_async=False),
                self._original_methods
            )
            if hasattr(GenerativeModel, "generate_content_async"):
                wrap_method(
                    GenerativeModel,
                    "generate_content_async",
                    lambda orig: self._create_generate_wrapper(orig, is_async=True),
                    self._original_methods
                )
            logger.debug("Instrumented GenerativeModel")
        except (ImportError, AttributeError) as e:
            logger.debug(f"Could not instrument GenerativeModel: {e}")
        
        # Instrument embed_content function
        try:
            if hasattr(genai, "embed_content"):
                original = genai.embed_content
                genai.embed_content = self._create_embed_wrapper(original)
                self._original_methods["genai.embed_content"] = original
                logger.debug("Instrumented embed_content")
        except (ImportError, AttributeError) as e:
            logger.debug(f"Could not instrument embed_content: {e}")
        
        logger.debug(f"Instrumented {len(self._original_methods)} Google AI methods")
    
    def _uninstrument(self) -> None:
        """Remove Google AI instrumentation."""
        try:
            from google.generativeai import GenerativeModel
            unwrap_method(GenerativeModel, "generate_content", self._original_methods)
            unwrap_method(GenerativeModel, "generate_content_async", self._original_methods)
        except ImportError:
            pass
        
        try:
            import google.generativeai as genai
            if "genai.embed_content" in self._original_methods:
                genai.embed_content = self._original_methods["genai.embed_content"]
                del self._original_methods["genai.embed_content"]
        except ImportError:
            pass
