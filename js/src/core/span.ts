/**
 * Span class representing a single span in a trace.
 */

import type { SpanType, SpanStatus, SpanData } from '../types';
import { getTimestamp } from './utils';

export interface SpanOptions {
  traceId: string;
  spanId: string;
  name: string;
  spanType: SpanType;
  workflowName?: string;
  parentSpanId?: string;
  modelName?: string;
  modelProvider?: string;
  inputTokens?: number;
  outputTokens?: number;
  temperature?: number;
  maxTokens?: number;
  embeddingModel?: string;
  embeddingDimensions?: number;
  vectorStore?: string;
  documentsRetrieved?: number;
  relevanceScore?: number;
  toolName?: string;
  agentName?: string;
  agentType?: string;
}

export class Span {
  readonly traceId: string;
  readonly spanId: string;
  readonly name: string;
  readonly spanType: SpanType;
  readonly workflowName?: string;
  readonly parentSpanId?: string;
  
  private startTime: number;
  private endTime?: number;
  
  durationMs?: number;
  status: SpanStatus = 'OK';
  isError: 0 | 1 = 0;
  errorMessage?: string;
  errorType?: string;
  
  // LLM fields
  modelName?: string;
  modelProvider?: string;
  inputTokens: number = 0;
  outputTokens: number = 0;
  temperature?: number;
  maxTokens?: number;
  
  // Embedding fields
  embeddingModel?: string;
  embeddingDimensions?: number;
  
  // Retrieval fields
  vectorStore?: string;
  documentsRetrieved: number = 0;
  relevanceScore?: number;
  
  // Tool fields
  toolName?: string;
  
  // Agent fields
  agentName?: string;
  agentType?: string;
  
  // Custom attributes
  private attributes: Record<string, unknown> = {};

  constructor(options: SpanOptions) {
    this.traceId = options.traceId;
    this.spanId = options.spanId;
    this.name = options.name;
    this.spanType = options.spanType;
    this.workflowName = options.workflowName;
    this.parentSpanId = options.parentSpanId;
    this.startTime = Date.now();
    
    // LLM fields
    this.modelName = options.modelName;
    this.modelProvider = options.modelProvider;
    this.inputTokens = options.inputTokens || 0;
    this.outputTokens = options.outputTokens || 0;
    this.temperature = options.temperature;
    this.maxTokens = options.maxTokens;
    
    // Embedding fields
    this.embeddingModel = options.embeddingModel;
    this.embeddingDimensions = options.embeddingDimensions;
    
    // Retrieval fields
    this.vectorStore = options.vectorStore;
    this.documentsRetrieved = options.documentsRetrieved || 0;
    this.relevanceScore = options.relevanceScore;
    
    // Tool fields
    this.toolName = options.toolName;
    
    // Agent fields
    this.agentName = options.agentName;
    this.agentType = options.agentType;
  }

  /**
   * Set a custom attribute on the span.
   */
  setAttribute(key: string, value: unknown): void {
    this.attributes[key] = value;
  }

  /**
   * Set error information on the span.
   */
  setError(error: Error): void {
    this.status = 'ERROR';
    this.isError = 1;
    this.errorMessage = error.message;
    this.errorType = error.name;
  }

  /**
   * Finish the span and calculate duration.
   */
  finish(error?: Error): void {
    this.endTime = Date.now();
    this.durationMs = Math.round((this.endTime - this.startTime) * 100) / 100;
    
    if (error) {
      this.setError(error);
    }
  }

  /**
   * Convert span to a dictionary format for export.
   */
  toDict(): SpanData {
    const data: SpanData = {
      trace_id: this.traceId,
      span_id: this.spanId,
      name: this.name,
      span_type: this.spanType,
      timestamp: new Date(this.startTime).toISOString(),
      duration_ms: this.durationMs || 0,
      status: this.status,
      is_error: this.isError,
    };

    // Add optional fields if they have values
    if (this.workflowName) data.workflow_name = this.workflowName;
    if (this.parentSpanId) data.parent_span_id = this.parentSpanId;
    if (this.errorMessage) data.error_message = this.errorMessage;
    if (this.errorType) data.error_type = this.errorType;
    
    // LLM fields
    if (this.modelName) data.model_name = this.modelName;
    if (this.modelProvider) data.model_provider = this.modelProvider;
    if (this.spanType === 'LLM') {
      data.input_tokens = this.inputTokens;
      data.output_tokens = this.outputTokens;
      data.total_tokens = this.inputTokens + this.outputTokens;
    } else {
      if (this.inputTokens) data.input_tokens = this.inputTokens;
      if (this.outputTokens) data.output_tokens = this.outputTokens;
    }
    if (this.temperature !== undefined) data.temperature = this.temperature;
    if (this.maxTokens !== undefined) data.max_tokens = this.maxTokens;
    
    // Embedding fields
    if (this.embeddingModel) data.embedding_model = this.embeddingModel;
    if (this.embeddingDimensions) data.embedding_dimensions = this.embeddingDimensions;
    
    // Retrieval fields
    if (this.vectorStore) data.vector_store = this.vectorStore;
    if (this.documentsRetrieved) data.documents_retrieved = this.documentsRetrieved;
    if (this.relevanceScore !== undefined) data.relevance_score = this.relevanceScore;
    
    // Tool fields
    if (this.toolName) data.tool_name = this.toolName;
    
    // Agent fields
    if (this.agentName) data.agent_name = this.agentName;
    if (this.agentType) data.agent_type = this.agentType;
    
    // Add custom attributes
    Object.assign(data, this.attributes);

    return data;
  }
}
