"""Tests for telemetry exporters."""

import json
import pytest
from unittest.mock import MagicMock, patch, mock_open

from genai_telemetry.exporters.base import BaseExporter
from genai_telemetry.exporters.console import ConsoleExporter
from genai_telemetry.exporters.file import FileExporter
from genai_telemetry.exporters.multi import MultiExporter
from genai_telemetry.exporters.splunk import SplunkHECExporter
from genai_telemetry.exporters.elasticsearch import ElasticsearchExporter


class TestBaseExporter:
    """Tests for base exporter interface."""
    
    def test_base_exporter_is_abstract(self):
        """Test that BaseExporter cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseExporter()
    
    def test_base_exporter_export_batch_default(self):
        """Test default export_batch implementation."""
        class TestExporter(BaseExporter):
            def __init__(self):
                self.exports = []
            
            def export(self, span_data):
                self.exports.append(span_data)
                return True
        
        exporter = TestExporter()
        spans = [{"span_type": "LLM"}, {"span_type": "TOOL"}]
        
        result = exporter.export_batch(spans)
        
        assert result is True
        assert len(exporter.exports) == 2


class TestConsoleExporter:
    """Tests for console exporter."""
    
    def test_export_basic_span(self, capsys):
        """Test basic span export to console."""
        exporter = ConsoleExporter(colored=False)
        
        span_data = {
            "span_type": "LLM",
            "name": "chat",
            "duration_ms": 150.5,
            "status": "OK",
            "model_name": "gpt-4o",
            "input_tokens": 100,
            "output_tokens": 50
        }
        
        result = exporter.export(span_data)
        
        assert result is True
        captured = capsys.readouterr()
        assert "LLM" in captured.out
        assert "chat" in captured.out
        assert "150.5" in captured.out
        assert "gpt-4o" in captured.out
    
    def test_export_colored_output(self, capsys):
        """Test colored console output."""
        exporter = ConsoleExporter(colored=True)
        
        span_data = {
            "span_type": "LLM",
            "name": "chat",
            "duration_ms": 100,
            "status": "OK",
            "model_name": "gpt-4o",
            "input_tokens": 50,
            "output_tokens": 25
        }
        
        exporter.export(span_data)
        
        captured = capsys.readouterr()
        # Check for ANSI escape codes
        assert "\033[" in captured.out
    
    def test_export_verbose_mode(self, capsys):
        """Test verbose console output."""
        exporter = ConsoleExporter(colored=False, verbose=True)
        
        span_data = {
            "span_type": "LLM",
            "name": "chat",
            "duration_ms": 100,
            "status": "OK",
            "model_name": "gpt-4o",
            "input_tokens": 50,
            "output_tokens": 25
        }
        
        exporter.export(span_data)
        
        captured = capsys.readouterr()
        # Verbose mode should include JSON
        assert "input_tokens" in captured.out
    
    def test_export_error_span(self, capsys):
        """Test error span display."""
        exporter = ConsoleExporter(colored=False)
        
        span_data = {
            "span_type": "LLM",
            "name": "chat",
            "duration_ms": 50,
            "status": "ERROR",
            "model_name": "gpt-4o",
            "input_tokens": 0,
            "output_tokens": 0
        }
        
        exporter.export(span_data)
        
        captured = capsys.readouterr()
        assert "ERROR" in captured.out


class TestFileExporter:
    """Tests for file exporter."""
    
    def test_export_writes_jsonl(self, tmp_path):
        """Test that export writes JSONL format."""
        file_path = tmp_path / "traces.jsonl"
        exporter = FileExporter(file_path=str(file_path))
        
        span_data = {
            "span_type": "LLM",
            "name": "chat",
            "duration_ms": 100
        }
        
        result = exporter.export(span_data)
        
        assert result is True
        
        with open(file_path) as f:
            line = f.readline()
            parsed = json.loads(line)
            assert parsed["span_type"] == "LLM"
            assert parsed["name"] == "chat"
    
    def test_export_multiple_spans(self, tmp_path):
        """Test multiple span exports."""
        file_path = tmp_path / "traces.jsonl"
        exporter = FileExporter(file_path=str(file_path))
        
        for i in range(3):
            exporter.export({"span_type": "LLM", "name": f"span_{i}"})
        
        with open(file_path) as f:
            lines = f.readlines()
            assert len(lines) == 3


class TestMultiExporter:
    """Tests for multi-exporter."""
    
    def test_export_to_multiple_backends(self):
        """Test exporting to multiple backends."""
        mock_exporter1 = MagicMock()
        mock_exporter1.export.return_value = True
        
        mock_exporter2 = MagicMock()
        mock_exporter2.export.return_value = True
        
        multi = MultiExporter([mock_exporter1, mock_exporter2])
        
        span_data = {"span_type": "LLM", "name": "test"}
        result = multi.export(span_data)
        
        assert result is True
        mock_exporter1.export.assert_called_once_with(span_data)
        mock_exporter2.export.assert_called_once_with(span_data)
    
    def test_export_succeeds_if_one_succeeds(self):
        """Test that export succeeds if at least one exporter succeeds."""
        mock_exporter1 = MagicMock()
        mock_exporter1.export.return_value = False
        
        mock_exporter2 = MagicMock()
        mock_exporter2.export.return_value = True
        
        multi = MultiExporter([mock_exporter1, mock_exporter2])
        
        result = multi.export({"span_type": "LLM"})
        
        assert result is True
    
    def test_start_calls_all_exporters(self):
        """Test start() calls all exporters."""
        mock_exporter1 = MagicMock()
        mock_exporter2 = MagicMock()
        
        multi = MultiExporter([mock_exporter1, mock_exporter2])
        multi.start()
        
        mock_exporter1.start.assert_called_once()
        mock_exporter2.start.assert_called_once()
    
    def test_stop_calls_all_exporters(self):
        """Test stop() calls all exporters."""
        mock_exporter1 = MagicMock()
        mock_exporter2 = MagicMock()
        
        multi = MultiExporter([mock_exporter1, mock_exporter2])
        multi.stop()
        
        mock_exporter1.stop.assert_called_once()
        mock_exporter2.stop.assert_called_once()
    
    def test_flush_calls_all_exporters(self):
        """Test flush() calls all exporters."""
        mock_exporter1 = MagicMock()
        mock_exporter2 = MagicMock()
        
        multi = MultiExporter([mock_exporter1, mock_exporter2])
        multi.flush()
        
        mock_exporter1.flush.assert_called_once()
        mock_exporter2.flush.assert_called_once()


class TestSplunkHECExporter:
    """Tests for Splunk HEC exporter."""
    
    def test_url_normalization(self):
        """Test HEC URL is normalized correctly."""
        exporter = SplunkHECExporter(
            hec_url="http://splunk:8088",
            hec_token="test-token"
        )
        
        assert exporter.hec_url.endswith("/services/collector/event")
    
    def test_url_with_trailing_slash(self):
        """Test HEC URL with trailing slash."""
        exporter = SplunkHECExporter(
            hec_url="http://splunk:8088/",
            hec_token="test-token"
        )
        
        assert exporter.hec_url.endswith("/services/collector/event")
    
    @patch('urllib.request.urlopen')
    def test_export_single_span(self, mock_urlopen):
        """Test single span export."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        exporter = SplunkHECExporter(
            hec_url="http://splunk:8088",
            hec_token="test-token",
            batch_size=1
        )
        
        result = exporter.export({"span_type": "LLM", "name": "test"})
        
        assert result is True
        mock_urlopen.assert_called_once()


class TestElasticsearchExporter:
    """Tests for Elasticsearch exporter."""
    
    def test_host_round_robin(self):
        """Test host selection rotates."""
        exporter = ElasticsearchExporter(
            hosts=["http://es1:9200", "http://es2:9200", "http://es3:9200"]
        )
        
        host1 = exporter._get_host()
        host2 = exporter._get_host()
        host3 = exporter._get_host()
        host4 = exporter._get_host()
        
        assert host1 == "http://es1:9200"
        assert host2 == "http://es2:9200"
        assert host3 == "http://es3:9200"
        assert host4 == "http://es1:9200"  # Wraps around
    
    def test_headers_with_api_key(self):
        """Test headers include API key auth."""
        exporter = ElasticsearchExporter(
            hosts=["http://localhost:9200"],
            api_key="test-api-key"
        )
        
        headers = exporter._get_headers()
        
        assert "Authorization" in headers
        assert headers["Authorization"] == "ApiKey test-api-key"
    
    def test_headers_with_basic_auth(self):
        """Test headers include basic auth."""
        exporter = ElasticsearchExporter(
            hosts=["http://localhost:9200"],
            username="elastic",
            password="password123"
        )
        
        headers = exporter._get_headers()
        
        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Basic ")
