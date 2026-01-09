/**
 * Tests for core telemetry functionality
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  setupTelemetry,
  getTelemetry,
  GenAITelemetry,
  Span,
  traceLLM,
  traceEmbedding,
  traceRetrieval,
  extractTokensFromResponse,
  extractContentFromResponse,
} from '../src';
import { ConsoleExporter } from '../src/exporters';

describe('GenAITelemetry', () => {
  beforeEach(() => {
    // Reset global telemetry instance
    setupTelemetry({
      workflowName: 'test-workflow',
      exporter: 'console',
    });
  });

  describe('setupTelemetry', () => {
    it('should create a telemetry instance', () => {
      const telemetry = setupTelemetry({
        workflowName: 'my-app',
        exporter: 'console',
      });

      expect(telemetry).toBeInstanceOf(GenAITelemetry);
      expect(telemetry.workflowName).toBe('my-app');
    });

    it('should use console exporter by default', () => {
      const telemetry = setupTelemetry({
        workflowName: 'my-app',
      });

      expect(telemetry.exporter).toBeInstanceOf(ConsoleExporter);
    });

    it('should support custom service name', () => {
      const telemetry = setupTelemetry({
        workflowName: 'my-app',
        serviceName: 'custom-service',
        exporter: 'console',
      });

      expect(telemetry.serviceName).toBe('custom-service');
    });
  });

  describe('getTelemetry', () => {
    it('should return the telemetry instance after setup', () => {
      setupTelemetry({ workflowName: 'test', exporter: 'console' });
      const telemetry = getTelemetry();
      expect(telemetry).toBeInstanceOf(GenAITelemetry);
    });
  });

  describe('traceId', () => {
    it('should generate a trace ID', () => {
      const telemetry = getTelemetry();
      const traceId = telemetry.traceId;
      expect(traceId).toBeDefined();
      expect(traceId.length).toBe(32);
    });

    it('should generate a new trace ID on newTrace()', () => {
      const telemetry = getTelemetry();
      const oldTraceId = telemetry.traceId;
      const newTraceId = telemetry.newTrace();
      expect(newTraceId).not.toBe(oldTraceId);
      expect(newTraceId.length).toBe(32);
    });
  });

  describe('sendSpan', () => {
    it('should send a span with correct data', async () => {
      const telemetry = getTelemetry();
      const exportSpy = vi.spyOn(telemetry.exporter, 'export');

      await telemetry.sendSpan('LLM', 'test-call', {
        modelName: 'gpt-4o',
        modelProvider: 'openai',
        durationMs: 100,
        inputTokens: 50,
        outputTokens: 25,
      });

      expect(exportSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          span_type: 'LLM',
          name: 'test-call',
          model_name: 'gpt-4o',
          model_provider: 'openai',
          duration_ms: 100,
          input_tokens: 50,
          output_tokens: 25,
          total_tokens: 75,
        })
      );
    });
  });
});

describe('Span', () => {
  it('should create a span with correct properties', () => {
    const span = new Span({
      traceId: 'abc123',
      spanId: 'def456',
      name: 'test-span',
      spanType: 'LLM',
      workflowName: 'test-workflow',
    });

    expect(span.traceId).toBe('abc123');
    expect(span.spanId).toBe('def456');
    expect(span.name).toBe('test-span');
    expect(span.spanType).toBe('LLM');
    expect(span.status).toBe('OK');
    expect(span.isError).toBe(0);
  });

  it('should finish and calculate duration', () => {
    const span = new Span({
      traceId: 'abc123',
      spanId: 'def456',
      name: 'test-span',
      spanType: 'LLM',
    });

    span.finish();

    expect(span.durationMs).toBeDefined();
    expect(span.durationMs).toBeGreaterThanOrEqual(0);
  });

  it('should set error correctly', () => {
    const span = new Span({
      traceId: 'abc123',
      spanId: 'def456',
      name: 'test-span',
      spanType: 'LLM',
    });

    span.setError(new Error('Test error'));

    expect(span.status).toBe('ERROR');
    expect(span.isError).toBe(1);
    expect(span.errorMessage).toBe('Test error');
    expect(span.errorType).toBe('Error');
  });

  it('should convert to dict correctly', () => {
    const span = new Span({
      traceId: 'abc123',
      spanId: 'def456',
      name: 'test-span',
      spanType: 'LLM',
      workflowName: 'test-workflow',
      modelName: 'gpt-4o',
      modelProvider: 'openai',
      inputTokens: 100,
      outputTokens: 50,
    });

    span.finish();
    const dict = span.toDict();

    expect(dict.trace_id).toBe('abc123');
    expect(dict.span_id).toBe('def456');
    expect(dict.name).toBe('test-span');
    expect(dict.span_type).toBe('LLM');
    expect(dict.workflow_name).toBe('test-workflow');
    expect(dict.model_name).toBe('gpt-4o');
    expect(dict.model_provider).toBe('openai');
    expect(dict.input_tokens).toBe(100);
    expect(dict.output_tokens).toBe(50);
    expect(dict.timestamp).toBeDefined();
    expect(dict.duration_ms).toBeGreaterThanOrEqual(0);
  });
});

describe('extractTokensFromResponse', () => {
  it('should extract tokens from OpenAI format', () => {
    const response = {
      usage: {
        prompt_tokens: 100,
        completion_tokens: 50,
      },
    };

    const [input, output] = extractTokensFromResponse(response);
    expect(input).toBe(100);
    expect(output).toBe(50);
  });

  it('should extract tokens from Anthropic format', () => {
    const response = {
      usage: {
        input_tokens: 100,
        output_tokens: 50,
      },
    };

    const [input, output] = extractTokensFromResponse(response);
    expect(input).toBe(100);
    expect(output).toBe(50);
  });

  it('should return zeros for missing usage', () => {
    const [input, output] = extractTokensFromResponse({});
    expect(input).toBe(0);
    expect(output).toBe(0);
  });

  it('should handle null/undefined', () => {
    const [input1, output1] = extractTokensFromResponse(null);
    const [input2, output2] = extractTokensFromResponse(undefined);
    
    expect(input1).toBe(0);
    expect(output1).toBe(0);
    expect(input2).toBe(0);
    expect(output2).toBe(0);
  });
});

describe('extractContentFromResponse', () => {
  it('should extract content from OpenAI format', () => {
    const response = {
      choices: [{ message: { content: 'Hello, world!' } }],
    };

    const content = extractContentFromResponse(response, 'openai');
    expect(content).toBe('Hello, world!');
  });

  it('should extract content from Anthropic format', () => {
    const response = {
      content: [{ type: 'text', text: 'Hello from Claude!' }],
    };

    const content = extractContentFromResponse(response, 'anthropic');
    expect(content).toBe('Hello from Claude!');
  });

  it('should handle string response', () => {
    const content = extractContentFromResponse('Just a string', 'openai');
    expect(content).toBe('Just a string');
  });
});

describe('traceLLM', () => {
  beforeEach(() => {
    setupTelemetry({
      workflowName: 'test-workflow',
      exporter: 'console',
    });
  });

  it('should trace successful LLM calls', async () => {
    const telemetry = getTelemetry();
    const exportSpy = vi.spyOn(telemetry.exporter, 'export');

    const mockLLM = traceLLM(
      async (message: string) => ({
        choices: [{ message: { content: `Echo: ${message}` } }],
        usage: { prompt_tokens: 10, completion_tokens: 5 },
      }),
      { modelName: 'test-model', modelProvider: 'test' }
    );

    const result = await mockLLM('Hello');

    expect(result.choices[0].message.content).toBe('Echo: Hello');
    expect(exportSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        span_type: 'LLM',
        model_name: 'test-model',
        model_provider: 'test',
        input_tokens: 10,
        output_tokens: 5,
        status: 'OK',
      })
    );
  });

  it('should trace errors', async () => {
    const telemetry = getTelemetry();
    const exportSpy = vi.spyOn(telemetry.exporter, 'export');

    const mockLLM = traceLLM(
      async () => {
        throw new Error('API Error');
      },
      { modelName: 'test-model', modelProvider: 'test' }
    );

    await expect(mockLLM('Hello')).rejects.toThrow('API Error');

    expect(exportSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        span_type: 'LLM',
        status: 'ERROR',
        is_error: 1,
        error_message: 'API Error',
      })
    );
  });
});

describe('traceEmbedding', () => {
  beforeEach(() => {
    setupTelemetry({
      workflowName: 'test-workflow',
      exporter: 'console',
    });
  });

  it('should trace embedding calls', async () => {
    const telemetry = getTelemetry();
    const exportSpy = vi.spyOn(telemetry.exporter, 'export');

    const mockEmbed = traceEmbedding(
      async (text: string) => ({
        data: [{ embedding: [0.1, 0.2, 0.3] }],
        usage: { prompt_tokens: text.length },
      }),
      { model: 'text-embedding-3-small' }
    );

    await mockEmbed('Hello');

    expect(exportSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        span_type: 'EMBEDDING',
        embedding_model: 'text-embedding-3-small',
      })
    );
  });
});

describe('traceRetrieval', () => {
  beforeEach(() => {
    setupTelemetry({
      workflowName: 'test-workflow',
      exporter: 'console',
    });
  });

  it('should trace retrieval calls', async () => {
    const telemetry = getTelemetry();
    const exportSpy = vi.spyOn(telemetry.exporter, 'export');

    const mockSearch = traceRetrieval(
      async () => [{ id: 1, content: 'doc1' }, { id: 2, content: 'doc2' }],
      { vectorStore: 'pinecone', embeddingModel: 'text-embedding-3-small' }
    );

    const results = await mockSearch('query');

    expect(results.length).toBe(2);
    expect(exportSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        span_type: 'RETRIEVER',
        vector_store: 'pinecone',
        documents_retrieved: 2,
      })
    );
  });
});
