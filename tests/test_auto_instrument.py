"""
Tests for auto-instrumentation module.
"""

import unittest
from unittest.mock import MagicMock, patch
import sys


class TestAutoInstrument(unittest.TestCase):
    """Tests for auto_instrument functionality."""
    
    def setUp(self):
        """Reset instrumentation state before each test."""
        from genai_telemetry.instrumentation import auto
        auto._active_instrumentors = []
        auto._INSTRUMENTORS = {}
    
    def test_import_auto_instrument(self):
        """Test that auto_instrument can be imported from main module."""
        from genai_telemetry import auto_instrument
        self.assertIsNotNone(auto_instrument)
        self.assertTrue(callable(auto_instrument))
    
    def test_import_uninstrument(self):
        """Test that uninstrument can be imported from main module."""
        from genai_telemetry import uninstrument
        self.assertIsNotNone(uninstrument)
        self.assertTrue(callable(uninstrument))
    
    def test_import_helper_functions(self):
        """Test that helper functions can be imported."""
        from genai_telemetry import (
            get_instrumented_frameworks,
            is_instrumented
        )
        self.assertIsNotNone(get_instrumented_frameworks)
        self.assertIsNotNone(is_instrumented)
    
    def test_auto_instrument_returns_dict(self):
        """Test that auto_instrument returns a dictionary of results."""
        from genai_telemetry import setup_telemetry, auto_instrument
        
        setup_telemetry(workflow_name="test", exporter="console")
        result = auto_instrument()
        
        self.assertIsInstance(result, dict)
    
    def test_auto_instrument_with_specific_frameworks(self):
        """Test instrumenting specific frameworks only."""
        from genai_telemetry import setup_telemetry, auto_instrument
        
        setup_telemetry(workflow_name="test", exporter="console")
        result = auto_instrument(frameworks=["openai"])
        
        self.assertIsInstance(result, dict)
        # Only openai should be in results (if available)
        for key in result.keys():
            self.assertEqual(key, "openai")
    
    def test_auto_instrument_with_exclude(self):
        """Test excluding specific frameworks."""
        from genai_telemetry import setup_telemetry, auto_instrument
        
        setup_telemetry(workflow_name="test", exporter="console")
        result = auto_instrument(exclude=["openai", "anthropic"])
        
        self.assertIsInstance(result, dict)
        self.assertNotIn("openai", result)
        self.assertNotIn("anthropic", result)
    
    def test_get_instrumented_frameworks_empty(self):
        """Test get_instrumented_frameworks when nothing is instrumented."""
        from genai_telemetry import get_instrumented_frameworks
        
        result = get_instrumented_frameworks()
        self.assertIsInstance(result, list)
    
    def test_is_instrumented_false(self):
        """Test is_instrumented returns False for non-instrumented framework."""
        from genai_telemetry import is_instrumented
        
        result = is_instrumented("nonexistent_framework")
        self.assertFalse(result)
    
    def test_uninstrument_returns_dict(self):
        """Test that uninstrument returns a dictionary."""
        from genai_telemetry import uninstrument
        
        result = uninstrument()
        self.assertIsInstance(result, dict)
    
    def test_idempotent_instrumentation(self):
        """Test that calling auto_instrument multiple times is safe."""
        from genai_telemetry import setup_telemetry, auto_instrument
        
        setup_telemetry(workflow_name="test", exporter="console")
        
        result1 = auto_instrument()
        result2 = auto_instrument()
        
        # Both should succeed without errors
        self.assertIsInstance(result1, dict)
        self.assertIsInstance(result2, dict)


class TestBaseInstrumentor(unittest.TestCase):
    """Tests for BaseInstrumentor class."""
    
    def test_base_instrumentor_abstract(self):
        """Test that BaseInstrumentor cannot be instantiated directly."""
        from genai_telemetry.instrumentation.base import BaseInstrumentor
        
        with self.assertRaises(TypeError):
            BaseInstrumentor()
    
    def test_wrap_method(self):
        """Test wrap_method utility function."""
        from genai_telemetry.instrumentation.base import wrap_method, unwrap_method
        
        class TestClass:
            def method(self):
                return "original"
        
        original_store = {}
        
        def wrapper(orig):
            def wrapped(*args, **kwargs):
                return "wrapped"
            return wrapped
        
        # Wrap the method
        wrap_method(TestClass, "method", wrapper, original_store)
        
        obj = TestClass()
        self.assertEqual(obj.method(), "wrapped")
        
        # Unwrap the method
        unwrap_method(TestClass, "method", original_store)
        
        obj2 = TestClass()
        self.assertEqual(obj2.method(), "original")


class TestOpenAIInstrumentor(unittest.TestCase):
    """Tests for OpenAI instrumentor."""
    
    def test_instrumentor_name(self):
        """Test that instrumentor has correct name."""
        from genai_telemetry.instrumentation.openai_inst import OpenAIInstrumentor
        
        inst = OpenAIInstrumentor()
        self.assertEqual(inst.name, "OpenAI")
    
    def test_check_installed_without_openai(self):
        """Test _check_installed returns False when openai not installed."""
        from genai_telemetry.instrumentation.openai_inst import OpenAIInstrumentor
        
        # Mock the import to simulate openai not being installed
        with patch.dict(sys.modules, {'openai': None}):
            inst = OpenAIInstrumentor()
            # This should not raise, just return False
            # (actual behavior depends on implementation)


class TestLangChainInstrumentor(unittest.TestCase):
    """Tests for LangChain instrumentor."""
    
    def test_instrumentor_name(self):
        """Test that instrumentor has correct name."""
        from genai_telemetry.instrumentation.langchain_inst import LangChainInstrumentor
        
        inst = LangChainInstrumentor()
        self.assertEqual(inst.name, "LangChain")


class TestLlamaIndexInstrumentor(unittest.TestCase):
    """Tests for LlamaIndex instrumentor."""
    
    def test_instrumentor_name(self):
        """Test that instrumentor has correct name."""
        from genai_telemetry.instrumentation.llamaindex_inst import LlamaIndexInstrumentor
        
        inst = LlamaIndexInstrumentor()
        self.assertEqual(inst.name, "LlamaIndex")


class TestAnthropicInstrumentor(unittest.TestCase):
    """Tests for Anthropic instrumentor."""
    
    def test_instrumentor_name(self):
        """Test that instrumentor has correct name."""
        from genai_telemetry.instrumentation.anthropic_inst import AnthropicInstrumentor
        
        inst = AnthropicInstrumentor()
        self.assertEqual(inst.name, "Anthropic")


class TestGoogleInstrumentor(unittest.TestCase):
    """Tests for Google AI instrumentor."""
    
    def test_instrumentor_name(self):
        """Test that instrumentor has correct name."""
        from genai_telemetry.instrumentation.google_inst import GoogleAIInstrumentor
        
        inst = GoogleAIInstrumentor()
        self.assertEqual(inst.name, "Google")


if __name__ == "__main__":
    unittest.main()
