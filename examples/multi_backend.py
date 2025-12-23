"""
Example: Multi-Backend Telemetry
================================

This example shows how to send telemetry to multiple backends simultaneously.
Useful for:
- Development (console) + Production (Splunk)
- A/B testing different observability platforms
- Redundancy across backends

Prerequisites:
    pip install genai-telemetry

Usage:
    python multi_backend.py
"""

from genai_telemetry import (
    setup_telemetry,
    trace_llm,
    SplunkHECExporter,
    ElasticsearchExporter,
    ConsoleExporter,
    FileExporter,
    MultiExporter,
)


def example_1_simple_multi_backend():
    """Use the simple list-based configuration."""
    print("\n" + "=" * 60)
    print("Example 1: Simple Multi-Backend Configuration")
    print("=" * 60)
    
    # Configure multiple backends using the list syntax
    setup_telemetry(
        workflow_name="multi-backend-app",
        exporter=[
            {"type": "console", "colored": True},
            {"type": "file", "path": "/tmp/traces.jsonl"},
            # Uncomment for production:
            # {"type": "splunk", "url": "https://splunk:8088", "token": "xxx"},
            # {"type": "elasticsearch", "hosts": ["http://es:9200"]},
        ]
    )
    
    @trace_llm(model_name="gpt-4o", model_provider="openai")
    def mock_chat(message: str):
        # Mock response
        class MockResponse:
            class Usage:
                prompt_tokens = 100
                completion_tokens = 50
            usage = Usage()
        return MockResponse()
    
    mock_chat("Hello!")
    print("✓ Telemetry sent to console and file")


def example_2_custom_exporters():
    """Use custom exporter instances for more control."""
    print("\n" + "=" * 60)
    print("Example 2: Custom Exporter Instances")
    print("=" * 60)
    
    # Create custom exporter instances
    console_exporter = ConsoleExporter(colored=True, verbose=False)
    file_exporter = FileExporter(file_path="/tmp/custom_traces.jsonl")
    
    # Combine them
    multi_exporter = MultiExporter([
        console_exporter,
        file_exporter,
    ])
    
    # Use the multi-exporter directly
    setup_telemetry(
        workflow_name="custom-exporters-app",
        exporter=multi_exporter
    )
    
    @trace_llm(model_name="claude-3-sonnet", model_provider="anthropic")
    def mock_anthropic_chat(message: str):
        class MockResponse:
            class Usage:
                input_tokens = 75
                output_tokens = 125
            usage = Usage()
        return MockResponse()
    
    mock_anthropic_chat("Hello from Anthropic!")
    print("✓ Telemetry sent via custom exporters")


def example_3_console_plus_file_shorthand():
    """Use the console=True and file_path shorthand."""
    print("\n" + "=" * 60)
    print("Example 3: Console + File Shorthand")
    print("=" * 60)
    
    # Quick shorthand for console + file
    setup_telemetry(
        workflow_name="shorthand-app",
        exporter="console",  # Primary exporter
        file_path="/tmp/shorthand_traces.jsonl"  # Also write to file
    )
    
    @trace_llm(model_name="gpt-4o-mini", model_provider="openai")
    def quick_test(message: str):
        class MockResponse:
            class Usage:
                prompt_tokens = 25
                completion_tokens = 10
            usage = Usage()
        return MockResponse()
    
    quick_test("Quick test!")
    print("✓ Telemetry sent via shorthand config")


if __name__ == "__main__":
    print("Multi-Backend Telemetry Examples")
    print("=" * 60)
    
    example_1_simple_multi_backend()
    example_2_custom_exporters()
    example_3_console_plus_file_shorthand()
    
    print("\n" + "=" * 60)
    print("All examples completed!")
    print("Check /tmp/traces.jsonl for file output")
    print("=" * 60)
