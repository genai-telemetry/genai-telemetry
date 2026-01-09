/**
 * Console exporter - outputs spans to console for debugging.
 */

import type { SpanData } from '../types';
import { BaseExporter } from './base';

export interface ConsoleExporterOptions {
  colored?: boolean;
  verbose?: boolean;
}

export class ConsoleExporter extends BaseExporter {
  private colored: boolean;
  private verbose: boolean;

  constructor(options: ConsoleExporterOptions = {}) {
    super();
    this.colored = options.colored ?? true;
    this.verbose = options.verbose ?? false;
  }

  async export(spanData: SpanData): Promise<boolean> {
    try {
      const timestamp = spanData.timestamp;
      const spanType = spanData.span_type;
      const name = spanData.name;
      const duration = spanData.duration_ms;
      const status = spanData.status;

      if (this.colored) {
        const color = status === 'ERROR' ? '\x1b[31m' : '\x1b[32m';
        const reset = '\x1b[0m';
        const cyan = '\x1b[36m';
        const yellow = '\x1b[33m';

        console.log(
          `${cyan}[${timestamp}]${reset} ` +
          `${yellow}${spanType}${reset} ` +
          `${name} ` +
          `${color}${status}${reset} ` +
          `(${duration}ms)`
        );
      } else {
        console.log(`[${timestamp}] ${spanType} ${name} ${status} (${duration}ms)`);
      }

      if (this.verbose) {
        console.log(JSON.stringify(spanData, null, 2));
      }

      return true;
    } catch (error) {
      console.error('ConsoleExporter error:', error);
      return false;
    }
  }
}
