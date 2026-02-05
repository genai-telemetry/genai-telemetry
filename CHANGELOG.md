# Changelog
All notable changes to the genai-telemetry SDK will be documented in this file.
The format is based on Keep a Changelog,
and this project adheres to Semantic Versioning.

## Version 1.1.0 - 2026-02-05

### Added - Auto-Instrumentation (Major Feature)

**Zero-code instrumentation for popular LLM frameworks.** Simply call `auto_instrument()` and all LLM calls are automatically traced!

```python
from genai_telemetry import setup_telemetry, auto_instrument

setup_telemetry(workflow_name="my-app", exporter="splunk", ...)
auto_instrument()  # That's it! All LLM calls are now traced.
```

#### Supported Frameworks:
- **OpenAI Python SDK** - chat completions, embeddings (sync & async)
- **Anthropic Python SDK** - messages API (sync & async)
- **Google Generative AI (Gemini)** - generate_content, embeddings
- **LangChain / LangChain-Core** - LLMs, chains, agents, retrievers, tools, embeddings
- **LlamaIndex** - query engines, retrievers, LLMs, embeddings

#### New Functions:
- `auto_instrument()` - Enable automatic tracing for all installed frameworks
- `auto_instrument(frameworks=["openai", "langchain"])` - Instrument specific frameworks
- `auto_instrument(exclude=["anthropic"])` - Exclude specific frameworks
- `uninstrument()` - Remove all instrumentation
- `get_instrumented_frameworks()` - List currently instrumented frameworks
- `is_instrumented("openai")` - Check if a framework is instrumented

### New Files:
- `genai_telemetry/instrumentation/` - New instrumentation module
- `genai_telemetry/instrumentation/auto.py` - Main auto_instrument orchestrator
- `genai_telemetry/instrumentation/base.py` - BaseInstrumentor class
- `genai_telemetry/instrumentation/openai_inst.py` - OpenAI instrumentor
- `genai_telemetry/instrumentation/anthropic_inst.py` - Anthropic instrumentor
- `genai_telemetry/instrumentation/langchain_inst.py` - LangChain instrumentor
- `genai_telemetry/instrumentation/llamaindex_inst.py` - LlamaIndex instrumentor
- `genai_telemetry/instrumentation/google_inst.py` - Google AI instrumentor
- `examples/auto_instrument_example.py` - Usage examples
- `tests/test_auto_instrument.py` - Test suite (18 tests)

## Version (0.6.0 - 2026-01-21)
## Added
Adding CHANGELOG.md

Adding CONTRIBUTING.md

Adding CODE_OF_CONDUCT.md

Updating LICENSE
## Version (0.5.1 - 2026-01-20)
## Changed
Delete java directory

Delete js directory
## Version (0.5.0 - 2026-01-08)
## Added
adding java sdk

adding javascript sdk
## Changed
Improved batch processing performance for high-throughput applications
## Version (0.4.2 - 2025-12-26)
## Changed
Update Splunk app link in README
## Version 0.4.1 - 2025-12-26
## Changed
Update utils.py

Update README.md
## Version (0.4.0 - 2025-12-24)
## Added
Datadog APM exporter

AWS CloudWatch Logs exporter

Grafana Loki exporter

Prometheus Push Gateway exporter

OpenTelemetry Protocol (OTLP) exporter

Multi-exporter support for sending telemetry to multiple backends simultaneously
## Fixed
Token counting accuracy for streaming responses
## Version (0.3.0 - 2025-12-23)
## Added
Initial release of genai-telemetry SDK

Core telemetry manager and span classes

Tracing decorators for LLM operations:

@trace_llm - Trace LLM/chat completions

@trace_embedding - Trace embedding operations

@trace_retrieval - Trace vector store retrievals

@trace_tool - Trace tool/function calls

@trace_chain - Trace LLM chains/pipelines

@trace_agent - Trace autonomous agents

## Exporters:
Splunk HTTP Event Collector (HEC)

Elasticsearch/OpenSearch

Console output (for debugging)

JSON Lines file exporter

Automatic token extraction from OpenAI and Anthropic responses

Configurable batch processing

Python 3.8+ support

## Documentation

Comprehensive README with quick start guide

Exporter-specific documentation

Usage examples for all decorators
