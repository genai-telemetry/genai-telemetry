"""
Decorators for tracing LLM operations.
"""

import time
from functools import wraps
from typing import Callable

from genai_telemetry.core.utils import (
    extract_tokens_from_response,
    extract_content_from_response,
)


def _get_telemetry():
    """Import telemetry to avoid circular imports."""
    from genai_telemetry.core.telemetry import get_telemetry
    return get_telemetry()


def trace_llm(
    model_name: str,
    model_provider: str = "openai",
    extract_content: bool = False
) -> Callable:
    """
    Decorator to trace LLM calls.
    
    IMPORTANT: To capture token usage, you must return the FULL response object
    from the LLM client, not just response.choices[0].message.content.
    
    Args:
        model_name: Name of the model (e.g., "gpt-4o", "claude-3-opus")
        model_provider: Provider name (e.g., "openai", "anthropic")
        extract_content: If True, automatically extract and return just the content
                        string while still capturing token metrics. This allows you
                        to return the full response in your function but get just
                        the content string back.
    
    Example (correct - captures tokens):
        @trace_llm(model_name="gpt-4o", model_provider="openai")
        def chat(message):
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": message}]
            )
            return response  # Return FULL response
        
        answer = chat("Hello")
        print(answer.choices[0].message.content)  # Extract content here
    
    Example (with extract_content=True):
        @trace_llm(model_name="gpt-4o", model_provider="openai", extract_content=True)
        def chat(message):
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": message}]
            )
            return response  # Return FULL response
        
        answer = chat("Hello")  # answer is now just the content string
        print(answer)
    
    Example (WRONG - tokens will be 0):
        @trace_llm(model_name="gpt-4o", model_provider="openai")
        def chat(message):
            response = client.chat.completions.create(...)
            return response.choices[0].message.content  # DON'T DO THIS
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            telemetry = _get_telemetry()
            start = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration = round((time.time() - start) * 1000, 2)
                
                # Extract tokens using the helper function
                input_tokens, output_tokens = extract_tokens_from_response(result)
                
                telemetry.send_span(
                    span_type="LLM",
                    name=func.__name__,
                    model_name=model_name,
                    model_provider=model_provider,
                    duration_ms=duration,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=input_tokens + output_tokens
                )
                
                # If extract_content is True, return just the content string
                if extract_content:
                    return extract_content_from_response(result, model_provider)
                
                return result
                
            except Exception as e:
                duration = round((time.time() - start) * 1000, 2)
                telemetry.send_span(
                    span_type="LLM",
                    name=func.__name__,
                    model_name=model_name,
                    model_provider=model_provider,
                    duration_ms=duration,
                    status="ERROR",
                    is_error=1,
                    error_message=str(e),
                    error_type=type(e).__name__
                )
                raise
        return wrapper
    return decorator


def trace_embedding(model: str) -> Callable:
    """Decorator to trace embedding calls."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            telemetry = _get_telemetry()
            start = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration = round((time.time() - start) * 1000, 2)
                
                # Try to extract token usage from embedding response
                input_tokens = 0
                if hasattr(result, "usage") and result.usage:
                    input_tokens = getattr(result.usage, "prompt_tokens", 0) or 0
                    if not input_tokens:
                        input_tokens = getattr(result.usage, "total_tokens", 0) or 0
                
                telemetry.send_span(
                    span_type="EMBEDDING",
                    name=func.__name__,
                    embedding_model=model,
                    duration_ms=duration,
                    input_tokens=input_tokens
                )
                return result
                
            except Exception as e:
                duration = round((time.time() - start) * 1000, 2)
                telemetry.send_span(
                    span_type="EMBEDDING",
                    name=func.__name__,
                    embedding_model=model,
                    duration_ms=duration,
                    status="ERROR",
                    is_error=1,
                    error_message=str(e)
                )
                raise
        return wrapper
    return decorator


def trace_retrieval(vector_store: str, embedding_model: str = None) -> Callable:
    """Decorator to trace retrieval calls."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            telemetry = _get_telemetry()
            start = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration = round((time.time() - start) * 1000, 2)
                
                docs_count = len(result) if isinstance(result, (list, tuple)) else 0
                
                telemetry.send_span(
                    span_type="RETRIEVER",
                    name=func.__name__,
                    vector_store=vector_store,
                    embedding_model=embedding_model,
                    documents_retrieved=docs_count,
                    duration_ms=duration
                )
                return result
                
            except Exception as e:
                duration = round((time.time() - start) * 1000, 2)
                telemetry.send_span(
                    span_type="RETRIEVER",
                    name=func.__name__,
                    vector_store=vector_store,
                    duration_ms=duration,
                    status="ERROR",
                    is_error=1,
                    error_message=str(e)
                )
                raise
        return wrapper
    return decorator


def trace_tool(tool_name: str) -> Callable:
    """Decorator to trace tool calls."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            telemetry = _get_telemetry()
            start = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration = round((time.time() - start) * 1000, 2)
                
                telemetry.send_span(
                    span_type="TOOL",
                    name=func.__name__,
                    tool_name=tool_name,
                    duration_ms=duration
                )
                return result
                
            except Exception as e:
                duration = round((time.time() - start) * 1000, 2)
                telemetry.send_span(
                    span_type="TOOL",
                    name=func.__name__,
                    tool_name=tool_name,
                    duration_ms=duration,
                    status="ERROR",
                    is_error=1,
                    error_message=str(e)
                )
                raise
        return wrapper
    return decorator


def trace_chain(name: str) -> Callable:
    """Decorator to trace chain/pipeline calls."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            telemetry = _get_telemetry()
            telemetry.new_trace()
            start = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration = round((time.time() - start) * 1000, 2)
                
                telemetry.send_span(
                    span_type="CHAIN",
                    name=name,
                    duration_ms=duration
                )
                return result
                
            except Exception as e:
                duration = round((time.time() - start) * 1000, 2)
                telemetry.send_span(
                    span_type="CHAIN",
                    name=name,
                    duration_ms=duration,
                    status="ERROR",
                    is_error=1,
                    error_message=str(e)
                )
                raise
        return wrapper
    return decorator


def trace_agent(agent_name: str, agent_type: str = None) -> Callable:
    """Decorator to trace agent calls."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            telemetry = _get_telemetry()
            telemetry.new_trace()
            start = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration = round((time.time() - start) * 1000, 2)
                
                telemetry.send_span(
                    span_type="AGENT",
                    name=func.__name__,
                    agent_name=agent_name,
                    agent_type=agent_type,
                    duration_ms=duration
                )
                return result
                
            except Exception as e:
                duration = round((time.time() - start) * 1000, 2)
                telemetry.send_span(
                    span_type="AGENT",
                    name=func.__name__,
                    agent_name=agent_name,
                    agent_type=agent_type,
                    duration_ms=duration,
                    status="ERROR",
                    is_error=1,
                    error_message=str(e)
                )
                raise
        return wrapper
    return decorator
