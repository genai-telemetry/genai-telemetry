/**
 * File exporter - writes spans to a JSONL file.
 */

import { writeFileSync, appendFileSync, existsSync } from 'fs';
import type { SpanData } from '../types';
import { BaseExporter } from './base';

export interface FileExporterOptions {
  filePath?: string;
}

export class FileExporter extends BaseExporter {
  private filePath: string;
  private initialized: boolean = false;

  constructor(options: FileExporterOptions = {}) {
    super();
    this.filePath = options.filePath || 'genai_traces.jsonl';
  }

  private ensureFile(): void {
    if (!this.initialized && !existsSync(this.filePath)) {
      writeFileSync(this.filePath, '', 'utf-8');
      this.initialized = true;
    }
  }

  async export(spanData: SpanData): Promise<boolean> {
    try {
      this.ensureFile();
      const line = JSON.stringify(spanData) + '\n';
      appendFileSync(this.filePath, line, 'utf-8');
      return true;
    } catch (error) {
      console.error('FileExporter error:', error);
      return false;
    }
  }
}
