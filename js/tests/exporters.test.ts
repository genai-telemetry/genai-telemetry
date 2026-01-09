/**
 * Tests for telemetry exporters
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  ConsoleExporter,
  FileExporter,
  SplunkHECExporter,
  ElasticsearchExporter,
  OTLPExporter,
  MultiExporter,
} from '../src/exporters';
import type { SpanData } from '../src/types';
import { existsSync, unlinkSync, readFileSync } from 'fs';

const mockSpan: SpanData = {
  trace_id: 'abc123def456abc123def456abc12345',
  span_id: 'abc123def4567890',
  name: 'test-span',
  span_type: 'LLM',
  workflow_name: 'test-workflow',
  timestamp: new Date().toISOString(),
  duration_ms: 100,
  status: 'OK',
  is_error: 0,
  model_name: 'gpt-4o',
  model_provider: 'openai',
  input_tokens: 50,
  output_tokens: 25,
};

describe('ConsoleExporter', () => {
  it('should export spans to console', async () => {
    const consoleSpy = vi.spyOn(console, 'log').mockImplementation(() => {});
    const exporter = new ConsoleExporter();
    
    const result = await exporter.export(mockSpan);
    
    expect(result).toBe(true);
    expect(consoleSpy).toHaveBeenCalled();
    
    consoleSpy.mockRestore();
  });

  it('should support colored output', async () => {
    const consoleSpy = vi.spyOn(console, 'log').mockImplementation(() => {});
    const exporter = new ConsoleExporter({ colored: true });
    
    await exporter.export(mockSpan);
    
    const output = consoleSpy.mock.calls[0][0] as string;
    expect(output).toContain('\x1b['); // ANSI color codes
    
    consoleSpy.mockRestore();
  });

  it('should support verbose output', async () => {
    const consoleSpy = vi.spyOn(console, 'log').mockImplementation(() => {});
    const exporter = new ConsoleExporter({ verbose: true });
    
    await exporter.export(mockSpan);
    
    // Verbose mode logs twice: summary and JSON
    expect(consoleSpy).toHaveBeenCalledTimes(2);
    
    consoleSpy.mockRestore();
  });
});

describe('FileExporter', () => {
  const testFile = '/tmp/test_traces.jsonl';

  afterEach(() => {
    if (existsSync(testFile)) {
      unlinkSync(testFile);
    }
  });

  it('should export spans to file', async () => {
    const exporter = new FileExporter({ filePath: testFile });
    
    const result = await exporter.export(mockSpan);
    
    expect(result).toBe(true);
    expect(existsSync(testFile)).toBe(true);
    
    const content = readFileSync(testFile, 'utf-8');
    const parsed = JSON.parse(content.trim());
    expect(parsed.trace_id).toBe(mockSpan.trace_id);
  });

  it('should append multiple spans', async () => {
    const exporter = new FileExporter({ filePath: testFile });
    
    await exporter.export(mockSpan);
    await exporter.export({ ...mockSpan, span_id: 'different123456' });
    
    const content = readFileSync(testFile, 'utf-8');
    const lines = content.trim().split('\n');
    expect(lines.length).toBe(2);
  });
});

describe('SplunkHECExporter', () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = vi.fn().mockResolvedValue({ ok: true });
    global.fetch = fetchMock;
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should construct HEC URL correctly', () => {
    const exporter = new SplunkHECExporter({
      hecUrl: 'http://splunk:8088',
      hecToken: 'test-token',
    });

    // The URL should include the collector endpoint
    // We can't directly access private properties, but we can test via export
  });

  it('should export spans to Splunk HEC', async () => {
    const exporter = new SplunkHECExporter({
      hecUrl: 'http://splunk:8088',
      hecToken: 'test-token',
    });
    exporter.start();

    const result = await exporter.export(mockSpan);

    expect(result).toBe(true);
    expect(fetchMock).toHaveBeenCalledWith(
      'http://splunk:8088/services/collector/event',
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({
          Authorization: 'Splunk test-token',
        }),
      })
    );

    exporter.stop();
  });

  it('should batch spans when batchSize > 1', async () => {
    const exporter = new SplunkHECExporter({
      hecUrl: 'http://splunk:8088',
      hecToken: 'test-token',
      batchSize: 5,
    });
    exporter.start();

    // Send 3 spans (less than batch size)
    await exporter.export(mockSpan);
    await exporter.export(mockSpan);
    await exporter.export(mockSpan);

    // Should not have called fetch yet
    expect(fetchMock).not.toHaveBeenCalled();

    // Flush manually
    await exporter.flush();
    expect(fetchMock).toHaveBeenCalledTimes(1);

    exporter.stop();
  });

  it('should handle API errors', async () => {
    fetchMock.mockResolvedValue({ ok: false, status: 500 });
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    const exporter = new SplunkHECExporter({
      hecUrl: 'http://splunk:8088',
      hecToken: 'test-token',
    });

    const result = await exporter.export(mockSpan);

    expect(result).toBe(false);

    consoleSpy.mockRestore();
  });
});

describe('ElasticsearchExporter', () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = vi.fn().mockResolvedValue({ 
      ok: true, 
      json: () => Promise.resolve({ errors: false }) 
    });
    global.fetch = fetchMock;
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should export spans to Elasticsearch', async () => {
    const exporter = new ElasticsearchExporter({
      hosts: ['http://localhost:9200'],
      index: 'genai-traces',
    });
    exporter.start();

    const result = await exporter.export(mockSpan);

    expect(result).toBe(true);
    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:9200/_bulk',
      expect.objectContaining({
        method: 'POST',
      })
    );

    exporter.stop();
  });

  it('should use API key authentication', async () => {
    const exporter = new ElasticsearchExporter({
      hosts: ['http://localhost:9200'],
      apiKey: 'test-api-key',
    });

    await exporter.export(mockSpan);

    expect(fetchMock).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: 'ApiKey test-api-key',
        }),
      })
    );
  });

  it('should use basic authentication', async () => {
    const exporter = new ElasticsearchExporter({
      hosts: ['http://localhost:9200'],
      username: 'elastic',
      password: 'changeme',
    });

    await exporter.export(mockSpan);

    const expectedAuth = Buffer.from('elastic:changeme').toString('base64');
    expect(fetchMock).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: `Basic ${expectedAuth}`,
        }),
      })
    );
  });
});

describe('OTLPExporter', () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = vi.fn().mockResolvedValue({ ok: true });
    global.fetch = fetchMock;
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should export spans in OTLP format', async () => {
    const exporter = new OTLPExporter({
      endpoint: 'http://localhost:4318',
      serviceName: 'test-service',
    });
    exporter.start();

    const result = await exporter.export(mockSpan);

    expect(result).toBe(true);
    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:4318/v1/traces',
      expect.objectContaining({
        method: 'POST',
        body: expect.stringContaining('resourceSpans'),
      })
    );

    exporter.stop();
  });

  it('should include custom headers', async () => {
    const exporter = new OTLPExporter({
      endpoint: 'http://localhost:4318',
      headers: { 'X-Custom-Header': 'test-value' },
    });

    await exporter.export(mockSpan);

    expect(fetchMock).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        headers: expect.objectContaining({
          'X-Custom-Header': 'test-value',
        }),
      })
    );
  });
});

describe('MultiExporter', () => {
  it('should export to all exporters', async () => {
    const exporter1 = new ConsoleExporter();
    const exporter2 = new ConsoleExporter();
    
    const export1Spy = vi.spyOn(exporter1, 'export');
    const export2Spy = vi.spyOn(exporter2, 'export');
    vi.spyOn(console, 'log').mockImplementation(() => {});

    const multi = new MultiExporter([exporter1, exporter2]);
    
    await multi.export(mockSpan);

    expect(export1Spy).toHaveBeenCalledWith(mockSpan);
    expect(export2Spy).toHaveBeenCalledWith(mockSpan);
  });

  it('should start all exporters', () => {
    const exporter1 = new ConsoleExporter();
    const exporter2 = new ConsoleExporter();
    
    const start1Spy = vi.spyOn(exporter1, 'start');
    const start2Spy = vi.spyOn(exporter2, 'start');

    const multi = new MultiExporter([exporter1, exporter2]);
    multi.start();

    expect(start1Spy).toHaveBeenCalled();
    expect(start2Spy).toHaveBeenCalled();
  });

  it('should return true if at least one exporter succeeds', async () => {
    const successExporter = new ConsoleExporter();
    const failExporter = new ConsoleExporter();
    
    vi.spyOn(successExporter, 'export').mockResolvedValue(true);
    vi.spyOn(failExporter, 'export').mockResolvedValue(false);

    const multi = new MultiExporter([successExporter, failExporter]);
    const result = await multi.export(mockSpan);

    expect(result).toBe(true);
  });

  it('should return false if all exporters fail', async () => {
    const exporter1 = new ConsoleExporter();
    const exporter2 = new ConsoleExporter();
    
    vi.spyOn(exporter1, 'export').mockResolvedValue(false);
    vi.spyOn(exporter2, 'export').mockResolvedValue(false);

    const multi = new MultiExporter([exporter1, exporter2]);
    const result = await multi.export(mockSpan);

    expect(result).toBe(false);
  });
});
