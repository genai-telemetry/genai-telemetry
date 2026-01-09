/**
 * Multi exporter - sends spans to multiple exporters.
 */

import type { SpanData } from '../types';
import { BaseExporter } from './base';

export class MultiExporter extends BaseExporter {
  private exporters: BaseExporter[];

  constructor(exporters: BaseExporter[]) {
    super();
    this.exporters = exporters;
  }

  start(): void {
    for (const exporter of this.exporters) {
      exporter.start();
    }
  }

  stop(): void {
    for (const exporter of this.exporters) {
      exporter.stop();
    }
  }

  async flush(): Promise<void> {
    await Promise.all(this.exporters.map(e => e.flush()));
  }

  async export(spanData: SpanData): Promise<boolean> {
    const results = await Promise.all(
      this.exporters.map(exporter => exporter.export(spanData))
    );
    return results.some(result => result); // Return true if at least one succeeded
  }

  async exportBatch(spans: SpanData[]): Promise<boolean> {
    const results = await Promise.all(
      this.exporters.map(exporter => exporter.exportBatch(spans))
    );
    return results.some(result => result);
  }

  async healthCheck(): Promise<boolean> {
    const results = await Promise.all(
      this.exporters.map(exporter => exporter.healthCheck())
    );
    return results.some(result => result);
  }
}
