/**
 * GenAI Telemetry - Observability SDK for LLM Applications
 * =========================================================
 *
 * A platform-agnostic telemetry library for tracing GenAI/LLM applications.
 * Supports multiple backends: Splunk, Elasticsearch, OpenTelemetry, Datadog,
 * Prometheus, Grafana Loki, AWS CloudWatch, and more.
 *
 * @example Basic Usage with OpenAI
 * ```typescript
 * import { setupTelemetry, traceLLM } from 'genai-telemetry';
 * import OpenAI from 'openai';
 *
 * // Initialize telemetry
 * setupTelemetry({
 *   workflowName: 'my-chatbot',
 *   exporter: 'splunk',
 *   splunkUrl: 'http://splunk:8088',
 *   splunkToken: 'your-token'
 * });
 *
 * const client = new OpenAI();
 *
 * // Wrap your LLM function
 * const chat = traceLLM(
 *   async (message: string) => {
 *     return await client.chat.completions.create({
 *       model: 'gpt-4o',
 *       messages: [{ role: 'user', content: message }]
 *     });
 *   },
 *   { modelName: 'gpt-4o', modelProvider: 'openai' }
 * );
 *
 * // Use it
 * const response = await chat('Hello!');
 * console.log(response.choices[0].message.content);
 * ```
 *
 * @example Multiple Exporters
 * ```typescript
 * setupTelemetry({
 *   workflowName: 'my-app',
 *   exporter: [
 *     { type: 'splunk', url: '...', token: '...' },
 *     { type: 'elasticsearch', hosts: ['http://localhost:9200'] },
 *     { type: 'console' }
 *   ]
 * });
 * ```
 *
 * @author Kamal Singh Bisht
 * @license Apache-2.0
 */

export const VERSION = '1.0.3';

// Core exports
export {
  Span,
  type SpanOptions,
  GenAITelemetry,
  setupTelemetry,
  getTelemetry,
  extractTokensFromResponse,
  extractContentFromResponse,
  generateTraceId,
  generateSpanId,
  // Function wrappers
  traceLLM,
  traceEmbedding,
  traceRetrieval,
  traceTool,
  traceChain,
  traceAgent,
  // Class decorators
  TraceLLM,
  TraceEmbedding,
  TraceRetrieval,
  TraceTool,
  TraceChain,
  TraceAgent,
} from './core';

// Exporter exports
export {
  BaseExporter,
  ConsoleExporter,
  FileExporter,
  SplunkHECExporter,
  ElasticsearchExporter,
  OTLPExporter,
  DatadogExporter,
  PrometheusExporter,
  LokiExporter,
  CloudWatchExporter,
  MultiExporter,
} from './exporters';

// Type exports
export type {
  SpanType,
  SpanStatus,
  SpanData,
  ExporterType,
  ExporterConfig,
  SetupOptions,
  TraceLLMOptions,
  TraceEmbeddingOptions,
  TraceRetrievalOptions,
  TraceToolOptions,
  TraceChainOptions,
  TraceAgentOptions,
  LLMResponse,
  OpenAIResponse,
  AnthropicResponse,
} from './types';
