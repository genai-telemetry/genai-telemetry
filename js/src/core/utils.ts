/**
 * Utility functions for GenAI Telemetry
 */

import type { LLMResponse } from './types';

/**
 * Extract token usage from LLM response.
 * Supports OpenAI, Anthropic, and other common formats.
 */
export function extractTokensFromResponse(response: LLMResponse): [number, number] {
  if (!response || typeof response !== 'object') {
    return [0, 0];
  }

  const resp = response as Record<string, unknown>;

  // Check for usage object (OpenAI, Anthropic, etc.)
  if (resp.usage && typeof resp.usage === 'object') {
    const usage = resp.usage as Record<string, unknown>;

    // OpenAI format
    if ('prompt_tokens' in usage || 'completion_tokens' in usage) {
      const inputTokens = (usage.prompt_tokens as number) || 0;
      const outputTokens = (usage.completion_tokens as number) || 0;
      return [inputTokens, outputTokens];
    }

    // Anthropic format
    if ('input_tokens' in usage || 'output_tokens' in usage) {
      const inputTokens = (usage.input_tokens as number) || 0;
      const outputTokens = (usage.output_tokens as number) || 0;
      return [inputTokens, outputTokens];
    }

    // Generic total_tokens format
    if ('total_tokens' in usage) {
      const total = (usage.total_tokens as number) || 0;
      return [Math.floor(total / 2), Math.ceil(total / 2)];
    }
  }

  // Check for response_metadata (LangChain format)
  if (resp.response_metadata && typeof resp.response_metadata === 'object') {
    const metadata = resp.response_metadata as Record<string, unknown>;
    if (metadata.token_usage && typeof metadata.token_usage === 'object') {
      const tokenUsage = metadata.token_usage as Record<string, unknown>;
      const inputTokens = (tokenUsage.prompt_tokens as number) || 
                          (tokenUsage.input_tokens as number) || 0;
      const outputTokens = (tokenUsage.completion_tokens as number) || 
                           (tokenUsage.output_tokens as number) || 0;
      return [inputTokens, outputTokens];
    }
  }

  return [0, 0];
}

/**
 * Extract content from LLM response.
 * Supports OpenAI, Anthropic, and other common formats.
 */
export function extractContentFromResponse(
  response: LLMResponse, 
  provider: string = 'openai'
): string {
  if (!response || typeof response !== 'object') {
    return String(response || '');
  }

  const resp = response as Record<string, unknown>;

  // If response is already a string, return it
  if (typeof response === 'string') {
    return response;
  }

  // Anthropic format
  if (provider.toLowerCase() === 'anthropic' || 
      provider.toLowerCase() === 'claude') {
    if (Array.isArray(resp.content)) {
      const textBlocks = resp.content.filter(
        (block: unknown) => 
          typeof block === 'object' && 
          block !== null && 
          (block as Record<string, unknown>).type === 'text'
      );
      if (textBlocks.length > 0) {
        return textBlocks
          .map((block: unknown) => (block as Record<string, unknown>).text)
          .join('');
      }
    }
    // Simple content field
    if (typeof resp.content === 'string') {
      return resp.content;
    }
  }

  // OpenAI format (and most others)
  if (Array.isArray(resp.choices) && resp.choices.length > 0) {
    const choice = resp.choices[0] as Record<string, unknown>;
    
    // Chat completion format
    if (choice.message && typeof choice.message === 'object') {
      const message = choice.message as Record<string, unknown>;
      if (typeof message.content === 'string') {
        return message.content;
      }
    }
    
    // Text completion format
    if (typeof choice.text === 'string') {
      return choice.text;
    }
  }

  // LangChain AIMessage format
  if (typeof resp.content === 'string') {
    return resp.content;
  }

  // Fallback: try to stringify
  try {
    return JSON.stringify(response);
  } catch {
    return String(response);
  }
}

/**
 * Generate a random hex string of specified length.
 */
export function randomHex(length: number): string {
  const chars = '0123456789abcdef';
  let result = '';
  for (let i = 0; i < length; i++) {
    result += chars[Math.floor(Math.random() * chars.length)];
  }
  return result;
}

/**
 * Generate a new trace ID (32 hex characters).
 */
export function generateTraceId(): string {
  return randomHex(32);
}

/**
 * Generate a new span ID (16 hex characters).
 */
export function generateSpanId(): string {
  return randomHex(16);
}

/**
 * Get current timestamp in ISO format.
 */
export function getTimestamp(): string {
  return new Date().toISOString();
}

/**
 * Deep clone an object.
 */
export function deepClone<T>(obj: T): T {
  return JSON.parse(JSON.stringify(obj));
}

/**
 * Sleep for a specified number of milliseconds.
 */
export function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}
