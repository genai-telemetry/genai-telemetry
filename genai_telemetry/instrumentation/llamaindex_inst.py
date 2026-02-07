"""
LlamaIndex Auto-Instrumentation.

Automatically traces LlamaIndex components including:
- Query Engines
- Retrievers
- LLMs
- Embeddings
- Agents
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


class LlamaIndexInstrumentor(BaseInstrumentor):
    """Instrumentor for LlamaIndex."""
    
    _original_methods = {}
    
    @property
    def name(self) -> str:
        return "LlamaIndex"
    
    def _check_installed(self) -> bool:
        return (
            safe_import("llama_index") is not None or
            safe_import("llama_index.core") is not None
        )
    
    def _get_telemetry(self):
        """Get telemetry instance, handling case where it's not set up."""
        try:
            from genai_telemetry.core.telemetry import get_telemetry
            return get_telemetry()
        except RuntimeError:
            return None
    
    def _create_query_wrapper(self, original_method: Callable) -> Callable:
        """Create a wrapper for query methods."""
        instrumentor = self
        
        @wraps(original_method)
        def wrapper(self_instance, *args, **kwargs):
            telemetry = instrumentor._get_telemetry()
            if telemetry is None:
                return original_method(self_instance, *args, **kwargs)
            
            # Start a new trace for queries
            telemetry.new_trace()
            engine_name = type(self_instance).__name__
            start_time = time.time()
            error_info = None
            
            try:
                result = original_method(self_instance, *args, **kwargs)
                return result
            except Exception as e:
                error_info = e
                raise
            finally:
                duration_ms = round((time.time() - start_time) * 1000, 2)
                
                span_kwargs = {
                    "span_type": "CHAIN",
                    "name": f"llamaindex.{engine_name}.query",
                    "duration_ms": duration_ms,
                }
                
                if error_info:
                    span_kwargs["status"] = "ERROR"
                    span_kwargs["is_error"] = 1
                    span_kwargs["error_message"] = str(error_info)
                    span_kwargs["error_type"] = type(error_info).__name__
                
                telemetry.send_span(**span_kwargs)
        
        return wrapper
    
    def _create_aquery_wrapper(self, original_method: Callable) -> Callable:
        """Create a wrapper for async query methods."""
        instrumentor = self
        
        @wraps(original_method)
        async def wrapper(self_instance, *args, **kwargs):
            telemetry = instrumentor._get_telemetry()
            if telemetry is None:
                return await original_method(self_instance, *args, **kwargs)
            
            # Start a new trace for queries
            telemetry.new_trace()
            engine_name = type(self_instance).__name__
            start_time = time.time()
            error_info = None
            
            try:
                result = await original_method(self_instance, *args, **kwargs)
                return result
            except Exception as e:
                error_info = e
                raise
            finally:
                duration_ms = round((time.time() - start_time) * 1000, 2)
                
                span_kwargs = {
                    "span_type": "CHAIN",
                    "name": f"llamaindex.{engine_name}.aquery",
                    "duration_ms": duration_ms,
                }
                
                if error_info:
                    span_kwargs["status"] = "ERROR"
                    span_kwargs["is_error"] = 1
                    span_kwargs["error_message"] = str(error_info)
                    span_kwargs["error_type"] = type(error_info).__name__
                
                telemetry.send_span(**span_kwargs)
        
        return wrapper
    
    def _create_retrieve_wrapper(self, original_method: Callable) -> Callable:
        """Create a wrapper for retrieve methods."""
        instrumentor = self
        
        @wraps(original_method)
        def wrapper(self_instance, *args, **kwargs):
            telemetry = instrumentor._get_telemetry()
            if telemetry is None:
                return original_method(self_instance, *args, **kwargs)
            
            retriever_name = type(self_instance).__name__
            start_time = time.time()
            error_info = None
            result = None
            
            try:
                result = original_method(self_instance, *args, **kwargs)
                return result
            except Exception as e:
                error_info = e
                raise
            finally:
                duration_ms = round((time.time() - start_time) * 1000, 2)
                docs_count = len(result) if result else 0
                
                span_kwargs = {
                    "span_type": "RETRIEVER",
                    "name": f"llamaindex.{retriever_name}.retrieve",
                    "vector_store": "llamaindex",
                    "documents_retrieved": docs_count,
                    "duration_ms": duration_ms,
                }
                
                if error_info:
                    span_kwargs["status"] = "ERROR"
                    span_kwargs["is_error"] = 1
                    span_kwargs["error_message"] = str(error_info)
                
                telemetry.send_span(**span_kwargs)
        
        return wrapper
    
    def _create_llm_complete_wrapper(self, original_method: Callable) -> Callable:
        """Create a wrapper for LLM complete methods."""
        instrumentor = self
        
        @wraps(original_method)
        def wrapper(self_instance, *args, **kwargs):
            telemetry = instrumentor._get_telemetry()
            if telemetry is None:
                return original_method(self_instance, *args, **kwargs)
            
            model_name = getattr(self_instance, "model", "unknown")
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
                
                # Try to extract token info from LlamaIndex response
                if response is not None:
                    if hasattr(response, "raw"):
                        input_tokens, output_tokens = extract_tokens_from_response(response.raw)
                    elif hasattr(response, "additional_kwargs"):
                        usage = response.additional_kwargs.get("usage", {})
                        input_tokens = usage.get("prompt_tokens", 0) or usage.get("input_tokens", 0)
                        output_tokens = usage.get("completion_tokens", 0) or usage.get("output_tokens", 0)
                
                span_kwargs = {
                    "span_type": "LLM",
                    "name": f"llamaindex.{type(self_instance).__name__}.complete",
                    "model_name": model_name,
                    "model_provider": "llamaindex",
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
        
        return wrapper
    
    def _create_llm_chat_wrapper(self, original_method: Callable) -> Callable:
        """Create a wrapper for LLM chat methods."""
        instrumentor = self
        
        @wraps(original_method)
        def wrapper(self_instance, *args, **kwargs):
            telemetry = instrumentor._get_telemetry()
            if telemetry is None:
                return original_method(self_instance, *args, **kwargs)
            
            model_name = getattr(self_instance, "model", "unknown")
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
                
                if response is not None:
                    if hasattr(response, "raw"):
                        input_tokens, output_tokens = extract_tokens_from_response(response.raw)
                    elif hasattr(response, "additional_kwargs"):
                        usage = response.additional_kwargs.get("usage", {})
                        input_tokens = usage.get("prompt_tokens", 0) or usage.get("input_tokens", 0)
                        output_tokens = usage.get("completion_tokens", 0) or usage.get("output_tokens", 0)
                
                span_kwargs = {
                    "span_type": "LLM",
                    "name": f"llamaindex.{type(self_instance).__name__}.chat",
                    "model_name": model_name,
                    "model_provider": "llamaindex",
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
        
        return wrapper
    
    def _create_embed_wrapper(self, original_method: Callable, method_name: str) -> Callable:
        """Create a wrapper for embedding methods."""
        instrumentor = self
        
        @wraps(original_method)
        def wrapper(self_instance, *args, **kwargs):
            telemetry = instrumentor._get_telemetry()
            if telemetry is None:
                return original_method(self_instance, *args, **kwargs)
            
            model_name = getattr(self_instance, "model_name", "unknown")
            start_time = time.time()
            error_info = None
            
            try:
                result = original_method(self_instance, *args, **kwargs)
                return result
            except Exception as e:
                error_info = e
                raise
            finally:
                duration_ms = round((time.time() - start_time) * 1000, 2)
                
                span_kwargs = {
                    "span_type": "EMBEDDING",
                    "name": f"llamaindex.{type(self_instance).__name__}.{method_name}",
                    "embedding_model": model_name,
                    "duration_ms": duration_ms,
                }
                
                if error_info:
                    span_kwargs["status"] = "ERROR"
                    span_kwargs["is_error"] = 1
                    span_kwargs["error_message"] = str(error_info)
                
                telemetry.send_span(**span_kwargs)
        
        return wrapper
    
    def _instrument(self) -> None:
        """Apply LlamaIndex instrumentation."""
        
        # Try llama_index.core first (newer versions), then llama_index (older versions)
        core_module = safe_import("llama_index.core")
        legacy_module = safe_import("llama_index")
        
        # Instrument BaseQueryEngine
        try:
            if core_module:
                from llama_index.core.base.base_query_engine import BaseQueryEngine
            else:
                from llama_index.indices.query.base import BaseQueryEngine
            
            wrap_method(
                BaseQueryEngine,
                "query",
                lambda orig: self._create_query_wrapper(orig),
                self._original_methods
            )
            if hasattr(BaseQueryEngine, "aquery"):
                wrap_method(
                    BaseQueryEngine,
                    "aquery",
                    lambda orig: self._create_aquery_wrapper(orig),
                    self._original_methods
                )
            logger.debug("Instrumented BaseQueryEngine")
        except (ImportError, AttributeError) as e:
            logger.debug(f"Could not instrument BaseQueryEngine: {e}")
        
        # Instrument BaseRetriever
        try:
            if core_module:
                from llama_index.core.retrievers import BaseRetriever
            else:
                from llama_index.retrievers import BaseRetriever
            
            wrap_method(
                BaseRetriever,
                "retrieve",
                lambda orig: self._create_retrieve_wrapper(orig),
                self._original_methods
            )
            logger.debug("Instrumented LlamaIndex BaseRetriever")
        except (ImportError, AttributeError) as e:
            logger.debug(f"Could not instrument LlamaIndex BaseRetriever: {e}")
        
        # Instrument LLM base class
        try:
            if core_module:
                from llama_index.core.llms import LLM
            else:
                from llama_index.llms import LLM
            
            wrap_method(
                LLM,
                "complete",
                lambda orig: self._create_llm_complete_wrapper(orig),
                self._original_methods
            )
            wrap_method(
                LLM,
                "chat",
                lambda orig: self._create_llm_chat_wrapper(orig),
                self._original_methods
            )
            logger.debug("Instrumented LlamaIndex LLM")
        except (ImportError, AttributeError) as e:
            logger.debug(f"Could not instrument LlamaIndex LLM: {e}")
        
        # Instrument BaseEmbedding
        try:
            if core_module:
                from llama_index.core.embeddings import BaseEmbedding
            else:
                from llama_index.embeddings import BaseEmbedding
            
            wrap_method(
                BaseEmbedding,
                "get_text_embedding",
                lambda orig: self._create_embed_wrapper(orig, "get_text_embedding"),
                self._original_methods
            )
            wrap_method(
                BaseEmbedding,
                "get_query_embedding",
                lambda orig: self._create_embed_wrapper(orig, "get_query_embedding"),
                self._original_methods
            )
            logger.debug("Instrumented LlamaIndex BaseEmbedding")
        except (ImportError, AttributeError) as e:
            logger.debug(f"Could not instrument LlamaIndex BaseEmbedding: {e}")
        
        logger.debug(f"Instrumented {len(self._original_methods)} LlamaIndex methods")
    
    def _uninstrument(self) -> None:
        """Remove LlamaIndex instrumentation."""
        core_module = safe_import("llama_index.core")
        
        try:
            if core_module:
                from llama_index.core.base.base_query_engine import BaseQueryEngine
            else:
                from llama_index.indices.query.base import BaseQueryEngine
            unwrap_method(BaseQueryEngine, "query", self._original_methods)
            unwrap_method(BaseQueryEngine, "aquery", self._original_methods)
        except ImportError:
            pass
        
        try:
            if core_module:
                from llama_index.core.retrievers import BaseRetriever
            else:
                from llama_index.retrievers import BaseRetriever
            unwrap_method(BaseRetriever, "retrieve", self._original_methods)
        except ImportError:
            pass
        
        try:
            if core_module:
                from llama_index.core.llms import LLM
            else:
                from llama_index.llms import LLM
            unwrap_method(LLM, "complete", self._original_methods)
            unwrap_method(LLM, "chat", self._original_methods)
        except ImportError:
            pass
        
        try:
            if core_module:
                from llama_index.core.embeddings import BaseEmbedding
            else:
                from llama_index.embeddings import BaseEmbedding
            unwrap_method(BaseEmbedding, "get_text_embedding", self._original_methods)
            unwrap_method(BaseEmbedding, "get_query_embedding", self._original_methods)
        except ImportError:
            pass
