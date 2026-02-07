"""
Auto-Instrumentation for GenAI Telemetry.

This module provides automatic instrumentation for popular LLM frameworks
with zero code changes required. Simply call `auto_instrument()` after
setting up telemetry.

Supported frameworks:
- OpenAI Python SDK
- Anthropic Python SDK
- LangChain / LangChain-Core
- LlamaIndex
- CrewAI
- AutoGen
- Haystack

Usage:
    from genai_telemetry import setup_telemetry, auto_instrument

    # Setup telemetry first
    setup_telemetry(
        workflow_name="my-app",
        exporter="splunk",
        splunk_url="http://splunk:8088",
        splunk_token="your-token"
    )

    # Enable auto-instrumentation
    auto_instrument()

    # Now all LLM calls are automatically traced!
    from openai import OpenAI
    client = OpenAI()
    response = client.chat.completions.create(...)  # Automatically traced!
"""

import logging
from typing import List, Optional, Set, Dict, Any

from genai_telemetry.instrumentation.base import BaseInstrumentor

logger = logging.getLogger(__name__)

# Registry of all available instrumentors
_INSTRUMENTORS: Dict[str, type] = {}
_active_instrumentors: List[BaseInstrumentor] = []


def _register_instrumentors():
    """Register all available instrumentors."""
    global _INSTRUMENTORS
    
    if _INSTRUMENTORS:
        return  # Already registered
    
    # Import and register each instrumentor
    try:
        from genai_telemetry.instrumentation.openai_inst import OpenAIInstrumentor
        _INSTRUMENTORS["openai"] = OpenAIInstrumentor
    except ImportError as e:
        logger.debug(f"OpenAI instrumentor not available: {e}")
    
    try:
        from genai_telemetry.instrumentation.anthropic_inst import AnthropicInstrumentor
        _INSTRUMENTORS["anthropic"] = AnthropicInstrumentor
    except ImportError as e:
        logger.debug(f"Anthropic instrumentor not available: {e}")
    
    try:
        from genai_telemetry.instrumentation.langchain_inst import LangChainInstrumentor
        _INSTRUMENTORS["langchain"] = LangChainInstrumentor
    except ImportError as e:
        logger.debug(f"LangChain instrumentor not available: {e}")
    
    try:
        from genai_telemetry.instrumentation.llamaindex_inst import LlamaIndexInstrumentor
        _INSTRUMENTORS["llamaindex"] = LlamaIndexInstrumentor
    except ImportError as e:
        logger.debug(f"LlamaIndex instrumentor not available: {e}")
    
    try:
        from genai_telemetry.instrumentation.google_inst import GoogleAIInstrumentor
        _INSTRUMENTORS["google"] = GoogleAIInstrumentor
    except ImportError as e:
        logger.debug(f"Google AI instrumentor not available: {e}")


def auto_instrument(
    frameworks: Optional[List[str]] = None,
    exclude: Optional[List[str]] = None,
) -> Dict[str, bool]:
    """
    Automatically instrument LLM frameworks for tracing.
    
    This function monkey-patches popular LLM libraries to automatically
    send telemetry data for all LLM calls. Call this once after setting
    up telemetry with `setup_telemetry()`.
    
    Args:
        frameworks: List of frameworks to instrument. If None, instruments all
                   available frameworks. Options: "openai", "anthropic", 
                   "langchain", "llamaindex", "crewai", "autogen", "haystack"
        exclude: List of frameworks to exclude from instrumentation.
    
    Returns:
        Dict mapping framework names to whether instrumentation succeeded.
    
    Example:
        >>> from genai_telemetry import setup_telemetry, auto_instrument
        >>> 
        >>> # Setup telemetry
        >>> setup_telemetry(
        ...     workflow_name="my-app",
        ...     exporter="splunk",
        ...     splunk_url="http://splunk:8088",
        ...     splunk_token="token"
        ... )
        >>> 
        >>> # Instrument all frameworks
        >>> results = auto_instrument()
        >>> print(results)
        {'openai': True, 'anthropic': True, 'langchain': True, ...}
        >>> 
        >>> # Or instrument specific frameworks only
        >>> results = auto_instrument(frameworks=["openai", "langchain"])
        >>> 
        >>> # Or exclude specific frameworks
        >>> results = auto_instrument(exclude=["anthropic"])
    
    Note:
        - Call this AFTER `setup_telemetry()` but BEFORE importing/using LLM clients
        - Instrumentation is idempotent - calling multiple times is safe
        - Frameworks that aren't installed are silently skipped
    """
    global _active_instrumentors
    
    # Register instrumentors if not already done
    _register_instrumentors()
    
    # Determine which frameworks to instrument
    if frameworks is None:
        frameworks_to_instrument = set(_INSTRUMENTORS.keys())
    else:
        frameworks_to_instrument = set(f.lower() for f in frameworks)
    
    if exclude:
        frameworks_to_instrument -= set(e.lower() for e in exclude)
    
    results = {}
    
    for name, instrumentor_class in _INSTRUMENTORS.items():
        if name not in frameworks_to_instrument:
            continue
        
        # Check if already instrumented
        existing = next(
            (i for i in _active_instrumentors if type(i).__name__ == instrumentor_class.__name__),
            None
        )
        
        if existing and existing.is_instrumented:
            results[name] = True
            continue
        
        # Create and run instrumentor
        instrumentor = instrumentor_class()
        success = instrumentor.instrument()
        results[name] = success
        
        if success:
            _active_instrumentors.append(instrumentor)
    
    # Log summary
    successful = [k for k, v in results.items() if v]
    failed = [k for k, v in results.items() if not v]
    
    if successful:
        logger.info(f"Auto-instrumented: {', '.join(successful)}")
    if failed:
        logger.debug(f"Not instrumented (not installed or failed): {', '.join(failed)}")
    
    return results


def uninstrument(frameworks: Optional[List[str]] = None) -> Dict[str, bool]:
    """
    Remove auto-instrumentation from frameworks.
    
    Args:
        frameworks: List of frameworks to uninstrument. If None, 
                   uninstruments all currently instrumented frameworks.
    
    Returns:
        Dict mapping framework names to whether uninstrumentation succeeded.
    
    Example:
        >>> uninstrument()  # Remove all instrumentation
        >>> uninstrument(frameworks=["openai"])  # Remove only OpenAI
    """
    global _active_instrumentors
    
    results = {}
    remaining = []
    
    for instrumentor in _active_instrumentors:
        name = instrumentor.name.lower()
        
        if frameworks is not None and name not in [f.lower() for f in frameworks]:
            remaining.append(instrumentor)
            continue
        
        success = instrumentor.uninstrument()
        results[name] = success
        
        if not success:
            remaining.append(instrumentor)
    
    _active_instrumentors = remaining
    
    if results:
        logger.info(f"Uninstrumented: {', '.join(results.keys())}")
    
    return results


def get_instrumented_frameworks() -> List[str]:
    """
    Get list of currently instrumented frameworks.
    
    Returns:
        List of framework names that are currently instrumented.
    
    Example:
        >>> auto_instrument()
        >>> get_instrumented_frameworks()
        ['openai', 'langchain', 'llamaindex']
    """
    return [
        inst.name.lower()
        for inst in _active_instrumentors
        if inst.is_instrumented
    ]


def is_instrumented(framework: str) -> bool:
    """
    Check if a specific framework is currently instrumented.
    
    Args:
        framework: Name of the framework to check.
    
    Returns:
        True if the framework is currently instrumented, False otherwise.
    
    Example:
        >>> auto_instrument(frameworks=["openai"])
        >>> is_instrumented("openai")
        True
        >>> is_instrumented("langchain")
        False
    """
    framework_lower = framework.lower()
    return any(
        inst.name.lower() == framework_lower and inst.is_instrumented
        for inst in _active_instrumentors
    )


# Convenience aliases
instrument = auto_instrument
instrument_all = auto_instrument
