/**
 * Splunk HTTP Event Collector (HEC) exporter.
 */

import type { SpanData } from '../types';
import { BaseExporter } from './base';

export interface SplunkHECExporterOptions {
  hecUrl: string;
  hecToken: string;
  index?: string;
  sourcetype?: string;
  verifySsl?: boolean;
  batchSize?: number;
  flushInterval?: number;
}

export class SplunkHECExporter extends BaseExporter {
  private hecUrl: string;
  private hecToken: string;
  private index: string;
  private sourcetype: string;
  private batchSize: number;
  private flushInterval: number;
  
  private batch: SpanData[] = [];
  private flushTimer?: ReturnType<typeof setInterval>;
  private running: boolean = false;

  constructor(options: SplunkHECExporterOptions) {
    super();
    
    let url = options.hecUrl.replace(/\/$/, '');
    if (!url.endsWith('/services/collector/event')) {
      url += '/services/collector/event';
    }
    
    this.hecUrl = url;
    this.hecToken = options.hecToken;
    this.index = options.index || 'genai_traces';
    this.sourcetype = options.sourcetype || 'genai:trace';
    this.batchSize = options.batchSize || 1;
    this.flushInterval = (options.flushInterval || 5) * 1000; // Convert to ms
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

  private async sendBatch(spans: SpanData[]): Promise<boolean> {
    if (spans.length === 0) return true;

    const payload = spans.map(span => JSON.stringify({
      index: this.index,
      sourcetype: this.sourcetype,
      source: 'genai-telemetry',
      event: span,
    })).join('\n');

    try {
      const response = await fetch(this.hecUrl, {
        method: 'POST',
        headers: {
          'Authorization': `Splunk ${this.hecToken}`,
          'Content-Type': 'application/json',
        },
        body: payload,
      });

      return response.ok;
    } catch (error) {
      console.error('Splunk HEC Error:', error);
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
      return await this.sendBatch([{ 
        event: 'health_check', 
        sourcetype: 'genai:health' 
      } as unknown as SpanData]);
    } catch {
      return false;
    }
  }
}
