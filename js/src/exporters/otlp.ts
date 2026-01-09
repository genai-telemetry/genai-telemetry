/**
 * OpenTelemetry Protocol (OTLP) exporter.
 */

import type { SpanData } from '../types';
import { BaseExporter } from './base';

export interface OTLPExporterOptions {
  endpoint?: string;
  headers?: Record<string, string>;
  serviceName?: string;
  verifySsl?: boolean;
  batchSize?: number;
  flushInterval?: number;
}

interface OTLPSpan {
  traceId: string;
  spanId: string;
  parentSpanId?: string;
  name: string;
  kind: number;
  startTimeUnixNano: string;
  endTimeUnixNano: string;
  attributes: Array<{ key: string; value: { stringValue?: string; intValue?: string; doubleValue?: number } }>;
  status: { code: number; message?: string };
}

export class OTLPExporter extends BaseExporter {
  private endpoint: string;
  private headers: Record<string, string>;
  private serviceName: string;
  private batchSize: number;
  private flushInterval: number;

  private batch: SpanData[] = [];
  private flushTimer?: ReturnType<typeof setInterval>;
  private running: boolean = false;

  constructor(options: OTLPExporterOptions = {}) {
    super();
    
    let endpoint = options.endpoint || 'http://localhost:4318';
    endpoint = endpoint.replace(/\/$/, '');
    if (!endpoint.includes('/v1/traces')) {
      endpoint += '/v1/traces';
    }
    
    this.endpoint = endpoint;
    this.headers = {
      'Content-Type': 'application/json',
      ...options.headers,
    };
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

  private spanToOTLP(span: SpanData): OTLPSpan {
    const timestamp = new Date(span.timestamp).getTime();
    const durationNs = (span.duration_ms || 0) * 1_000_000;

    const attributes: OTLPSpan['attributes'] = [];
    
    // Add standard attributes
    const addAttr = (key: string, value: unknown) => {
      if (value === undefined || value === null) return;
      
      if (typeof value === 'string') {
        attributes.push({ key, value: { stringValue: value } });
      } else if (typeof value === 'number') {
        if (Number.isInteger(value)) {
          attributes.push({ key, value: { intValue: String(value) } });
        } else {
          attributes.push({ key, value: { doubleValue: value } });
        }
      } else {
        attributes.push({ key, value: { stringValue: String(value) } });
      }
    };

    addAttr('gen_ai.span_type', span.span_type);
    addAttr('gen_ai.workflow_name', span.workflow_name);
    addAttr('gen_ai.model.name', span.model_name);
    addAttr('gen_ai.model.provider', span.model_provider);
    addAttr('gen_ai.usage.input_tokens', span.input_tokens);
    addAttr('gen_ai.usage.output_tokens', span.output_tokens);
    addAttr('gen_ai.usage.total_tokens', span.total_tokens);
    addAttr('gen_ai.embedding.model', span.embedding_model);
    addAttr('gen_ai.vector_store', span.vector_store);
    addAttr('gen_ai.documents_retrieved', span.documents_retrieved);
    addAttr('gen_ai.tool.name', span.tool_name);
    addAttr('gen_ai.agent.name', span.agent_name);
    addAttr('gen_ai.agent.type', span.agent_type);

    if (span.is_error) {
      addAttr('error.message', span.error_message);
      addAttr('error.type', span.error_type);
    }

    return {
      traceId: span.trace_id,
      spanId: span.span_id,
      parentSpanId: span.parent_span_id,
      name: span.name,
      kind: 1, // SPAN_KIND_INTERNAL
      startTimeUnixNano: String(timestamp * 1_000_000),
      endTimeUnixNano: String((timestamp * 1_000_000) + durationNs),
      attributes,
      status: {
        code: span.is_error ? 2 : 1, // STATUS_CODE_ERROR or STATUS_CODE_OK
        message: span.error_message,
      },
    };
  }

  private async sendBatch(spans: SpanData[]): Promise<boolean> {
    if (spans.length === 0) return true;

    const otlpSpans = spans.map(s => this.spanToOTLP(s));

    const payload = {
      resourceSpans: [{
        resource: {
          attributes: [
            { key: 'service.name', value: { stringValue: this.serviceName } },
            { key: 'telemetry.sdk.name', value: { stringValue: 'genai-telemetry' } },
            { key: 'telemetry.sdk.language', value: { stringValue: 'javascript' } },
          ],
        },
        scopeSpans: [{
          scope: { name: 'genai-telemetry' },
          spans: otlpSpans,
        }],
      }],
    };

    try {
      const response = await fetch(this.endpoint, {
        method: 'POST',
        headers: this.headers,
        body: JSON.stringify(payload),
      });

      return response.ok;
    } catch (error) {
      console.error('OTLP Error:', error);
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
