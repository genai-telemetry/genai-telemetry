"""
Base class for all instrumentors.
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class BaseInstrumentor(ABC):
    """Base class for framework-specific instrumentors."""
    
    _is_instrumented: bool = False
    _original_methods: Dict[str, Any] = {}
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the framework being instrumented."""
        pass
    
    @abstractmethod
    def _check_installed(self) -> bool:
        """Check if the framework is installed."""
        pass
    
    @abstractmethod
    def _instrument(self) -> None:
        """Apply instrumentation patches."""
        pass
    
    @abstractmethod
    def _uninstrument(self) -> None:
        """Remove instrumentation patches."""
        pass
    
    def instrument(self) -> bool:
        """
        Instrument the framework.
        
        Returns:
            bool: True if instrumentation was applied, False otherwise.
        """
        if self._is_instrumented:
            logger.debug(f"{self.name} is already instrumented")
            return True
        
        if not self._check_installed():
            logger.debug(f"{self.name} is not installed, skipping instrumentation")
            return False
        
        try:
            self._instrument()
            self._is_instrumented = True
            logger.info(f"Successfully instrumented {self.name}")
            return True
        except Exception as e:
            logger.warning(f"Failed to instrument {self.name}: {e}")
            return False
    
    def uninstrument(self) -> bool:
        """
        Remove instrumentation from the framework.
        
        Returns:
            bool: True if uninstrumentation was successful, False otherwise.
        """
        if not self._is_instrumented:
            logger.debug(f"{self.name} is not instrumented")
            return True
        
        try:
            self._uninstrument()
            self._is_instrumented = False
            logger.info(f"Successfully uninstrumented {self.name}")
            return True
        except Exception as e:
            logger.warning(f"Failed to uninstrument {self.name}: {e}")
            return False
    
    @property
    def is_instrumented(self) -> bool:
        """Check if the framework is currently instrumented."""
        return self._is_instrumented


def safe_import(module_name: str):
    """Safely import a module, returning None if not installed."""
    try:
        import importlib
        return importlib.import_module(module_name)
    except ImportError:
        return None


def wrap_method(obj: Any, method_name: str, wrapper_func, original_store: dict):
    """
    Safely wrap a method with a wrapper function.
    
    Args:
        obj: The object or class containing the method
        method_name: Name of the method to wrap
        wrapper_func: The wrapper function (receives original method as first arg)
        original_store: Dict to store the original method for later restoration
    """
    if not hasattr(obj, method_name):
        return False
    
    original = getattr(obj, method_name)
    key = f"{obj.__module__}.{obj.__name__ if hasattr(obj, '__name__') else type(obj).__name__}.{method_name}"
    original_store[key] = original
    
    wrapped = wrapper_func(original)
    setattr(obj, method_name, wrapped)
    return True


def unwrap_method(obj: Any, method_name: str, original_store: dict):
    """
    Restore a wrapped method to its original.
    
    Args:
        obj: The object or class containing the method
        method_name: Name of the method to restore
        original_store: Dict containing the original methods
    """
    key = f"{obj.__module__}.{obj.__name__ if hasattr(obj, '__name__') else type(obj).__name__}.{method_name}"
    if key in original_store:
        setattr(obj, method_name, original_store[key])
        del original_store[key]
        return True
    return False
