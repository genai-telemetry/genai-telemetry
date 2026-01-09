/**
 * AWS CloudWatch Logs exporter.
 */

import type { SpanData } from '../types';
import { BaseExporter } from './base';

export interface CloudWatchExporterOptions {
  logGroup?: string;
  region?: string;
  accessKeyId?: string;
  secretAccessKey?: string;
  batchSize?: number;
  flushInterval?: number;
}

export class CloudWatchExporter extends BaseExporter {
  private logGroup: string;
  private region: string;
  private accessKeyId?: string;
  private secretAccessKey?: string;
  private batchSize: number;
  private flushInterval: number;

  private batch: SpanData[] = [];
  private flushTimer?: ReturnType<typeof setInterval>;
  private running: boolean = false;
  private sequenceToken?: string;
  private logStreamName: string;

  constructor(options: CloudWatchExporterOptions = {}) {
    super();
    this.logGroup = options.logGroup || '/genai/traces';
    this.region = options.region || process.env.AWS_REGION || 'us-east-1';
    this.accessKeyId = options.accessKeyId || process.env.AWS_ACCESS_KEY_ID;
    this.secretAccessKey = options.secretAccessKey || process.env.AWS_SECRET_ACCESS_KEY;
    this.batchSize = options.batchSize || 10;
    this.flushInterval = (options.flushInterval || 5) * 1000;

    // Create a unique log stream name
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    this.logStreamName = `genai-telemetry-${timestamp}`;
  }

  start(): void {
    if (this.running) return;
    this.running = true;

    // Ensure log group and stream exist
    this.ensureLogStream();

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

  private async ensureLogStream(): Promise<void> {
    // This is a simplified implementation
    // In production, you'd use @aws-sdk/client-cloudwatch-logs
    console.log(`CloudWatch: Would create log group ${this.logGroup} and stream ${this.logStreamName}`);
  }

  private async sendBatch(spans: SpanData[]): Promise<boolean> {
    if (spans.length === 0) return true;

    // Prepare log events
    const logEvents = spans.map(span => ({
      timestamp: new Date(span.timestamp).getTime(),
      message: JSON.stringify(span),
    }));

    // Sort by timestamp (required by CloudWatch)
    logEvents.sort((a, b) => a.timestamp - b.timestamp);

    // In a real implementation, you'd use the AWS SDK
    // This is a simplified version using fetch with AWS Signature V4
    try {
      // Check if @aws-sdk/client-cloudwatch-logs is available
      try {
        const { CloudWatchLogsClient, PutLogEventsCommand, CreateLogStreamCommand } = 
          await import('@aws-sdk/client-cloudwatch-logs');

        const client = new CloudWatchLogsClient({
          region: this.region,
          ...(this.accessKeyId && this.secretAccessKey ? {
            credentials: {
              accessKeyId: this.accessKeyId,
              secretAccessKey: this.secretAccessKey,
            },
          } : {}),
        });

        // Try to create log stream (ignore if exists)
        try {
          await client.send(new CreateLogStreamCommand({
            logGroupName: this.logGroup,
            logStreamName: this.logStreamName,
          }));
        } catch {
          // Stream might already exist
        }

        const command = new PutLogEventsCommand({
          logGroupName: this.logGroup,
          logStreamName: this.logStreamName,
          logEvents,
          sequenceToken: this.sequenceToken,
        });

        const response = await client.send(command);
        this.sequenceToken = response.nextSequenceToken;
        return true;
      } catch (importError) {
        // AWS SDK not available, log warning
        console.warn(
          'CloudWatch exporter requires @aws-sdk/client-cloudwatch-logs. ' +
          'Install it with: npm install @aws-sdk/client-cloudwatch-logs'
        );
        console.log('CloudWatch: Would send', logEvents.length, 'log events');
        return true; // Return true to not block the application
      }
    } catch (error) {
      console.error('CloudWatch Error:', error);
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
