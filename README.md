# GenAI Telemetry

[![PyPI version](https://badge.fury.io/py/genai-telemetry.svg)](https://badge.fury.io/py/genai-telemetry)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

A **Platform-agnostic observability for LLM and GenAI applications.**
Trace AI workloads and export telemetry to any backend, including Splunk, Elasticsearch, Datadog, Prometheus, OpenTelemetry, Grafana Loki, AWS CloudWatch, and more

## Features

- **Multi-Backend Support** - Send traces to 10+ observability platforms
- **Simple Decorators** - Instrument your code with minimal changes
- **Token Tracking** - Automatically capture input/output token counts
- **Batching & Async** - Efficient background flushing for high-throughput apps
- **Framework Agnostic** - Works with OpenAI, Anthropic, LangChain, LlamaIndex, etc.

## Installation

```bash
pip install genai-telemetry

# For AWS CloudWatch support
pip install genai-telemetry[aws]
```

## Quick Start

### Basic Usage with Console Output

```python
from genai_telemetry import setup_telemetry, trace_llm

# Initialize with console output (great for development)
setup_telemetry(workflow_name="my-chatbot", exporter="console")

@trace_llm(model_name="gpt-4o", model_provider="openai")
def chat(message: str):
    from openai import OpenAI
    client = OpenAI()
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": message}]
    )
    return response  # Return FULL response to capture token counts

# Use your function
result = chat("Hello, how are you?")
print(result.choices[0].message.content)
```

### With Splunk

```python
from genai_telemetry import setup_telemetry, trace_llm

setup_telemetry(
    workflow_name="my-chatbot",
    exporter="splunk",
    splunk_url="https://splunk.example.com:8088",
    splunk_token="your-hec-token",
    splunk_index="genai_traces"
)

@trace_llm(model_name="gpt-4o", model_provider="openai")
def chat(message: str):
    # Your LLM code here
    return response
```

### With Elasticsearch

```python
setup_telemetry(
    workflow_name="my-chatbot",
    exporter="elasticsearch",
    es_hosts=["https://elasticsearch:9200"],
    es_api_key="your-api-key",
    es_index="genai-traces"
)
```

### With Datadog

```python
setup_telemetry(
    workflow_name="my-chatbot",
    exporter="datadog",
    datadog_api_key="your-api-key",
    datadog_site="datadoghq.com"
)
```

### With OpenTelemetry (Jaeger, Tempo, etc.)

```python
setup_telemetry(
    workflow_name="my-chatbot",
    exporter="otlp",
    otlp_endpoint="http://localhost:4318",
    otlp_headers={"Authorization": "Bearer your-token"}
)
```

### Multiple Backends

```python
setup_telemetry(
    workflow_name="my-chatbot",
    exporter=[
        {"type": "splunk", "url": "https://splunk:8088", "token": "xxx"},
        {"type": "elasticsearch", "hosts": ["http://es:9200"]},
        {"type": "console"}
    ]
)
```

## Available Decorators

### `@trace_llm` - LLM Calls

```python
@trace_llm(model_name="gpt-4o", model_provider="openai")
def generate_response(prompt: str):
    return openai_client.chat.completions.create(...)
```

**Important:** Return the full response object to capture token counts!

### `@trace_embedding` - Embedding Calls

```python
@trace_embedding(model="text-embedding-3-small")
def get_embeddings(texts: list):
    return openai_client.embeddings.create(...)
```

### `@trace_retrieval` - Vector Store Queries

```python
@trace_retrieval(vector_store="pinecone", embedding_model="text-embedding-3-small")
def search_documents(query: str):
    return vector_store.similarity_search(query, k=5)
```

### `@trace_tool` - Tool/Function Calls

```python
@trace_tool(tool_name="web_search")
def search_web(query: str):
    return search_api.search(query)
```

### `@trace_chain` - Pipelines/Chains

```python
@trace_chain(name="rag-pipeline")
def rag_pipeline(question: str):
    docs = retrieve(question)
    return generate(question, docs)
```

### `@trace_agent` - Agent Executions

```python
@trace_agent(agent_name="research-agent", agent_type="react")
def run_agent(task: str):
    return agent.execute(task)
```

## Supported Exporters

| Exporter | Backend | Key Parameters |
|----------|---------|----------------|
| `splunk` | Splunk HEC | `splunk_url`, `splunk_token`, `splunk_index` |
| `elasticsearch` | Elasticsearch/OpenSearch | `es_hosts`, `es_api_key`, `es_index` |
| `otlp` | OpenTelemetry Collector | `otlp_endpoint`, `otlp_headers` |
| `datadog` | Datadog | `datadog_api_key`, `datadog_site` |
| `prometheus` | Prometheus Push Gateway | `prometheus_gateway` |
| `loki` | Grafana Loki | `loki_url`, `loki_tenant_id` |
| `cloudwatch` | AWS CloudWatch Logs | `cloudwatch_log_group`, `cloudwatch_region` |
| `console` | Console/stdout | `colored`, `verbose` |
| `file` | JSONL File | `file_path` |

## Auto Content Extraction

Use `extract_content=True` to automatically extract the text content while still tracking tokens:

```python
@trace_llm(model_name="gpt-4o", model_provider="openai", extract_content=True)
def chat(message: str):
    response = client.chat.completions.create(...)
    return response  # Return full response

# The decorator automatically extracts the content
answer = chat("Hello!")  # answer is now just the string content
print(answer)  # "Hello! How can I help you today?"
```

## Span Data Schema

Each span includes:

```json
{
  "trace_id": "abc123...",
  "span_id": "def456...",
  "parent_span_id": "ghi789...",
  "span_type": "LLM",
  "name": "chat",
  "workflow_name": "my-chatbot",
  "timestamp": "2024-01-15T10:30:00Z",
  "duration_ms": 1234.56,
  "status": "OK",
  "is_error": 0,
  "model_name": "gpt-4o",
  "model_provider": "openai",
  "input_tokens": 150,
  "output_tokens": 200,
  "total_tokens": 350
}
```

## Manual Span Creation

For more control, use the context manager:

```python
from genai_telemetry import get_telemetry

telemetry = get_telemetry()

with telemetry.start_span("custom-operation", span_type="TOOL") as span:
    span.set_attribute("custom_field", "custom_value")
    # Your code here
    result = do_something()
```

Or send spans directly:

```python
telemetry.send_span(
    span_type="LLM",
    name="custom-llm-call",
    duration_ms=1500,
    model_name="claude-3-opus",
    model_provider="anthropic",
    input_tokens=100,
    output_tokens=200
)
```

## Architecture

```
genai_telemetry/
├── __init__.py          # Public API exports
├── core/
│   ├── telemetry.py     # Main telemetry manager
│   ├── span.py          # Span class
│   ├── decorators.py    # @trace_* decorators
│   └── utils.py         # Token extraction helpers
└── exporters/
    ├── base.py          # BaseExporter interface
    ├── splunk.py        # Splunk HEC
    ├── elasticsearch.py # Elasticsearch
    ├── otlp.py          # OpenTelemetry
    ├── datadog.py       # Datadog
    ├── prometheus.py    # Prometheus
    ├── loki.py          # Grafana Loki
    ├── cloudwatch.py    # AWS CloudWatch
    ├── console.py       # Console output
    ├── file.py          # File output
    └── multi.py         # Multi-exporter
```

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

Apache 2.0 - see [LICENSE](LICENSE) for details.
