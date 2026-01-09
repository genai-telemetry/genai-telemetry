/**
 * Decorators and wrapper functions for tracing LLM operations.
 */

import type { LLMResponse } from '../types';
import { getTelemetry } from './telemetry';
import { extractTokensFromResponse, extractContentFromResponse } from './utils';

/**
 * Wrapper for tracing LLM calls.
 * 
 * @example
 * ```typescript
 * const tracedChat = traceLLM(
 *   async (message: string) => {
 *     return await client.chat.completions.create({
 *       model: 'gpt-4o',
 *       messages: [{ role: 'user', content: message }]
 *     });
 *   },
 *   { modelName: 'gpt-4o', modelProvider: 'openai' }
 * );
 * 
 * const response = await tracedChat('Hello!');
 * ```
 */
export function traceLLM<T extends (...args: unknown[]) => Promise<LLMResponse>>(
  fn: T,
  options: {
    modelName: string;
    modelProvider?: string;
    extractContent?: boolean;
  }
): T {
  const { modelName, modelProvider = 'openai', extractContent = false } = options;

  const wrapped = async (...args: Parameters<T>): Promise<ReturnType<T> | string> => {
    const telemetry = getTelemetry();
    const start = Date.now();

    try {
      const result = await fn(...args);
      const duration = Date.now() - start;

      const [inputTokens, outputTokens] = extractTokensFromResponse(result);

      await telemetry.sendSpan('LLM', fn.name || 'llm_call', {
        modelName,
        modelProvider,
        durationMs: duration,
        inputTokens,
        outputTokens,
      });

      if (extractContent) {
        return extractContentFromResponse(result, modelProvider);
      }

      return result as ReturnType<T>;
    } catch (error) {
      const duration = Date.now() - start;

      await telemetry.sendSpan('LLM', fn.name || 'llm_call', {
        modelName,
        modelProvider,
        durationMs: duration,
        status: 'ERROR',
        isError: 1,
        errorMessage: (error as Error).message,
        errorType: (error as Error).name,
      });

      throw error;
    }
  };

  return wrapped as T;
}

/**
 * Wrapper for tracing embedding calls.
 */
export function traceEmbedding<T extends (...args: unknown[]) => Promise<unknown>>(
  fn: T,
  options: { model: string }
): T {
  const { model } = options;

  const wrapped = async (...args: Parameters<T>): Promise<ReturnType<T>> => {
    const telemetry = getTelemetry();
    const start = Date.now();

    try {
      const result = await fn(...args);
      const duration = Date.now() - start;

      let inputTokens = 0;
      if (result && typeof result === 'object') {
        const resp = result as Record<string, unknown>;
        if (resp.usage && typeof resp.usage === 'object') {
          const usage = resp.usage as Record<string, unknown>;
          inputTokens = (usage.prompt_tokens as number) || (usage.total_tokens as number) || 0;
        }
      }

      await telemetry.sendSpan('EMBEDDING', fn.name || 'embedding', {
        embeddingModel: model,
        durationMs: duration,
        inputTokens,
      });

      return result as ReturnType<T>;
    } catch (error) {
      const duration = Date.now() - start;

      await telemetry.sendSpan('EMBEDDING', fn.name || 'embedding', {
        embeddingModel: model,
        durationMs: duration,
        status: 'ERROR',
        isError: 1,
        errorMessage: (error as Error).message,
      });

      throw error;
    }
  };

  return wrapped as T;
}

/**
 * Wrapper for tracing retrieval calls.
 */
export function traceRetrieval<T extends (...args: unknown[]) => Promise<unknown[]>>(
  fn: T,
  options: { vectorStore: string; embeddingModel?: string }
): T {
  const { vectorStore, embeddingModel } = options;

  const wrapped = async (...args: Parameters<T>): Promise<ReturnType<T>> => {
    const telemetry = getTelemetry();
    const start = Date.now();

    try {
      const result = await fn(...args);
      const duration = Date.now() - start;

      const docsCount = Array.isArray(result) ? result.length : 0;

      await telemetry.sendSpan('RETRIEVER', fn.name || 'retrieval', {
        vectorStore,
        embeddingModel,
        documentsRetrieved: docsCount,
        durationMs: duration,
      });

      return result as ReturnType<T>;
    } catch (error) {
      const duration = Date.now() - start;

      await telemetry.sendSpan('RETRIEVER', fn.name || 'retrieval', {
        vectorStore,
        durationMs: duration,
        status: 'ERROR',
        isError: 1,
        errorMessage: (error as Error).message,
      });

      throw error;
    }
  };

  return wrapped as T;
}

/**
 * Wrapper for tracing tool calls.
 */
export function traceTool<T extends (...args: unknown[]) => Promise<unknown>>(
  fn: T,
  options: { toolName: string }
): T {
  const { toolName } = options;

  const wrapped = async (...args: Parameters<T>): Promise<ReturnType<T>> => {
    const telemetry = getTelemetry();
    const start = Date.now();

    try {
      const result = await fn(...args);
      const duration = Date.now() - start;

      await telemetry.sendSpan('TOOL', fn.name || 'tool_call', {
        toolName,
        durationMs: duration,
      });

      return result as ReturnType<T>;
    } catch (error) {
      const duration = Date.now() - start;

      await telemetry.sendSpan('TOOL', fn.name || 'tool_call', {
        toolName,
        durationMs: duration,
        status: 'ERROR',
        isError: 1,
        errorMessage: (error as Error).message,
      });

      throw error;
    }
  };

  return wrapped as T;
}

/**
 * Wrapper for tracing chain/pipeline calls.
 */
export function traceChain<T extends (...args: unknown[]) => Promise<unknown>>(
  fn: T,
  options: { name: string }
): T {
  const { name } = options;

  const wrapped = async (...args: Parameters<T>): Promise<ReturnType<T>> => {
    const telemetry = getTelemetry();
    telemetry.newTrace();
    const start = Date.now();

    try {
      const result = await fn(...args);
      const duration = Date.now() - start;

      await telemetry.sendSpan('CHAIN', name, {
        durationMs: duration,
      });

      return result as ReturnType<T>;
    } catch (error) {
      const duration = Date.now() - start;

      await telemetry.sendSpan('CHAIN', name, {
        durationMs: duration,
        status: 'ERROR',
        isError: 1,
        errorMessage: (error as Error).message,
      });

      throw error;
    }
  };

  return wrapped as T;
}

/**
 * Wrapper for tracing agent calls.
 */
export function traceAgent<T extends (...args: unknown[]) => Promise<unknown>>(
  fn: T,
  options: { agentName: string; agentType?: string }
): T {
  const { agentName, agentType } = options;

  const wrapped = async (...args: Parameters<T>): Promise<ReturnType<T>> => {
    const telemetry = getTelemetry();
    telemetry.newTrace();
    const start = Date.now();

    try {
      const result = await fn(...args);
      const duration = Date.now() - start;

      await telemetry.sendSpan('AGENT', fn.name || 'agent', {
        agentName,
        agentType,
        durationMs: duration,
      });

      return result as ReturnType<T>;
    } catch (error) {
      const duration = Date.now() - start;

      await telemetry.sendSpan('AGENT', fn.name || 'agent', {
        agentName,
        agentType,
        durationMs: duration,
        status: 'ERROR',
        isError: 1,
        errorMessage: (error as Error).message,
      });

      throw error;
    }
  };

  return wrapped as T;
}

// ============================================================================
// TypeScript Decorators (for class methods)
// ============================================================================

/**
 * Decorator for tracing LLM calls on class methods.
 * 
 * @example
 * ```typescript
 * class ChatService {
 *   @TraceLLM({ modelName: 'gpt-4o', modelProvider: 'openai' })
 *   async chat(message: string) {
 *     return await this.client.chat.completions.create({...});
 *   }
 * }
 * ```
 */
export function TraceLLM(options: {
  modelName: string;
  modelProvider?: string;
  extractContent?: boolean;
}) {
  return function (
    _target: unknown,
    _propertyKey: string,
    descriptor: PropertyDescriptor
  ) {
    const originalMethod = descriptor.value;
    descriptor.value = traceLLM(originalMethod, options);
    return descriptor;
  };
}

/**
 * Decorator for tracing embedding calls on class methods.
 */
export function TraceEmbedding(options: { model: string }) {
  return function (
    _target: unknown,
    _propertyKey: string,
    descriptor: PropertyDescriptor
  ) {
    const originalMethod = descriptor.value;
    descriptor.value = traceEmbedding(originalMethod, options);
    return descriptor;
  };
}

/**
 * Decorator for tracing retrieval calls on class methods.
 */
export function TraceRetrieval(options: { vectorStore: string; embeddingModel?: string }) {
  return function (
    _target: unknown,
    _propertyKey: string,
    descriptor: PropertyDescriptor
  ) {
    const originalMethod = descriptor.value;
    descriptor.value = traceRetrieval(originalMethod, options);
    return descriptor;
  };
}

/**
 * Decorator for tracing tool calls on class methods.
 */
export function TraceTool(options: { toolName: string }) {
  return function (
    _target: unknown,
    _propertyKey: string,
    descriptor: PropertyDescriptor
  ) {
    const originalMethod = descriptor.value;
    descriptor.value = traceTool(originalMethod, options);
    return descriptor;
  };
}

/**
 * Decorator for tracing chain calls on class methods.
 */
export function TraceChain(options: { name: string }) {
  return function (
    _target: unknown,
    _propertyKey: string,
    descriptor: PropertyDescriptor
  ) {
    const originalMethod = descriptor.value;
    descriptor.value = traceChain(originalMethod, options);
    return descriptor;
  };
}

/**
 * Decorator for tracing agent calls on class methods.
 */
export function TraceAgent(options: { agentName: string; agentType?: string }) {
  return function (
    _target: unknown,
    _propertyKey: string,
    descriptor: PropertyDescriptor
  ) {
    const originalMethod = descriptor.value;
    descriptor.value = traceAgent(originalMethod, options);
    return descriptor;
  };
}
