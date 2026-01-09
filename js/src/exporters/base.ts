/**
 * Base exporter interface for all telemetry exporters.
 */

import type { SpanData } from '../types';

export abstract class BaseExporter {
  /**
   * Export a single span.
   * @param spanData Dictionary containing span data
   * @returns True if export was successful
   */
  abstract export(spanData: SpanData): Promise<boolean>;

  /**
   * Export multiple spans. Override for batch optimization.
   * @param spans List of span data dictionaries
   * @returns True if all exports were successful
   */
  async exportBatch(spans: SpanData[]): Promise<boolean> {
    const results = await Promise.all(spans.map(span => this.export(span)));
    return results.every(result => result);
  }

  /**
   * Start the exporter.
   */
  start(): void {
    // Override in subclasses if needed
  }

  /**
   * Stop the exporter and flush pending data.
   */
  stop(): void {
    // Override in subclasses if needed
  }

  /**
   * Flush any buffered data.
   */
  async flush(): Promise<void> {
    // Override in subclasses if needed
  }

  /**
   * Check if the exporter is healthy.
   * @returns True if the exporter is healthy
   */
  async healthCheck(): Promise<boolean> {
    return true;
  }
}
