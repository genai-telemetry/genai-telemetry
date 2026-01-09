# GenAI Telemetry - JavaScript/TypeScript SDK

[![npm version](https://badge.fury.io/js/genai-telemetry.svg)](https://www.npmjs.com/package/genai-telemetry)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

A platform-agnostic telemetry library for tracing GenAI/LLM applications in JavaScript and TypeScript. Supports multiple observability backends including Splunk, Elasticsearch, OpenTelemetry, Datadog, Prometheus, Grafana Loki, AWS CloudWatch, and more.

## Features

- 🔌 **Multi-Backend Support**: Splunk, Elasticsearch, OpenTelemetry, Datadog, Prometheus, Loki, CloudWatch
- 📊 **Automatic Token Tracking**: Captures input/output tokens from OpenAI, Anthropic, and other providers
- 🔗 **Distributed Tracing**: Full trace context propagation with parent-child span relationships
- 🎯 **Zero-Config Setup**: Simple one-line initialization
- 📝 **TypeScript First**: Full type definitions included
- 🪶 **Lightweight**: Minimal dependencies

## Installation

```bash
npm install genai-telemetry
# or
yarn add genai-telemetry
# or
pnpm add genai-telemetry
```

## Quick Start

```typescript
import { setupTelemetry, traceLLM } from 'genai-telemetry';
import OpenAI from 'openai';

// Initialize telemetry with Splunk
setupTelemetry({
  workflowName: 'my-chatbot',
  exporter: 'splunk',
  splunkUrl: 'http://splunk:8088',
  splunkToken: 'your-hec-token'
});

const client = new OpenAI();

// Wrap your LLM function for automatic tracing
const chat = traceLLM(
  async (message: string) => {
    return await client.chat.completions.create({
      model: 'gpt-4o',
      messages: [{ role: 'user', content: message }]
    });
  },
  { modelName: 'gpt-4o', modelProvider: 'openai' }
);

// Use it normally - telemetry is captured automatically!
const response = await chat('What is the capital of France?');
console.log(response.choices[0].message.content);
```

## Configuration

### Splunk

```typescript
setupTelemetry({
  workflowName: 'my-app',
  exporter: 'splunk',
  splunkUrl: 'http://splunk:8088',
  splunkToken: 'your-hec-token',
  splunkIndex: 'genai_traces'  // optional
});
```

### Elasticsearch

```typescript
setupTelemetry({
  workflowName: 'my-app',
  exporter: 'elasticsearch',
  esHosts: ['http://localhost:9200'],
  esIndex: 'genai-traces',
  esApiKey: 'your-api-key'  // or use esUsername/esPassword
});
```

### OpenTelemetry (OTLP)

```typescript
setupTelemetry({
  workflowName: 'my-app',
  exporter: 'otlp',
  otlpEndpoint: 'http://localhost:4318',
  otlpHeaders: { 'Authorization': 'Bearer token' }
});
```

### Datadog

```typescript
setupTelemetry({
  workflowName: 'my-app',
  exporter: 'datadog',
  datadogApiKey: 'your-api-key',
  datadogSite: 'datadoghq.com'
});
```

### Prometheus

```typescript
setupTelemetry({
  workflowName: 'my-app',
  exporter: 'prometheus',
  prometheusGateway: 'http://localhost:9091'
});
```

### Grafana Loki

```typescript
setupTelemetry({
  workflowName: 'my-app',
  exporter: 'loki',
  lokiUrl: 'http://localhost:3100'
});
```

### AWS CloudWatch

```typescript
setupTelemetry({
  workflowName: 'my-app',
  exporter: 'cloudwatch',
  cloudwatchLogGroup: '/genai/traces',
  cloudwatchRegion: 'us-east-1'
});
```

### Multiple Exporters

```typescript
setupTelemetry({
  workflowName: 'my-app',
  exporter: [
    { type: 'splunk', url: 'http://splunk:8088', token: 'xxx' },
    { type: 'elasticsearch', hosts: ['http://localhost:9200'] },
    { type: 'console' }
  ]
});
```

### Console (Development)

```typescript
setupTelemetry({
  workflowName: 'my-app',
  exporter: 'console'
});
```

## Tracing Functions

### traceLLM - Trace LLM Calls

```typescript
import { traceLLM } from 'genai-telemetry';

const chat = traceLLM(
  async (message: string) => {
    return await openai.chat.completions.create({
      model: 'gpt-4o',
      messages: [{ role: 'user', content: message }]
    });
  },
  { 
    modelName: 'gpt-4o', 
    modelProvider: 'openai',
    extractContent: false  // Set to true to return just the content string
  }
);
```

### traceEmbedding - Trace Embedding Calls

```typescript
import { traceEmbedding } from 'genai-telemetry';

const embed = traceEmbedding(
  async (text: string) => {
    return await openai.embeddings.create({
      model: 'text-embedding-3-small',
      input: text
    });
  },
  { model: 'text-embedding-3-small' }
);
```

### traceRetrieval - Trace Vector Search

```typescript
import { traceRetrieval } from 'genai-telemetry';

const search = traceRetrieval(
  async (query: string) => {
    return await vectorStore.similaritySearch(query, 5);
  },
  { 
    vectorStore: 'pinecone', 
    embeddingModel: 'text-embedding-3-small' 
  }
);
```

### traceTool - Trace Tool Calls

```typescript
import { traceTool } from 'genai-telemetry';

const searchWeb = traceTool(
  async (query: string) => {
    return await webSearchAPI.search(query);
  },
  { toolName: 'web_search' }
);
```

### traceChain - Trace Pipelines

```typescript
import { traceChain } from 'genai-telemetry';

const ragPipeline = traceChain(
  async (question: string) => {
    const docs = await search(question);
    const context = docs.map(d => d.content).join('\n');
    return await chat(`Context: ${context}\n\nQuestion: ${question}`);
  },
  { name: 'rag-pipeline' }
);
```

### traceAgent - Trace Agent Calls

```typescript
import { traceAgent } from 'genai-telemetry';

const agent = traceAgent(
  async (task: string) => {
    // Agent logic
    return await agentExecutor.run(task);
  },
  { agentName: 'research-agent', agentType: 'react' }
);
```

## Class Decorators (TypeScript)

For class-based code, use decorators:

```typescript
import { TraceLLM, TraceRetrieval } from 'genai-telemetry';

class ChatService {
  private client = new OpenAI();

  @TraceLLM({ modelName: 'gpt-4o', modelProvider: 'openai' })
  async chat(message: string) {
    return await this.client.chat.completions.create({
      model: 'gpt-4o',
      messages: [{ role: 'user', content: message }]
    });
  }

  @TraceRetrieval({ vectorStore: 'pinecone' })
  async search(query: string) {
    return await this.vectorStore.query(query);
  }
}
```

## Manual Span Management

For more control, use the telemetry instance directly:

```typescript
import { getTelemetry } from 'genai-telemetry';

const telemetry = getTelemetry();

// Send a span directly
await telemetry.sendSpan('LLM', 'custom-llm-call', {
  modelName: 'gpt-4o',
  modelProvider: 'openai',
  durationMs: 150,
  inputTokens: 100,
  outputTokens: 50
});

// Use context manager style
await telemetry.withSpan('my-operation', 'TOOL', async (span) => {
  span.setAttribute('custom_field', 'value');
  // Your code here
  return result;
});
```

## Span Data Schema

Each span includes:

| Field | Type | Description |
|-------|------|-------------|
| `trace_id` | string | Unique trace identifier |
| `span_id` | string | Unique span identifier |
| `parent_span_id` | string? | Parent span for nesting |
| `span_type` | string | LLM, EMBEDDING, RETRIEVER, TOOL, CHAIN, AGENT |
| `name` | string | Operation name |
| `workflow_name` | string | Application/workflow name |
| `timestamp` | string | ISO 8601 timestamp |
| `duration_ms` | number | Duration in milliseconds |
| `status` | string | OK or ERROR |
| `is_error` | number | 0 or 1 |
| `model_name` | string? | LLM model name |
| `model_provider` | string? | Provider (openai, anthropic, etc.) |
| `input_tokens` | number? | Input token count |
| `output_tokens` | number? | Output token count |
| `total_tokens` | number? | Total token count |

## Examples

See the [examples](./examples) directory for complete examples:

- [Basic OpenAI](./examples/basic_openai.ts)
- [RAG Pipeline](./examples/rag_pipeline.ts)
- [Multi-Backend](./examples/multi_backend.ts)

## License

Apache-2.0 - See [LICENSE](../LICENSE) for details.

## Author

Kamal Singh Bisht

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for contribution guidelines.
