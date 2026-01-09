/**
 * Prometheus Push Gateway exporter.
 */

import type { SpanData } from '../types';
import { BaseExporter } from './base';

export interface PrometheusExporterOptions {
  pushgatewayUrl?: string;
  jobName?: string;
}

export class PrometheusExporter extends BaseExporter {
  private pushgatewayUrl: string;
  private jobName: string;

  // Metrics storage
  private metrics: {
    llmDuration: Map<string, number[]>;
    llmTokens: Map<string, { input: number; output: number }>;
    llmErrors: Map<string, number>;
    embeddingDuration: Map<string, number[]>;
    retrieverDuration: Map<string, number[]>;
    retrieverDocs: Map<string, number[]>;
  };

  constructor(options: PrometheusExporterOptions = {}) {
    super();
    this.pushgatewayUrl = (options.pushgatewayUrl || 'http://localhost:9091').replace(/\/$/, '');
    this.jobName = options.jobName || 'genai_telemetry';

    this.metrics = {
      llmDuration: new Map(),
      llmTokens: new Map(),
      llmErrors: new Map(),
      embeddingDuration: new Map(),
      retrieverDuration: new Map(),
      retrieverDocs: new Map(),
    };
  }

  private updateMetrics(span: SpanData): void {
    const key = `${span.workflow_name || 'default'}:${span.model_name || span.name}`;

    switch (span.span_type) {
      case 'LLM': {
        if (!this.metrics.llmDuration.has(key)) {
          this.metrics.llmDuration.set(key, []);
        }
        this.metrics.llmDuration.get(key)!.push(span.duration_ms);

        const tokens = this.metrics.llmTokens.get(key) || { input: 0, output: 0 };
        tokens.input += span.input_tokens || 0;
        tokens.output += span.output_tokens || 0;
        this.metrics.llmTokens.set(key, tokens);

        if (span.is_error) {
          this.metrics.llmErrors.set(key, (this.metrics.llmErrors.get(key) || 0) + 1);
        }
        break;
      }
      case 'EMBEDDING': {
        if (!this.metrics.embeddingDuration.has(key)) {
          this.metrics.embeddingDuration.set(key, []);
        }
        this.metrics.embeddingDuration.get(key)!.push(span.duration_ms);
        break;
      }
      case 'RETRIEVER': {
        const rKey = `${span.workflow_name || 'default'}:${span.vector_store || span.name}`;
        if (!this.metrics.retrieverDuration.has(rKey)) {
          this.metrics.retrieverDuration.set(rKey, []);
        }
        this.metrics.retrieverDuration.get(rKey)!.push(span.duration_ms);

        if (!this.metrics.retrieverDocs.has(rKey)) {
          this.metrics.retrieverDocs.set(rKey, []);
        }
        this.metrics.retrieverDocs.get(rKey)!.push(span.documents_retrieved || 0);
        break;
      }
    }
  }

  private buildMetricsPayload(): string {
    const lines: string[] = [];

    // LLM duration histogram (simplified as gauge with count and sum)
    lines.push('# HELP genai_llm_duration_seconds LLM call duration');
    lines.push('# TYPE genai_llm_duration_seconds summary');
    for (const [key, durations] of this.metrics.llmDuration) {
      const [workflow, model] = key.split(':');
      const labels = `workflow="${workflow}",model="${model}"`;
      const sum = durations.reduce((a, b) => a + b, 0) / 1000;
      lines.push(`genai_llm_duration_seconds_sum{${labels}} ${sum}`);
      lines.push(`genai_llm_duration_seconds_count{${labels}} ${durations.length}`);
    }

    // LLM tokens
    lines.push('# HELP genai_llm_tokens_total Total tokens used');
    lines.push('# TYPE genai_llm_tokens_total counter');
    for (const [key, tokens] of this.metrics.llmTokens) {
      const [workflow, model] = key.split(':');
      const labels = `workflow="${workflow}",model="${model}"`;
      lines.push(`genai_llm_tokens_total{${labels},type="input"} ${tokens.input}`);
      lines.push(`genai_llm_tokens_total{${labels},type="output"} ${tokens.output}`);
    }

    // LLM errors
    lines.push('# HELP genai_llm_errors_total Total LLM errors');
    lines.push('# TYPE genai_llm_errors_total counter');
    for (const [key, count] of this.metrics.llmErrors) {
      const [workflow, model] = key.split(':');
      const labels = `workflow="${workflow}",model="${model}"`;
      lines.push(`genai_llm_errors_total{${labels}} ${count}`);
    }

    // Embedding duration
    lines.push('# HELP genai_embedding_duration_seconds Embedding call duration');
    lines.push('# TYPE genai_embedding_duration_seconds summary');
    for (const [key, durations] of this.metrics.embeddingDuration) {
      const [workflow, model] = key.split(':');
      const labels = `workflow="${workflow}",model="${model}"`;
      const sum = durations.reduce((a, b) => a + b, 0) / 1000;
      lines.push(`genai_embedding_duration_seconds_sum{${labels}} ${sum}`);
      lines.push(`genai_embedding_duration_seconds_count{${labels}} ${durations.length}`);
    }

    // Retriever duration
    lines.push('# HELP genai_retriever_duration_seconds Retriever call duration');
    lines.push('# TYPE genai_retriever_duration_seconds summary');
    for (const [key, durations] of this.metrics.retrieverDuration) {
      const [workflow, store] = key.split(':');
      const labels = `workflow="${workflow}",vector_store="${store}"`;
      const sum = durations.reduce((a, b) => a + b, 0) / 1000;
      lines.push(`genai_retriever_duration_seconds_sum{${labels}} ${sum}`);
      lines.push(`genai_retriever_duration_seconds_count{${labels}} ${durations.length}`);
    }

    // Retriever documents
    lines.push('# HELP genai_retriever_documents_total Documents retrieved');
    lines.push('# TYPE genai_retriever_documents_total counter');
    for (const [key, docs] of this.metrics.retrieverDocs) {
      const [workflow, store] = key.split(':');
      const labels = `workflow="${workflow}",vector_store="${store}"`;
      const total = docs.reduce((a, b) => a + b, 0);
      lines.push(`genai_retriever_documents_total{${labels}} ${total}`);
    }

    return lines.join('\n') + '\n';
  }

  async export(spanData: SpanData): Promise<boolean> {
    try {
      this.updateMetrics(spanData);
      const payload = this.buildMetricsPayload();

      const response = await fetch(
        `${this.pushgatewayUrl}/metrics/job/${this.jobName}`,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'text/plain' },
          body: payload,
        }
      );

      return response.ok;
    } catch (error) {
      console.error('Prometheus Push Gateway Error:', error);
      return false;
    }
  }

  async healthCheck(): Promise<boolean> {
    try {
      const response = await fetch(`${this.pushgatewayUrl}/-/healthy`);
      return response.ok;
    } catch {
      return false;
    }
  }
}
