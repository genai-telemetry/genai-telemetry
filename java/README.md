# GenAI Telemetry - Java SDK

[![Maven Central](https://img.shields.io/maven-central/v/io.github.genai-telemetry/genai-telemetry.svg)](https://search.maven.org/artifact/io.github.genai-telemetry/genai-telemetry)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

A platform-agnostic telemetry library for tracing GenAI/LLM applications in Java. Supports multiple observability backends including Splunk, Elasticsearch, OpenTelemetry, Datadog, and more.

## Features

- 🔌 **Multi-Backend Support**: Splunk, Elasticsearch, OpenTelemetry, Datadog, and more
- 📊 **Automatic Token Tracking**: Captures input/output tokens from LLM responses
- 🔗 **Distributed Tracing**: Full trace context propagation with parent-child span relationships
- 🎯 **Simple API**: Fluent builder pattern and functional interfaces
- ☕ **Java 11+**: Modern Java with CompletableFuture support
- 🧵 **Thread-Safe**: ThreadLocal context management for concurrent applications

## Installation

### Maven

```xml
<dependency>
    <groupId>io.github.genai-telemetry</groupId>
    <artifactId>genai-telemetry</artifactId>
    <version>1.0.3</version>
</dependency>
```

### Gradle

```groovy
implementation 'io.github.genai-telemetry:genai-telemetry:1.0.3'
```

## Quick Start

```java
import io.github.genaitelemetry.core.GenAITelemetry;
import io.github.genaitelemetry.exporters.SplunkHECExporter;

// Initialize telemetry
GenAITelemetry telemetry = GenAITelemetry.builder()
    .workflowName("my-chatbot")
    .exporter(SplunkHECExporter.builder()
        .hecUrl("http://splunk:8088")
        .hecToken("your-token")
        .build())
    .build();

telemetry.start();

// Trace an LLM call
ChatResponse response = telemetry.traceLLM(
    "chat",           // operation name
    "gpt-4o",         // model name
    "openai",         // provider
    () -> {
        // Your LLM call here
        return openAIClient.chat(message);
    }
);

// Clean up
telemetry.stop();
```

## Configuration

### Splunk HEC

```java
SplunkHECExporter exporter = SplunkHECExporter.builder()
    .hecUrl("http://splunk:8088")
    .hecToken("your-token")
    .index("genai_traces")
    .sourcetype("genai:trace")
    .batchSize(10)
    .flushIntervalMs(5000)
    .build();
```

### Elasticsearch

```java
ElasticsearchExporter exporter = ElasticsearchExporter.builder()
    .hosts("http://localhost:9200")
    .index("genai-traces")
    .apiKey("your-api-key")  // or use username/password
    .batchSize(10)
    .build();
```

### OpenTelemetry (OTLP)

```java
OTLPExporter exporter = OTLPExporter.builder()
    .endpoint("http://localhost:4318")
    .serviceName("my-service")
    .header("Authorization", "Bearer token")
    .batchSize(10)
    .build();
```

### Datadog

```java
DatadogExporter exporter = DatadogExporter.builder()
    .apiKey("your-api-key")
    .site("datadoghq.com")
    .serviceName("my-service")
    .build();
```

### Multiple Exporters

```java
MultiExporter exporter = new MultiExporter(
    SplunkHECExporter.builder()...build(),
    ElasticsearchExporter.builder()...build(),
    ConsoleExporter.builder().build()
);

GenAITelemetry telemetry = GenAITelemetry.builder()
    .workflowName("my-app")
    .exporter(exporter)
    .build();
```

### Console (Development)

```java
ConsoleExporter exporter = ConsoleExporter.builder()
    .colored(true)
    .verbose(false)
    .build();
```

## Tracing Operations

### traceLLM - Trace LLM Calls

```java
// Basic usage
Map<String, Object> response = telemetry.traceLLM(
    "chat",
    "gpt-4o",
    "openai",
    () -> callOpenAI(message)
);

// Token extraction happens automatically from the response
```

### traceEmbedding - Trace Embedding Calls

```java
List<Float> embedding = telemetry.traceEmbedding(
    "embed",
    "text-embedding-3-small",
    () -> embeddingClient.embed(text)
);
```

### traceTool - Trace Tool Calls

```java
String result = telemetry.traceTool(
    "search",
    "web_search",
    () -> searchAPI.search(query)
);
```

### traceChain - Trace Pipelines

```java
String answer = telemetry.traceChain(
    "rag-pipeline",
    () -> {
        // Nested operations are automatically linked
        var docs = telemetry.traceTool("retrieve", "vector_search",
            () -> vectorStore.search(query));
        
        return telemetry.traceLLM("generate", "gpt-4o", "openai",
            () -> llm.generate(docs, query));
    }
);
```

### traceAgent - Trace Agent Calls

```java
String result = telemetry.traceAgent(
    "execute",
    "research-agent",
    "react",
    () -> agent.run(task)
);
```

## Manual Span Management

For more control, use manual span management:

```java
Span span = telemetry.startSpan("custom-operation", SpanType.TOOL);
span.setToolName("my-tool");
span.setAttribute("custom_field", "value");

try {
    // Your operation
    doSomething();
} catch (Exception e) {
    span.setError(e);
    throw e;
} finally {
    telemetry.endSpan().join();
}
```

## Direct Span Sending

Send spans without the span stack:

```java
telemetry.sendSpan(SpanType.LLM, "custom-llm-call", SpanData.builder()
    .modelName("gpt-4o")
    .modelProvider("openai")
    .durationMs(150)
    .inputTokens(100)
    .outputTokens(50)
    .status(SpanStatus.OK)
).join();
```

## Span Data Schema

Each span includes:

| Field | Type | Description |
|-------|------|-------------|
| `trace_id` | String | Unique trace identifier (32 hex chars) |
| `span_id` | String | Unique span identifier (16 hex chars) |
| `parent_span_id` | String | Parent span ID for nesting |
| `span_type` | String | LLM, EMBEDDING, RETRIEVER, TOOL, CHAIN, AGENT |
| `name` | String | Operation name |
| `workflow_name` | String | Application/workflow name |
| `timestamp` | String | ISO 8601 timestamp |
| `duration_ms` | double | Duration in milliseconds |
| `status` | String | OK or ERROR |
| `is_error` | int | 0 or 1 |
| `model_name` | String | LLM model name |
| `model_provider` | String | Provider (openai, anthropic, etc.) |
| `input_tokens` | int | Input token count |
| `output_tokens` | int | Output token count |
| `total_tokens` | int | Total token count |

## Thread Safety

GenAI Telemetry uses `ThreadLocal` for trace context management, making it safe for concurrent applications:

```java
ExecutorService executor = Executors.newFixedThreadPool(10);

for (int i = 0; i < 100; i++) {
    executor.submit(() -> {
        // Each thread gets its own trace context
        telemetry.traceLLM("concurrent-call", "gpt-4o", "openai",
            () -> processRequest());
    });
}
```

## Requirements

- Java 11 or higher
- Jackson for JSON processing (included)
- SLF4J for logging (included)

## License

Apache-2.0 - See [LICENSE](../LICENSE) for details.

## Author

Kamal Singh Bisht

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for contribution guidelines.
