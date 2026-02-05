# GenAI Telemetry

[![PyPI version](https://badge.fury.io/py/genai-telemetry.svg)](https://badge.fury.io/py/genai-telemetry)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Downloads](https://pepy.tech/badge/genai-telemetry)](https://pepy.tech/project/genai-telemetry)

**The most comprehensive open-source observability SDK for GenAI/LLM applications.**

Trace prompts, completions, token usage, latency, errors, and costs across OpenAI, Anthropic, LangChain, LlamaIndex, and more. Export to 10+ backends including Splunk, Elasticsearch, Datadog, and Prometheus.

## ✨ What's New in v1.1.0: Zero-Code Auto-Instrumentation

**No more decorators on every function!** Just call `auto_instrument()` and all your LLM calls are automatically traced:

```python
from genai_telemetry import setup_telemetry, auto_instrument

setup_telemetry(workflow_name="my-app", exporter="splunk", splunk_url="...", splunk_token="...")
auto_instrument()  # ← That's it!

# All LLM calls are now automatically traced
from openai import OpenAI
client = OpenAI()
response = client.chat.completions.create(model="gpt-4o", messages=[...])  # ✓ Traced!
```

## 🚀 Quick Start

### Installation

```bash
pip install genai-telemetry
```

### Option 1: Auto-Instrumentation (Recommended)

The fastest way to get started — **zero code changes** to your existing LLM code:

```python
from genai_telemetry import setup_telemetry, auto_instrument

# 1. Setup telemetry (pick your backend)
setup_telemetry(
    workflow_name="my-chatbot",
    exporter="splunk",  # or "elasticsearch", "datadog", "console", etc.
    splunk_url="https://splunk.example.com:8088",
    splunk_token="your-hec-token",
)

# 2. Enable auto-instrumentation
auto_instrument()

# 3. Use your LLM libraries normally — they're now traced!
from openai import OpenAI
client = OpenAI()
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "What is observability?"}]
)
# ↑ Automatically captures: latency, tokens, cost, errors, model info
```

### Option 2: Decorator-Based (Fine-Grained Control)

For explicit control over what gets traced:

```python
from genai_telemetry import setup_telemetry, trace_llm

setup_telemetry(workflow_name="my-chatbot", exporter="console")

@trace_llm(model_name="gpt-4o", model_provider="openai")
def chat(message: str):
    from openai import OpenAI
    client = OpenAI()
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": message}]
    )
    return response  # Return full response to capture token counts

result = chat("Hello!")
```

## 🔧 Supported Frameworks (Auto-Instrumentation)

| Framework | What's Traced | Status |
|-----------|--------------|--------|
| **OpenAI** | Chat completions, embeddings (sync + async) | ✅ Supported |
| **Anthropic** | Messages API (sync + async) | ✅ Supported |
| **Google AI (Gemini)** | generate_content, embeddings | ✅ Supported |
| **LangChain** | LLMs, chains, agents, retrievers, tools, embeddings | ✅ Supported |
| **LlamaIndex** | Query engines, retrievers, LLMs, embeddings | ✅ Supported |
| **CrewAI** | Agents, tasks, crews | 🔜 Coming Soon |
| **AutoGen** | Agents, conversations | 🔜 Coming Soon |
| **Haystack** | Pipelines, components | 🔜 Coming Soon |

### Auto-Instrumentation API

```python
from genai_telemetry import (
    auto_instrument,
    uninstrument,
    get_instrumented_frameworks,
    is_instrumented,
)

# Instrument all available frameworks
auto_instrument()

# Instrument specific frameworks only
auto_instrument(frameworks=["openai", "langchain"])

# Exclude specific frameworks
auto_instrument(exclude=["anthropic"])

# Check what's instrumented
print(get_instrumented_frameworks())  # ['openai', 'langchain', 'llamaindex']
print(is_instrumented("openai"))      # True

# Remove instrumentation
uninstrument()                        # Remove all
uninstrument(frameworks=["openai"])   # Remove specific
```

## 📊 Supported Backends

Export telemetry to **10+ observability platforms**:

| Exporter | Backend | Key Parameters |
|----------|---------|----------------|
| `splunk` | Splunk HEC | `splunk_url`, `splunk_token`, `splunk_index` |
| `elasticsearch` | Elasticsearch/OpenSearch | `es_hosts`, `es_api_key`, `es_index` |
| `otlp` | OpenTelemetry Collector | `otlp_endpoint`, `otlp_headers` |
| `datadog` | Datadog APM | `datadog_api_key`, `datadog_site` |
| `prometheus` | Prometheus Push Gateway | `prometheus_gateway` |
| `loki` | Grafana Loki | `loki_url`, `loki_tenant_id` |
| `cloudwatch` | AWS CloudWatch Logs | `cloudwatch_log_group`, `cloudwatch_region` |
| `console` | Console/stdout | `colored`, `verbose` |
| `file` | JSONL File | `file_path` |

### Backend Examples

<details>
<summary><b>Splunk</b></summary>

```python
setup_telemetry(
    workflow_name="my-chatbot",
    exporter="splunk",
    splunk_url="https://splunk.example.com:8088",
    splunk_token="your-hec-token",
    splunk_index="genai_traces"
)
```
</details>

<details>
<summary><b>Elasticsearch</b></summary>

```python
setup_telemetry(
    workflow_name="my-chatbot",
    exporter="elasticsearch",
    es_hosts=["https://elasticsearch:9200"],
    es_api_key="your-api-key",
    es_index="genai-traces"
)
```
</details>

<details>
<summary><b>Datadog</b></summary>

```python
setup_telemetry(
    workflow_name="my-chatbot",
    exporter="datadog",
    datadog_api_key="your-api-key",
    datadog_site="datadoghq.com"
)
```
</details>

<details>
<summary><b>OpenTelemetry (Jaeger, Tempo, etc.)</b></summary>

```python
setup_telemetry(
    workflow_name="my-chatbot",
    exporter="otlp",
    otlp_endpoint="http://localhost:4318",
    otlp_headers={"Authorization": "Bearer your-token"}
)
```
</details>

<details>
<summary><b>Multiple Backends</b></summary>

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
</details>

<details>
<summary><b>Console (Development)</b></summary>

```python
setup_telemetry(
    workflow_name="my-chatbot",
    exporter="console"
)
```
</details>

## 🏷️ Available Decorators

For fine-grained control, use decorators on specific functions:

### `@trace_llm` — LLM Completions

```python
@trace_llm(model_name="gpt-4o", model_provider="openai")
def generate_response(prompt: str):
    return client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
```

### `@trace_embedding` — Embedding Calls

```python
@trace_embedding(model="text-embedding-3-small")
def get_embeddings(texts: list):
    return client.embeddings.create(input=texts, model="text-embedding-3-small")
```

### `@trace_retrieval` — Vector Store Queries

```python
@trace_retrieval(vector_store="pinecone", embedding_model="text-embedding-3-small")
def search_documents(query: str):
    return vector_store.similarity_search(query, k=5)
```

### `@trace_tool` — Tool/Function Calls

```python
@trace_tool(tool_name="web_search")
def search_web(query: str):
    return search_api.search(query)
```

### `@trace_chain` — Pipelines/Chains

```python
@trace_chain(name="rag-pipeline")
def rag_pipeline(question: str):
    docs = retrieve(question)
    return generate(question, docs)
```

### `@trace_agent` — Agent Executions

```python
@trace_agent(agent_name="research-agent", agent_type="react")
def run_agent(task: str):
    return agent.execute(task)
```

## 📈 What Gets Captured

Every trace includes:

```json
{
  "trace_id": "abc123...",
  "span_id": "def456...",
  "parent_span_id": "ghi789...",
  "span_type": "LLM",
  "name": "openai.chat.completions.create",
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

## 🖥️ Production Use: Splunk App

genai-telemetry powers the **[GenAI Observability for Splunk](https://splunkbase.splunk.com/app/8308)** app on Splunkbase — a production-grade monitoring solution for GenAI workloads with:

- 📊 7 pre-built dashboards (Overview, LLM Performance, RAG Analytics, Cost Management, etc.)
- 🔍 Trace Explorer for debugging individual requests
- 💰 Real-time cost tracking and optimization recommendations
- ⚠️ Pre-built alerts for errors, latency spikes, and cost anomalies

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Your Application                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   OpenAI    │  │  Anthropic  │  │  LangChain  │  ...        │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘             │
│         │                │                │                     │
│         └────────────────┼────────────────┘                     │
│                          ▼                                      │
│              ┌───────────────────────┐                          │
│              │   genai-telemetry     │                          │
│              │   auto_instrument()   │                          │
│              └───────────┬───────────┘                          │
└──────────────────────────┼──────────────────────────────────────┘
                           │
                           ▼
        ┌──────────────────────────────────────┐
        │         Multi-Backend Export         │
        └──────────────────────────────────────┘
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
    ┌──────────┐    ┌──────────┐    ┌──────────┐
    │  Splunk  │    │ Elastic  │    │ Datadog  │  ...
    └──────────┘    └──────────┘    └──────────┘
```

## 🔧 Advanced Usage

### Manual Span Creation

For custom operations:

```python
from genai_telemetry import get_telemetry

telemetry = get_telemetry()

with telemetry.start_span("custom-operation", span_type="TOOL") as span:
    span.set_attribute("custom_field", "custom_value")
    result = do_something()
```

### Direct Span Submission

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

### Auto Content Extraction

Extract text content while still tracking tokens:

```python
@trace_llm(model_name="gpt-4o", model_provider="openai", extract_content=True)
def chat(message: str):
    response = client.chat.completions.create(...)
    return response

answer = chat("Hello!")  # Returns just the string content
print(answer)  # "Hello! How can I help you today?"
```

## 🆚 Why genai-telemetry?

| Feature | genai-telemetry | LangSmith | Langfuse | Phoenix |
|---------|-----------------|-----------|----------|---------|
| Open Source | ✅ Apache 2.0 | ❌ Proprietary | ✅ MIT | ✅ BSD |
| Multi-Backend (9+) | ✅ | ❌ | ❌ | ❌ |
| Splunk Native | ✅ | ❌ | ❌ | ❌ |
| Auto-Instrumentation | ✅ | ✅ | ✅ | ✅ |
| Self-Hosted | ✅ | Enterprise only | ✅ | ✅ |
| Vendor Neutral | ✅ | ❌ LangChain-focused | ✅ | ✅ |

## 📚 Examples

See the [`examples/`](examples/) directory for complete working examples:

- [`auto_instrument_example.py`](examples/auto_instrument_example.py) — Zero-code instrumentation
- [`basic_openai.py`](examples/basic_openai.py) — Basic OpenAI tracing
- [`rag_pipeline.py`](examples/rag_pipeline.py) — RAG pipeline with retrieval + generation
- [`multi_backend.py`](examples/multi_backend.py) — Sending to multiple backends

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

Apache 2.0 — see [LICENSE](LICENSE) for details.

## 🔗 Links

- **PyPI**: [pypi.org/project/genai-telemetry](https://pypi.org/project/genai-telemetry/)
- **Splunk App**: [splunkbase.splunk.com/app/8308](https://splunkbase.splunk.com/app/8308)
- **GitHub**: [github.com/kamalsinghbisht/genai-telemetry](https://github.com/kamalsinghbisht/genai-telemetry)
- **Changelog**: [CHANGELOG.md](CHANGELOG.md)

---

**Made with ❤️ by [Kamal Singh Bisht](https://github.com/kamalsinghbisht)**

*IEEE Senior Member | IETE Fellow | Principal Application Engineer*
