/**
 * Datadog exporter.
 */

import type { SpanData } from '../types';
import { BaseExporter } from './base';

export interface DatadogExporterOptions {
  apiKey: string;
  site?: string;
  serviceName?: string;
  batchSize?: number;
  flushInterval?: number;
}

interface DatadogSpan {
  trace_id: number;
  span_id: number;
  parent_id?: number;
  name: string;
  resource: string;
  service: string;
  type: string;
  start: number;
  duration: number;
  meta: Record<string, string>;
  metrics: Record<string, number>;
  error: number;
}

export class DatadogExporter extends BaseExporter {
  private apiKey: string;
  private site: string;
  private serviceName: string;
  private batchSize: number;
  private flushInterval: number;

  private batch: SpanData[] = [];
  private flushTimer?: ReturnType<typeof setInterval>;
  private running: boolean = false;

  constructor(options: DatadogExporterOptions) {
    super();
    this.apiKey = options.apiKey;
    this.site = options.site || 'datadoghq.com';
    this.serviceName = options.serviceName || 'genai-app';
    this.batchSize = options.batchSize || 10;
    this.flushInterval = (options.flushInterval || 5) * 1000;
  }

  start(): void {
    if (this.running) return;
    this.running = true;

    if (this.batchSize > 1) {
      this.flushTimer = setInterval(() => this.flush(), this.flushInterval);
    }
  }

  stop(): void {
    this.running = false;
    if (this.flushTimer) {
      clearInterval(this.flushTimer);
      this.flushTimer = undefined;
    }
    this.flush();
  }

  async flush(): Promise<void> {
    if (this.batch.length === 0) return;

    const batchToSend = [...this.batch];
    this.batch = [];

    await this.sendBatch(batchToSend);
  }

  private hexToInt(hex: string): number {
    // Take last 16 chars and convert to number
    const truncated = hex.slice(-16);
    return parseInt(truncated, 16);
  }

  private spanToDatadog(span: SpanData): DatadogSpan {
    const timestamp = new Date(span.timestamp).getTime();
    const durationNs = (span.duration_ms || 0) * 1_000_000;

    const meta: Record<string, string> = {
      'gen_ai.span_type': span.span_type,
    };

    const metrics: Record<string, number> = {};

    // Add metadata
    if (span.workflow_name) meta['gen_ai.workflow_name'] = span.workflow_name;
    if (span.model_name) meta['gen_ai.model.name'] = span.model_name;
    if (span.model_provider) meta['gen_ai.model.provider'] = span.model_provider;
    if (span.embedding_model) meta['gen_ai.embedding.model'] = span.embedding_model;
    if (span.vector_store) meta['gen_ai.vector_store'] = span.vector_store;
    if (span.tool_name) meta['gen_ai.tool.name'] = span.tool_name;
    if (span.agent_name) meta['gen_ai.agent.name'] = span.agent_name;
    if (span.agent_type) meta['gen_ai.agent.type'] = span.agent_type;

    // Add error info
    if (span.is_error) {
      if (span.error_message) meta['error.message'] = span.error_message;
      if (span.error_type) meta['error.type'] = span.error_type;
    }

    // Add metrics
    if (span.input_tokens) metrics['gen_ai.usage.input_tokens'] = span.input_tokens;
    if (span.output_tokens) metrics['gen_ai.usage.output_tokens'] = span.output_tokens;
    if (span.total_tokens) metrics['gen_ai.usage.total_tokens'] = span.total_tokens;
    if (span.documents_retrieved) metrics['gen_ai.documents_retrieved'] = span.documents_retrieved;

    const ddSpan: DatadogSpan = {
      trace_id: this.hexToInt(span.trace_id),
      span_id: this.hexToInt(span.span_id),
      name: span.span_type.toLowerCase(),
      resource: span.name,
      service: this.serviceName,
      type: 'custom',
      start: timestamp * 1_000_000, // nanoseconds
      duration: durationNs,
      meta,
      metrics,
      error: span.is_error,
    };

    if (span.parent_span_id) {
      ddSpan.parent_id = this.hexToInt(span.parent_span_id);
    }

    return ddSpan;
  }

  private async sendBatch(spans: SpanData[]): Promise<boolean> {
    if (spans.length === 0) return true;

    const ddSpans = spans.map(s => this.spanToDatadog(s));
    const payload = [[ddSpans]]; // Datadog expects array of traces, each trace is array of spans

    try {
      const response = await fetch(`https://trace.agent.${this.site}/api/v0.2/traces`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'DD-API-KEY': this.apiKey,
        },
        body: JSON.stringify(payload),
      });

      return response.ok;
    } catch (error) {
      console.error('Datadog Error:', error);
      return false;
    }
  }

  async export(spanData: SpanData): Promise<boolean> {
    if (this.batchSize <= 1) {
      return this.sendBatch([spanData]);
    }

    this.batch.push(spanData);

    if (this.batch.length >= this.batchSize) {
      await this.flush();
    }

    return true;
  }
}
