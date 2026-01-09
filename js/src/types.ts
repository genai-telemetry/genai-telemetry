/**
 * GenAI Telemetry - Type Definitions
 */

// ============================================================================
// Span Types
// ============================================================================

export type SpanType = 
  | 'LLM' 
  | 'EMBEDDING' 
  | 'RETRIEVER' 
  | 'TOOL' 
  | 'CHAIN' 
  | 'AGENT';

export type SpanStatus = 'OK' | 'ERROR';

export interface SpanData {
  trace_id: string;
  span_id: string;
  parent_span_id?: string;
  name: string;
  span_type: SpanType;
  workflow_name?: string;
  timestamp: string;
  duration_ms: number;
  status: SpanStatus;
  is_error: 0 | 1;
  
  // Error fields
  error_message?: string;
  error_type?: string;
  
  // LLM fields
  model_name?: string;
  model_provider?: string;
  input_tokens?: number;
  output_tokens?: number;
  total_tokens?: number;
  temperature?: number;
  max_tokens?: number;
  
  // Embedding fields
  embedding_model?: string;
  embedding_dimensions?: number;
  
  // Retrieval fields
  vector_store?: string;
  documents_retrieved?: number;
  relevance_score?: number;
  
  // Tool fields
  tool_name?: string;
  
  // Agent fields
  agent_name?: string;
  agent_type?: string;
  
  // Custom attributes
  [key: string]: unknown;
}

// ============================================================================
// Exporter Types
// ============================================================================

export type ExporterType = 
  | 'splunk' 
  | 'elasticsearch' 
  | 'es'
  | 'elastic'
  | 'otlp' 
  | 'opentelemetry'
  | 'otel'
  | 'datadog' 
  | 'prometheus' 
  | 'loki' 
  | 'cloudwatch'
  | 'aws'
  | 'console' 
  | 'file';

export interface ExporterConfig {
  type: ExporterType;
  
  // Splunk
  url?: string;
  token?: string;
  index?: string;
  
  // Elasticsearch
  hosts?: string[];
  api_key?: string;
  username?: string;
  password?: string;
  
  // OTLP
  endpoint?: string;
  headers?: Record<string, string>;
  
  // Datadog
  api_key?: string;
  site?: string;
  
  // Prometheus
  gateway?: string;
  job_name?: string;
  
  // Loki
  tenant_id?: string;
  
  // CloudWatch
  log_group?: string;
  region?: string;
  
  // File
  path?: string;
  
  // Common
  service_name?: string;
  verify_ssl?: boolean;
  batch_size?: number;
  flush_interval?: number;
  colored?: boolean;
  verbose?: boolean;
}

// ============================================================================
// Setup Options
// ============================================================================

export interface SetupOptions {
  workflowName: string;
  exporter?: ExporterType | ExporterConfig | ExporterConfig[];
  serviceName?: string;
  
  // Splunk options
  splunkUrl?: string;
  splunkToken?: string;
  splunkIndex?: string;
  
  // Elasticsearch options
  esHosts?: string[];
  esIndex?: string;
  esApiKey?: string;
  esUsername?: string;
  esPassword?: string;
  
  // OTLP options
  otlpEndpoint?: string;
  otlpHeaders?: Record<string, string>;
  
  // Datadog options
  datadogApiKey?: string;
  datadogSite?: string;
  
  // Prometheus options
  prometheusGateway?: string;
  
  // Loki options
  lokiUrl?: string;
  lokiTenantId?: string;
  
  // CloudWatch options
  cloudwatchLogGroup?: string;
  cloudwatchRegion?: string;
  
  // File options
  filePath?: string;
  
  // Common options
  console?: boolean;
  verifySsl?: boolean;
  batchSize?: number;
  flushInterval?: number;
}

// ============================================================================
// Decorator Options
// ============================================================================

export interface TraceLLMOptions {
  modelName: string;
  modelProvider?: string;
  extractContent?: boolean;
}

export interface TraceEmbeddingOptions {
  model: string;
}

export interface TraceRetrievalOptions {
  vectorStore: string;
  embeddingModel?: string;
}

export interface TraceToolOptions {
  toolName: string;
}

export interface TraceChainOptions {
  name: string;
}

export interface TraceAgentOptions {
  agentName: string;
  agentType?: string;
}

// ============================================================================
// Response Types (for token extraction)
// ============================================================================

export interface OpenAIUsage {
  prompt_tokens?: number;
  completion_tokens?: number;
  total_tokens?: number;
}

export interface OpenAIResponse {
  usage?: OpenAIUsage;
  choices?: Array<{
    message?: {
      content?: string;
    };
    text?: string;
  }>;
}

export interface AnthropicUsage {
  input_tokens?: number;
  output_tokens?: number;
}

export interface AnthropicResponse {
  usage?: AnthropicUsage;
  content?: Array<{
    text?: string;
    type?: string;
  }>;
}

export type LLMResponse = OpenAIResponse | AnthropicResponse | unknown;
