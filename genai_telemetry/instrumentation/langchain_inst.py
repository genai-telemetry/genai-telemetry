"""
LangChain Auto-Instrumentation.

Automatically traces LangChain components including:
- LLMs (BaseLLM, BaseChatModel)
- Chains (Chain, LLMChain, etc.)
- Agents (AgentExecutor)
- Retrievers (BaseRetriever)
- Embeddings (Embeddings)
- Tools
"""

import time
import logging
from functools import wraps
from typing import Any, Callable, Dict, List, Optional

from genai_telemetry.instrumentation.base import (
    BaseInstrumentor,
    safe_import,
    wrap_method,
    unwrap_method,
)
from genai_telemetry.core.utils import extract_tokens_from_response

logger = logging.getLogger(__name__)


class LangChainInstrumentor(BaseInstrumentor):
    """Instrumentor for LangChain."""
    
    _original_methods = {}
    
    @property
    def name(self) -> str:
        return "LangChain"
    
    def _check_installed(self) -> bool:
        # Check for langchain-core or langchain
        return (
            safe_import("langchain_core") is not None or
            safe_import("langchain") is not None
        )
    
    def _get_telemetry(self):
        """Get telemetry instance, handling case where it's not set up."""
        try:
            from genai_telemetry.core.telemetry import get_telemetry
            return get_telemetry()
        except RuntimeError:
            return None
    
    def _extract_model_info(self, instance: Any) -> Dict[str, str]:
        """Extract model name and provider from a LangChain LLM instance."""
        model_name = "unknown"
        model_provider = "langchain"
        
        # Try various attributes that different LLM classes use
        for attr in ["model_name", "model", "model_id", "repo_id"]:
            if hasattr(instance, attr):
                val = getattr(instance, attr)
                if val:
                    model_name = str(val)
                    break
        
        # Determine provider from class name
        class_name = type(instance).__name__.lower()
        if "openai" in class_name or "gpt" in class_name:
            model_provider = "openai"
        elif "anthropic" in class_name or "claude" in class_name:
            model_provider = "anthropic"
        elif "cohere" in class_name:
            model_provider = "cohere"
        elif "huggingface" in class_name or "hf" in class_name:
            model_provider = "huggingface"
        elif "google" in class_name or "gemini" in class_name or "palm" in class_name:
            model_provider = "google"
        elif "bedrock" in class_name:
            model_provider = "aws_bedrock"
        elif "ollama" in class_name:
            model_provider = "ollama"
        elif "mistral" in class_name:
            model_provider = "mistral"
        
        return {"model_name": model_name, "model_provider": model_provider}
    
    def _create_llm_invoke_wrapper(self, original_method: Callable) -> Callable:
        """Create a wrapper for LLM invoke methods."""
        instrumentor = self
        
        @wraps(original_method)
        def wrapper(self_instance, *args, **kwargs):
            telemetry = instrumentor._get_telemetry()
            if telemetry is None:
                return original_method(self_instance, *args, **kwargs)
            
            model_info = instrumentor._extract_model_info(self_instance)
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
                    input_tokens, output_tokens = extract_tokens_from_response(response)
                
                span_kwargs = {
                    "span_type": "LLM",
                    "name": f"langchain.{type(self_instance).__name__}.invoke",
                    "model_name": model_info["model_name"],
                    "model_provider": model_info["model_provider"],
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
    
    def _create_llm_ainvoke_wrapper(self, original_method: Callable) -> Callable:
        """Create a wrapper for async LLM invoke methods."""
        instrumentor = self
        
        @wraps(original_method)
        async def wrapper(self_instance, *args, **kwargs):
            telemetry = instrumentor._get_telemetry()
            if telemetry is None:
                return await original_method(self_instance, *args, **kwargs)
            
            model_info = instrumentor._extract_model_info(self_instance)
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
                
                if response is not None:
                    input_tokens, output_tokens = extract_tokens_from_response(response)
                
                span_kwargs = {
                    "span_type": "LLM",
                    "name": f"langchain.{type(self_instance).__name__}.ainvoke",
                    "model_name": model_info["model_name"],
                    "model_provider": model_info["model_provider"],
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
    
    def _create_chain_invoke_wrapper(self, original_method: Callable) -> Callable:
        """Create a wrapper for Chain invoke methods."""
        instrumentor = self
        
        @wraps(original_method)
        def wrapper(self_instance, *args, **kwargs):
            telemetry = instrumentor._get_telemetry()
            if telemetry is None:
                return original_method(self_instance, *args, **kwargs)
            
            # Start a new trace for chains
            telemetry.new_trace()
            chain_name = getattr(self_instance, "name", type(self_instance).__name__)
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
                    "name": f"langchain.{chain_name}.invoke",
                    "duration_ms": duration_ms,
                }
                
                if error_info:
                    span_kwargs["status"] = "ERROR"
                    span_kwargs["is_error"] = 1
                    span_kwargs["error_message"] = str(error_info)
                    span_kwargs["error_type"] = type(error_info).__name__
                
                telemetry.send_span(**span_kwargs)
        
        return wrapper
    
    def _create_retriever_invoke_wrapper(self, original_method: Callable) -> Callable:
        """Create a wrapper for Retriever invoke methods."""
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
                docs_count = len(result) if result and isinstance(result, list) else 0
                
                # Try to get vector store name
                vector_store = "unknown"
                if hasattr(self_instance, "vectorstore"):
                    vector_store = type(self_instance.vectorstore).__name__
                elif hasattr(self_instance, "vector_store"):
                    vector_store = type(self_instance.vector_store).__name__
                
                span_kwargs = {
                    "span_type": "RETRIEVER",
                    "name": f"langchain.{retriever_name}.invoke",
                    "vector_store": vector_store,
                    "documents_retrieved": docs_count,
                    "duration_ms": duration_ms,
                }
                
                if error_info:
                    span_kwargs["status"] = "ERROR"
                    span_kwargs["is_error"] = 1
                    span_kwargs["error_message"] = str(error_info)
                
                telemetry.send_span(**span_kwargs)
        
        return wrapper
    
    def _create_embeddings_wrapper(self, original_method: Callable, method_name: str) -> Callable:
        """Create a wrapper for Embeddings methods."""
        instrumentor = self
        
        @wraps(original_method)
        def wrapper(self_instance, *args, **kwargs):
            telemetry = instrumentor._get_telemetry()
            if telemetry is None:
                return original_method(self_instance, *args, **kwargs)
            
            model_name = getattr(self_instance, "model", "unknown")
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
                    "name": f"langchain.{type(self_instance).__name__}.{method_name}",
                    "embedding_model": model_name,
                    "duration_ms": duration_ms,
                }
                
                if error_info:
                    span_kwargs["status"] = "ERROR"
                    span_kwargs["is_error"] = 1
                    span_kwargs["error_message"] = str(error_info)
                
                telemetry.send_span(**span_kwargs)
        
        return wrapper
    
    def _create_tool_invoke_wrapper(self, original_method: Callable) -> Callable:
        """Create a wrapper for Tool invoke methods."""
        instrumentor = self
        
        @wraps(original_method)
        def wrapper(self_instance, *args, **kwargs):
            telemetry = instrumentor._get_telemetry()
            if telemetry is None:
                return original_method(self_instance, *args, **kwargs)
            
            tool_name = getattr(self_instance, "name", type(self_instance).__name__)
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
                    "span_type": "TOOL",
                    "name": f"langchain.tool.invoke",
                    "tool_name": tool_name,
                    "duration_ms": duration_ms,
                }
                
                if error_info:
                    span_kwargs["status"] = "ERROR"
                    span_kwargs["is_error"] = 1
                    span_kwargs["error_message"] = str(error_info)
                
                telemetry.send_span(**span_kwargs)
        
        return wrapper
    
    def _create_agent_invoke_wrapper(self, original_method: Callable) -> Callable:
        """Create a wrapper for Agent invoke methods."""
        instrumentor = self
        
        @wraps(original_method)
        def wrapper(self_instance, *args, **kwargs):
            telemetry = instrumentor._get_telemetry()
            if telemetry is None:
                return original_method(self_instance, *args, **kwargs)
            
            # Start a new trace for agents
            telemetry.new_trace()
            agent_name = getattr(self_instance, "name", type(self_instance).__name__)
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
                    "span_type": "AGENT",
                    "name": f"langchain.{agent_name}.invoke",
                    "agent_name": agent_name,
                    "duration_ms": duration_ms,
                }
                
                if error_info:
                    span_kwargs["status"] = "ERROR"
                    span_kwargs["is_error"] = 1
                    span_kwargs["error_message"] = str(error_info)
                    span_kwargs["error_type"] = type(error_info).__name__
                
                telemetry.send_span(**span_kwargs)
        
        return wrapper
    
    def _instrument(self) -> None:
        """Apply LangChain instrumentation."""
        
        # Instrument BaseChatModel (langchain_core)
        try:
            from langchain_core.language_models.chat_models import BaseChatModel
            wrap_method(
                BaseChatModel,
                "invoke",
                lambda orig: self._create_llm_invoke_wrapper(orig),
                self._original_methods
            )
            wrap_method(
                BaseChatModel,
                "ainvoke",
                lambda orig: self._create_llm_ainvoke_wrapper(orig),
                self._original_methods
            )
            logger.debug("Instrumented BaseChatModel")
        except (ImportError, AttributeError) as e:
            logger.debug(f"Could not instrument BaseChatModel: {e}")
        
        # Instrument BaseLLM (langchain_core)
        try:
            from langchain_core.language_models.llms import BaseLLM
            wrap_method(
                BaseLLM,
                "invoke",
                lambda orig: self._create_llm_invoke_wrapper(orig),
                self._original_methods
            )
            wrap_method(
                BaseLLM,
                "ainvoke",
                lambda orig: self._create_llm_ainvoke_wrapper(orig),
                self._original_methods
            )
            logger.debug("Instrumented BaseLLM")
        except (ImportError, AttributeError) as e:
            logger.debug(f"Could not instrument BaseLLM: {e}")
        
        # Instrument BaseRetriever
        try:
            from langchain_core.retrievers import BaseRetriever
            wrap_method(
                BaseRetriever,
                "invoke",
                lambda orig: self._create_retriever_invoke_wrapper(orig),
                self._original_methods
            )
            logger.debug("Instrumented BaseRetriever")
        except (ImportError, AttributeError) as e:
            logger.debug(f"Could not instrument BaseRetriever: {e}")
        
        # Instrument Embeddings
        try:
            from langchain_core.embeddings import Embeddings
            wrap_method(
                Embeddings,
                "embed_documents",
                lambda orig: self._create_embeddings_wrapper(orig, "embed_documents"),
                self._original_methods
            )
            wrap_method(
                Embeddings,
                "embed_query",
                lambda orig: self._create_embeddings_wrapper(orig, "embed_query"),
                self._original_methods
            )
            logger.debug("Instrumented Embeddings")
        except (ImportError, AttributeError) as e:
            logger.debug(f"Could not instrument Embeddings: {e}")
        
        # Instrument BaseTool
        try:
            from langchain_core.tools import BaseTool
            wrap_method(
                BaseTool,
                "invoke",
                lambda orig: self._create_tool_invoke_wrapper(orig),
                self._original_methods
            )
            logger.debug("Instrumented BaseTool")
        except (ImportError, AttributeError) as e:
            logger.debug(f"Could not instrument BaseTool: {e}")
        
        # Instrument Runnable (covers chains and LCEL)
        try:
            from langchain_core.runnables import Runnable, RunnableSequence
            # RunnableSequence is the most common chain type in LCEL
            wrap_method(
                RunnableSequence,
                "invoke",
                lambda orig: self._create_chain_invoke_wrapper(orig),
                self._original_methods
            )
            logger.debug("Instrumented RunnableSequence")
        except (ImportError, AttributeError) as e:
            logger.debug(f"Could not instrument Runnable: {e}")
        
        # Instrument AgentExecutor
        try:
            from langchain.agents import AgentExecutor
            wrap_method(
                AgentExecutor,
                "invoke",
                lambda orig: self._create_agent_invoke_wrapper(orig),
                self._original_methods
            )
            logger.debug("Instrumented AgentExecutor")
        except (ImportError, AttributeError) as e:
            logger.debug(f"Could not instrument AgentExecutor: {e}")
        
        logger.debug(f"Instrumented {len(self._original_methods)} LangChain methods")
    
    def _uninstrument(self) -> None:
        """Remove LangChain instrumentation."""
        try:
            from langchain_core.language_models.chat_models import BaseChatModel
            unwrap_method(BaseChatModel, "invoke", self._original_methods)
            unwrap_method(BaseChatModel, "ainvoke", self._original_methods)
        except ImportError:
            pass
        
        try:
            from langchain_core.language_models.llms import BaseLLM
            unwrap_method(BaseLLM, "invoke", self._original_methods)
            unwrap_method(BaseLLM, "ainvoke", self._original_methods)
        except ImportError:
            pass
        
        try:
            from langchain_core.retrievers import BaseRetriever
            unwrap_method(BaseRetriever, "invoke", self._original_methods)
        except ImportError:
            pass
        
        try:
            from langchain_core.embeddings import Embeddings
            unwrap_method(Embeddings, "embed_documents", self._original_methods)
            unwrap_method(Embeddings, "embed_query", self._original_methods)
        except ImportError:
            pass
        
        try:
            from langchain_core.tools import BaseTool
            unwrap_method(BaseTool, "invoke", self._original_methods)
        except ImportError:
            pass
        
        try:
            from langchain_core.runnables import RunnableSequence
            unwrap_method(RunnableSequence, "invoke", self._original_methods)
        except ImportError:
            pass
        
        try:
            from langchain.agents import AgentExecutor
            unwrap_method(AgentExecutor, "invoke", self._original_methods)
        except ImportError:
            pass
