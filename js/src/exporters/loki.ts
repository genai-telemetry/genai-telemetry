/**
 * Grafana Loki exporter.
 */

import type { SpanData } from '../types';
import { BaseExporter } from './base';

export interface LokiExporterOptions {
  url?: string;
  tenantId?: string;
  batchSize?: number;
  flushInterval?: number;
}

interface LokiStream {
  stream: Record<string, string>;
  values: Array<[string, string]>;
}

export class LokiExporter extends BaseExporter {
  private url: string;
  private tenantId?: string;
  private batchSize: number;
  private flushInterval: number;

  private batch: SpanData[] = [];
  private flushTimer?: ReturnType<typeof setInterval>;
  private running: boolean = false;

  constructor(options: LokiExporterOptions = {}) {
    super();
    
    let url = (options.url || 'http://localhost:3100').replace(/\/$/, '');
    if (!url.includes('/loki/api/v1/push')) {
      url += '/loki/api/v1/push';
    }
    
    this.url = url;
    this.tenantId = options.tenantId;
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

  private spansToLokiStreams(spans: SpanData[]): LokiStream[] {
    // Group spans by their labels
    const streamMap = new Map<string, LokiStream>();

    for (const span of spans) {
      const labels: Record<string, string> = {
        job: 'genai-telemetry',
        span_type: span.span_type,
        workflow: span.workflow_name || 'default',
        status: span.status,
      };

      if (span.model_name) labels.model = span.model_name;
      if (span.model_provider) labels.provider = span.model_provider;

      // Create a key for grouping
      const labelKey = Object.entries(labels)
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([k, v]) => `${k}="${v}"`)
        .join(',');

      if (!streamMap.has(labelKey)) {
        streamMap.set(labelKey, {
          stream: labels,
          values: [],
        });
      }

      // Loki expects nanosecond timestamps as strings
      const timestamp = new Date(span.timestamp).getTime() * 1_000_000;
      const logLine = JSON.stringify(span);
      
      streamMap.get(labelKey)!.values.push([String(timestamp), logLine]);
    }

    return Array.from(streamMap.values());
  }

  private async sendBatch(spans: SpanData[]): Promise<boolean> {
    if (spans.length === 0) return true;

    const streams = this.spansToLokiStreams(spans);
    const payload = { streams };

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    if (this.tenantId) {
      headers['X-Scope-OrgID'] = this.tenantId;
    }

    try {
      const response = await fetch(this.url, {
        method: 'POST',
        headers,
        body: JSON.stringify(payload),
      });

      return response.ok || response.status === 204;
    } catch (error) {
      console.error('Loki Error:', error);
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

  async healthCheck(): Promise<boolean> {
    try {
      const baseUrl = this.url.replace('/loki/api/v1/push', '');
      const response = await fetch(`${baseUrl}/ready`);
      return response.ok;
    } catch {
      return false;
    }
  }
}
