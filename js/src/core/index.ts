/**
 * Core module exports.
 */

export { Span, type SpanOptions } from './span';
export { GenAITelemetry, setupTelemetry, getTelemetry } from './telemetry';
export {
  extractTokensFromResponse,
  extractContentFromResponse,
  generateTraceId,
  generateSpanId,
  getTimestamp,
} from './utils';
export {
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
} from './decorators';
