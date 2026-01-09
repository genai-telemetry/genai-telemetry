/**
 * Main telemetry manager and setup functions.
 */

import type { SpanData, SpanType, SetupOptions, ExporterType, ExporterConfig } from '../types';
import { Span, type SpanOptions } from './span';
import { generateTraceId, generateSpanId, getTimestamp } from './utils';
import { BaseExporter } from '../exporters/base';
import { ConsoleExporter } from '../exporters/console';
import { FileExporter } from '../exporters/file';
import { SplunkHECExporter } from '../exporters/splunk';
import { ElasticsearchExporter } from '../exporters/elasticsearch';
import { OTLPExporter } from '../exporters/otlp';
import { DatadogExporter } from '../exporters/datadog';
import { PrometheusExporter } from '../exporters/prometheus';
import { LokiExporter } from '../exporters/loki';
import { CloudWatchExporter } from '../exporters/cloudwatch';
import { MultiExporter } from '../exporters/multi';

/**
 * Main telemetry manager.
 */
export class GenAITelemetry {
  readonly workflowName: string;
  readonly serviceName: string;
  readonly exporter: BaseExporter;

  private _traceId: string | null = null;
  private _spanStack: Span[] = [];

  constructor(
    workflowName: string,
    exporter: BaseExporter,
    serviceName?: string
  ) {
    this.workflowName = workflowName;
    this.serviceName = serviceName || workflowName;
    this.exporter = exporter;
  }

  get traceId(): string {
    if (!this._traceId) {
      this._traceId = generateTraceId();
    }
    return this._traceId;
  }

  set traceId(value: string) {
    this._traceId = value;
  }

  private get spanStack(): Span[] {
    return this._spanStack;
  }

  newTrace(): string {
    const traceId = generateTraceId();
    this.traceId = traceId;
    return traceId;
  }

  currentSpan(): Span | undefined {
    const stack = this.spanStack;
    return stack.length > 0 ? stack[stack.length - 1] : undefined;
  }

  startSpan(name: string, spanType: SpanType, options: Partial<SpanOptions> = {}): Span {
    const parentSpan = this.currentSpan();

    const span = new Span({
      traceId: this.traceId,
      spanId: generateSpanId(),
      name,
      spanType,
      workflowName: this.workflowName,
      parentSpanId: parentSpan?.spanId,
      ...options,
    });

    this.spanStack.push(span);
    return span;
  }

  async endSpan(error?: Error): Promise<void> {
    const span = this.spanStack.pop();
    if (span) {
      span.finish(error);
      await this.exporter.export(span.toDict());
    }
  }

  async withSpan<T>(
    name: string,
    spanType: SpanType,
    fn: (span: Span) => Promise<T>,
    options: Partial<SpanOptions> = {}
  ): Promise<T> {
    const span = this.startSpan(name, spanType, options);

    try {
      const result = await fn(span);
      await this.endSpan();
      return result;
    } catch (error) {
      await this.endSpan(error as Error);
      throw error;
    }
  }

  async sendSpan(
    spanType: SpanType,
    name: string,
    options: {
      durationMs?: number;
      status?: 'OK' | 'ERROR';
      isError?: 0 | 1;
      modelName?: string;
      modelProvider?: string;
      inputTokens?: number;
      outputTokens?: number;
      embeddingModel?: string;
      vectorStore?: string;
      documentsRetrieved?: number;
      toolName?: string;
      agentName?: string;
      agentType?: string;
      errorMessage?: string;
      errorType?: string;
      [key: string]: unknown;
    } = {}
  ): Promise<boolean> {
    const parentSpan = this.currentSpan();

    const spanData: SpanData = {
      trace_id: this.traceId,
      span_id: generateSpanId(),
      parent_span_id: parentSpan?.spanId,
      span_type: spanType,
      name,
      workflow_name: this.workflowName,
      timestamp: getTimestamp(),
      duration_ms: options.durationMs || 0,
      status: options.status || 'OK',
      is_error: options.isError || 0,
    };

    if (options.modelName) spanData.model_name = options.modelName;
    if (options.modelProvider) spanData.model_provider = options.modelProvider;
    if (options.inputTokens !== undefined) spanData.input_tokens = options.inputTokens;
    if (options.outputTokens !== undefined) spanData.output_tokens = options.outputTokens;
    if (options.inputTokens !== undefined && options.outputTokens !== undefined) {
      spanData.total_tokens = options.inputTokens + options.outputTokens;
    }
    if (options.embeddingModel) spanData.embedding_model = options.embeddingModel;
    if (options.vectorStore) spanData.vector_store = options.vectorStore;
    if (options.documentsRetrieved !== undefined) spanData.documents_retrieved = options.documentsRetrieved;
    if (options.toolName) spanData.tool_name = options.toolName;
    if (options.agentName) spanData.agent_name = options.agentName;
    if (options.agentType) spanData.agent_type = options.agentType;
    if (options.errorMessage) spanData.error_message = options.errorMessage;
    if (options.errorType) spanData.error_type = options.errorType;

    const knownKeys = new Set([
      'durationMs', 'status', 'isError', 'modelName', 'modelProvider',
      'inputTokens', 'outputTokens', 'embeddingModel', 'vectorStore',
      'documentsRetrieved', 'toolName', 'agentName', 'agentType',
      'errorMessage', 'errorType',
    ]);

    for (const [key, value] of Object.entries(options)) {
      if (!knownKeys.has(key) && value !== undefined && value !== null && value !== '') {
        spanData[key] = value;
      }
    }

    return this.exporter.export(spanData);
  }
}

// ============================================================================
// GLOBAL INSTANCE & SETUP
// ============================================================================

let _telemetry: GenAITelemetry | null = null;

function createExporter(exporterType: ExporterType, config: Record<string, unknown>): BaseExporter {
  const type = exporterType.toLowerCase() as ExporterType;

  switch (type) {
    case 'splunk': {
      const url = (config.splunkUrl || config.url) as string;
      const token = (config.splunkToken || config.token) as string;
      if (!url || !token) {
        throw new Error('Splunk requires splunkUrl and splunkToken');
      }
      return new SplunkHECExporter({
        hecUrl: url,
        hecToken: token,
        index: (config.splunkIndex || config.index || 'genai_traces') as string,
        verifySsl: config.verifySsl as boolean,
        batchSize: config.batchSize as number,
        flushInterval: config.flushInterval as number,
      });
    }

    case 'elasticsearch':
    case 'es':
    case 'elastic': {
      const hosts = (config.esHosts || config.hosts || ['http://localhost:9200']) as string[];
      return new ElasticsearchExporter({
        hosts,
        index: (config.esIndex || config.index || 'genai-traces') as string,
        apiKey: (config.esApiKey || config.apiKey) as string,
        username: (config.esUsername || config.username) as string,
        password: (config.esPassword || config.password) as string,
        verifySsl: config.verifySsl as boolean,
        batchSize: config.batchSize as number,
        flushInterval: config.flushInterval as number,
      });
    }

    case 'otlp':
    case 'opentelemetry':
    case 'otel': {
      return new OTLPExporter({
        endpoint: (config.otlpEndpoint || config.endpoint || 'http://localhost:4318') as string,
        headers: (config.otlpHeaders || config.headers) as Record<string, string>,
        serviceName: (config.serviceName || 'genai-app') as string,
        verifySsl: config.verifySsl as boolean,
        batchSize: config.batchSize as number,
        flushInterval: config.flushInterval as number,
      });
    }

    case 'datadog': {
      const apiKey = (config.datadogApiKey || config.apiKey) as string;
      if (!apiKey) {
        throw new Error('Datadog requires datadogApiKey');
      }
      return new DatadogExporter({
        apiKey,
        site: (config.datadogSite || config.site || 'datadoghq.com') as string,
        serviceName: (config.serviceName || 'genai-app') as string,
        batchSize: config.batchSize as number,
        flushInterval: config.flushInterval as number,
      });
    }

    case 'prometheus': {
      return new PrometheusExporter({
        pushgatewayUrl: (config.prometheusGateway || config.gateway || 'http://localhost:9091') as string,
        jobName: config.jobName as string,
      });
    }

    case 'loki': {
      return new LokiExporter({
        url: (config.lokiUrl || config.url || 'http://localhost:3100') as string,
        tenantId: (config.lokiTenantId || config.tenantId) as string,
        batchSize: config.batchSize as number,
        flushInterval: config.flushInterval as number,
      });
    }

    case 'cloudwatch':
    case 'aws': {
      return new CloudWatchExporter({
        logGroup: (config.cloudwatchLogGroup || config.logGroup || '/genai/traces') as string,
        region: (config.cloudwatchRegion || config.region || 'us-east-1') as string,
        batchSize: config.batchSize as number,
        flushInterval: config.flushInterval as number,
      });
    }

    case 'file': {
      return new FileExporter({
        filePath: (config.filePath || config.path || 'genai_traces.jsonl') as string,
      });
    }

    case 'console': {
      return new ConsoleExporter({
        colored: config.colored as boolean,
        verbose: config.verbose as boolean,
      });
    }

    default:
      throw new Error(`Unknown exporter type: ${exporterType}`);
  }
}

/**
 * Initialize GenAI telemetry with the specified exporter(s).
 */
export function setupTelemetry(options: SetupOptions): GenAITelemetry {
  const exporters: BaseExporter[] = [];

  const config: Record<string, unknown> = {
    splunkUrl: options.splunkUrl,
    splunkToken: options.splunkToken,
    splunkIndex: options.splunkIndex,
    esHosts: options.esHosts,
    esIndex: options.esIndex,
    esApiKey: options.esApiKey,
    esUsername: options.esUsername,
    esPassword: options.esPassword,
    otlpEndpoint: options.otlpEndpoint,
    otlpHeaders: options.otlpHeaders,
    datadogApiKey: options.datadogApiKey,
    datadogSite: options.datadogSite,
    prometheusGateway: options.prometheusGateway,
    lokiUrl: options.lokiUrl,
    lokiTenantId: options.lokiTenantId,
    cloudwatchLogGroup: options.cloudwatchLogGroup,
    cloudwatchRegion: options.cloudwatchRegion,
    filePath: options.filePath,
    verifySsl: options.verifySsl,
    batchSize: options.batchSize,
    flushInterval: options.flushInterval,
    serviceName: options.serviceName || options.workflowName,
  };

  // Handle exporter configuration
  if (Array.isArray(options.exporter)) {
    // Multiple exporters
    for (const expConfig of options.exporter) {
      const expInstance = createExporter(expConfig.type, { ...config, ...expConfig });
      exporters.push(expInstance);
    }
  } else if (typeof options.exporter === 'string') {
    // Single exporter type
    const expInstance = createExporter(options.exporter, config);
    exporters.push(expInstance);
  } else if (options.exporter && typeof options.exporter === 'object') {
    // Single exporter config
    const expConfig = options.exporter as ExporterConfig;
    const expInstance = createExporter(expConfig.type, { ...config, ...expConfig });
    exporters.push(expInstance);
  }

  // Add console if requested
  if (options.console && !exporters.some(e => e instanceof ConsoleExporter)) {
    exporters.push(new ConsoleExporter());
  }

  // Default to console if no exporters
  if (exporters.length === 0) {
    exporters.push(new ConsoleExporter());
  }

  // Create final exporter
  const finalExporter = exporters.length > 1 ? new MultiExporter(exporters) : exporters[0];
  finalExporter.start();

  _telemetry = new GenAITelemetry(
    options.workflowName,
    finalExporter,
    options.serviceName
  );

  return _telemetry;
}

/**
 * Get the telemetry instance.
 */
export function getTelemetry(): GenAITelemetry {
  if (!_telemetry) {
    throw new Error('Call setupTelemetry() first');
  }
  return _telemetry;
}
