/**
 * Elasticsearch exporter.
 */

import type { SpanData } from '../types';
import { BaseExporter } from './base';

export interface ElasticsearchExporterOptions {
  hosts: string[];
  index?: string;
  apiKey?: string;
  username?: string;
  password?: string;
  verifySsl?: boolean;
  batchSize?: number;
  flushInterval?: number;
}

export class ElasticsearchExporter extends BaseExporter {
  private hosts: string[];
  private index: string;
  private apiKey?: string;
  private username?: string;
  private password?: string;
  private batchSize: number;
  private flushInterval: number;
  
  private batch: SpanData[] = [];
  private flushTimer?: ReturnType<typeof setInterval>;
  private running: boolean = false;
  private hostIndex: number = 0;

  constructor(options: ElasticsearchExporterOptions) {
    super();
    this.hosts = options.hosts.map(h => h.replace(/\/$/, ''));
    this.index = options.index || 'genai-traces';
    this.apiKey = options.apiKey;
    this.username = options.username;
    this.password = options.password;
    this.batchSize = options.batchSize || 1;
    this.flushInterval = (options.flushInterval || 5) * 1000;
  }

  private getHost(): string {
    const host = this.hosts[this.hostIndex];
    this.hostIndex = (this.hostIndex + 1) % this.hosts.length;
    return host;
  }

  private getHeaders(): Record<string, string> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    if (this.apiKey) {
      headers['Authorization'] = `ApiKey ${this.apiKey}`;
    } else if (this.username && this.password) {
      const auth = Buffer.from(`${this.username}:${this.password}`).toString('base64');
      headers['Authorization'] = `Basic ${auth}`;
    }

    return headers;
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

    // Build bulk request body
    const lines: string[] = [];
    for (const span of spans) {
      lines.push(JSON.stringify({ index: { _index: this.index } }));
      lines.push(JSON.stringify(span));
    }
    const payload = lines.join('\n') + '\n';

    try {
      const host = this.getHost();
      const response = await fetch(`${host}/_bulk`, {
        method: 'POST',
        headers: this.getHeaders(),
        body: payload,
      });

      if (!response.ok) {
        console.error('Elasticsearch error:', await response.text());
        return false;
      }

      const result = await response.json() as { errors?: boolean };
      return !result.errors;
    } catch (error) {
      console.error('Elasticsearch Error:', error);
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
      const host = this.getHost();
      const response = await fetch(`${host}/_cluster/health`, {
        headers: this.getHeaders(),
      });
      return response.ok;
    } catch {
      return false;
    }
  }
}
