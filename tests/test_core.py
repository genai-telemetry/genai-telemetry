"""Tests for core telemetry functionality."""

import pytest
import time
from unittest.mock import MagicMock, patch

from genai_telemetry import (
    setup_telemetry,
    get_telemetry,
    trace_llm,
    trace_embedding,
    trace_retrieval,
    trace_tool,
    trace_chain,
    trace_agent,
    Span,
    ConsoleExporter,
)
from genai_telemetry.core.utils import (
    extract_tokens_from_response,
    extract_content_from_response,
)


class TestTokenExtraction:
    """Tests for token extraction utilities."""
    
    def test_extract_tokens_openai_response(self):
        """Test token extraction from OpenAI-style response."""
        # Mock OpenAI response
        response = MagicMock()
        response.usage.prompt_tokens = 100
        response.usage.completion_tokens = 50
        
        input_tokens, output_tokens = extract_tokens_from_response(response)
        
        assert input_tokens == 100
        assert output_tokens == 50
    
    def test_extract_tokens_anthropic_response(self):
        """Test token extraction from Anthropic-style response."""
        response = MagicMock()
        # Set up Anthropic-style usage (no prompt_tokens attribute)
        response.usage = MagicMock(spec=['input_tokens', 'output_tokens'])
        response.usage.input_tokens = 200
        response.usage.output_tokens = 100
        
        input_tokens, output_tokens = extract_tokens_from_response(response)
        
        assert input_tokens == 200
        assert output_tokens == 100
    
    def test_extract_tokens_dict_openai_style(self):
        """Test token extraction from dict response (OpenAI style)."""
        response = {
            "usage": {
                "prompt_tokens": 150,
                "completion_tokens": 75
            }
        }
        
        input_tokens, output_tokens = extract_tokens_from_response(response)
        
        assert input_tokens == 150
        assert output_tokens == 75
    
    def test_extract_tokens_dict_anthropic_style(self):
        """Test token extraction from dict response (Anthropic style)."""
        response = {
            "usage": {
                "input_tokens": 180,
                "output_tokens": 90
            }
        }
        
        input_tokens, output_tokens = extract_tokens_from_response(response)
        
        assert input_tokens == 180
        assert output_tokens == 90
    
    def test_extract_tokens_no_usage(self):
        """Test token extraction with no usage data."""
        response = {"content": "Hello"}
        
        input_tokens, output_tokens = extract_tokens_from_response(response)
        
        assert input_tokens == 0
        assert output_tokens == 0
    
    def test_extract_tokens_string_response(self):
        """Test token extraction from string response."""
        input_tokens, output_tokens = extract_tokens_from_response("Hello world")
        
        assert input_tokens == 0
        assert output_tokens == 0


class TestContentExtraction:
    """Tests for content extraction utilities."""
    
    def test_extract_content_string(self):
        """Test that string input is returned as-is."""
        content = extract_content_from_response("Hello world")
        assert content == "Hello world"
    
    def test_extract_content_openai_response(self):
        """Test content extraction from OpenAI response."""
        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message.content = "Generated text"
        
        content = extract_content_from_response(response)
        
        assert content == "Generated text"
    
    def test_extract_content_dict_openai_style(self):
        """Test content extraction from dict (OpenAI style)."""
        response = {
            "choices": [
                {"message": {"content": "Response content"}}
            ]
        }
        
        content = extract_content_from_response(response)
        
        assert content == "Response content"


class TestSpan:
    """Tests for Span class."""
    
    def test_span_creation(self):
        """Test basic span creation."""
        span = Span(
            trace_id="trace123",
            span_id="span456",
            name="test_span",
            span_type="LLM",
            workflow_name="test_workflow"
        )
        
        assert span.trace_id == "trace123"
        assert span.span_id == "span456"
        assert span.name == "test_span"
        assert span.span_type == "LLM"
        assert span.status == "OK"
        assert span.is_error == 0
    
    def test_span_with_llm_fields(self):
        """Test span with LLM-specific fields."""
        span = Span(
            trace_id="trace123",
            span_id="span456",
            name="llm_call",
            span_type="LLM",
            model_name="gpt-4o",
            model_provider="openai",
            input_tokens=100,
            output_tokens=50
        )
        
        assert span.model_name == "gpt-4o"
        assert span.model_provider == "openai"
        assert span.input_tokens == 100
        assert span.output_tokens == 50
    
    def test_span_set_error(self):
        """Test setting error on span."""
        span = Span(
            trace_id="trace123",
            span_id="span456",
            name="error_span",
            span_type="LLM"
        )
        
        error = ValueError("Test error")
        span.set_error(error)
        
        assert span.status == "ERROR"
        assert span.is_error == 1
        assert span.error_message == "Test error"
        assert span.error_type == "ValueError"
    
    def test_span_finish(self):
        """Test span finish."""
        span = Span(
            trace_id="trace123",
            span_id="span456",
            name="timed_span",
            span_type="LLM"
        )
        
        time.sleep(0.01)  # Small delay
        span.finish()
        
        assert span.duration_ms is not None
        assert span.duration_ms > 0
        assert span.end_time is not None
    
    def test_span_to_dict(self):
        """Test span serialization to dict."""
        span = Span(
            trace_id="trace123",
            span_id="span456",
            name="test_span",
            span_type="LLM",
            workflow_name="test_workflow",
            model_name="gpt-4o",
            input_tokens=100,
            output_tokens=50
        )
        span.finish()
        
        data = span.to_dict()
        
        assert data["trace_id"] == "trace123"
        assert data["span_id"] == "span456"
        assert data["name"] == "test_span"
        assert data["span_type"] == "LLM"
        assert data["status"] == "OK"
        assert "timestamp" in data
        assert "duration_ms" in data


class TestConsoleExporter:
    """Tests for console exporter."""
    
    def test_console_export(self, capsys):
        """Test console exporter outputs span data."""
        exporter = ConsoleExporter(colored=False)
        
        span_data = {
            "span_type": "LLM",
            "name": "test_call",
            "duration_ms": 100.5,
            "status": "OK",
            "model_name": "gpt-4o",
            "input_tokens": 50,
            "output_tokens": 25
        }
        
        result = exporter.export(span_data)
        
        assert result is True
        
        captured = capsys.readouterr()
        assert "LLM" in captured.out
        assert "test_call" in captured.out
        assert "100.5" in captured.out


class TestSetupTelemetry:
    """Tests for telemetry setup."""
    
    def test_setup_console_exporter(self):
        """Test setup with console exporter."""
        telemetry = setup_telemetry(
            workflow_name="test_app",
            exporter="console"
        )
        
        assert telemetry is not None
        assert telemetry.workflow_name == "test_app"
    
    def test_setup_invalid_exporter_raises(self):
        """Test that invalid exporter raises ValueError."""
        with pytest.raises(ValueError):
            setup_telemetry(
                workflow_name="test_app",
                exporter="invalid_exporter"
            )
    
    def test_get_telemetry_after_setup(self):
        """Test getting telemetry instance after setup."""
        setup_telemetry(workflow_name="test_app", exporter="console")
        
        telemetry = get_telemetry()
        
        assert telemetry is not None
        assert telemetry.workflow_name == "test_app"


class TestDecorators:
    """Tests for trace decorators."""
    
    def test_trace_llm_decorator(self, capsys):
        """Test @trace_llm decorator."""
        setup_telemetry(workflow_name="test_app", exporter="console")
        
        @trace_llm(model_name="gpt-4o", model_provider="openai")
        def mock_llm_call(message: str):
            return {"content": message}
        
        result = mock_llm_call("Hello")
        
        assert result == {"content": "Hello"}
        
        captured = capsys.readouterr()
        assert "LLM" in captured.out
        assert "mock_llm_call" in captured.out
    
    def test_trace_llm_with_error(self, capsys):
        """Test @trace_llm decorator with error."""
        setup_telemetry(workflow_name="test_app", exporter="console")
        
        @trace_llm(model_name="gpt-4o", model_provider="openai")
        def failing_llm_call(message: str):
            raise ValueError("Test error")
        
        with pytest.raises(ValueError):
            failing_llm_call("Hello")
        
        captured = capsys.readouterr()
        assert "ERROR" in captured.out
    
    def test_trace_tool_decorator(self, capsys):
        """Test @trace_tool decorator."""
        setup_telemetry(workflow_name="test_app", exporter="console")
        
        @trace_tool(tool_name="calculator")
        def calculate(a: int, b: int):
            return a + b
        
        result = calculate(2, 3)
        
        assert result == 5
        
        captured = capsys.readouterr()
        assert "TOOL" in captured.out
    
    def test_trace_embedding_decorator(self, capsys):
        """Test @trace_embedding decorator."""
        setup_telemetry(workflow_name="test_app", exporter="console")
        
        @trace_embedding(model="text-embedding-3-small")
        def get_embedding(text: str):
            return [0.1, 0.2, 0.3]
        
        result = get_embedding("Hello")
        
        assert result == [0.1, 0.2, 0.3]
        
        captured = capsys.readouterr()
        assert "EMBEDDING" in captured.out
    
    def test_trace_retrieval_decorator(self, capsys):
        """Test @trace_retrieval decorator."""
        setup_telemetry(workflow_name="test_app", exporter="console")
        
        @trace_retrieval(vector_store="pinecone")
        def search_docs(query: str):
            return ["doc1", "doc2", "doc3"]
        
        result = search_docs("query")
        
        assert len(result) == 3
        
        captured = capsys.readouterr()
        assert "RETRIEVER" in captured.out
