"""
Console exporter for debugging and development.
"""

import json
from typing import Any, Dict

from genai_telemetry.exporters.base import BaseExporter


class ConsoleExporter(BaseExporter):
    """Prints spans to console."""
    
    def __init__(self, colored: bool = True, verbose: bool = False):
        """
        Initialize console exporter.
        
        Args:
            colored: Whether to use ANSI colors in output
            verbose: Whether to print full span data as JSON
        """
        self.colored = colored
        self.verbose = verbose
    
    def export(self, span_data: Dict[str, Any]) -> bool:
        """Print span to console."""
        span_type = span_data.get('span_type', 'UNKNOWN')
        name = span_data.get('name', 'unknown')
        duration = span_data.get('duration_ms', 0)
        status = span_data.get('status', 'OK')
        model = span_data.get('model_name', '')
        input_tokens = span_data.get('input_tokens', 0)
        output_tokens = span_data.get('output_tokens', 0)
        total_tokens = input_tokens + output_tokens
        
        if self.colored:
            # ANSI colors
            colors = {
                "LLM": "\033[94m",       # Blue
                "EMBEDDING": "\033[95m",  # Magenta
                "RETRIEVER": "\033[96m",  # Cyan
                "TOOL": "\033[93m",       # Yellow
                "CHAIN": "\033[92m",      # Green
                "AGENT": "\033[91m",      # Red
                "ERROR": "\033[91m",      # Red
            }
            reset = "\033[0m"
            color = colors.get(span_type, "\033[0m")
            status_color = "\033[91m" if status == "ERROR" else "\033[92m"
            
            print(f"{color}[{span_type:12}]{reset} {name:30} | {duration:>8.1f}ms | {status_color}{status:5}{reset} | {model} | in:{input_tokens} out:{output_tokens} total:{total_tokens}")
        else:
            print(f"[{span_type:12}] {name:30} | {duration:>8.1f}ms | {status:5} | {model} | in:{input_tokens} out:{output_tokens} total:{total_tokens}")
        
        if self.verbose:
            print(f"    {json.dumps(span_data, indent=2)}")
        
        return True
