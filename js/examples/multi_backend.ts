/**
 * Multi-Backend Example
 * 
 * This example demonstrates how to send telemetry to multiple backends
 * simultaneously - useful for migration scenarios or redundancy.
 */

import { setupTelemetry, traceLLM, getTelemetry } from 'genai-telemetry';

// Initialize telemetry with multiple exporters
setupTelemetry({
  workflowName: 'multi-backend-app',
  exporter: [
    // Send to Splunk for real-time dashboards
    {
      type: 'splunk',
      url: process.env.SPLUNK_HEC_URL || 'http://localhost:8088',
      token: process.env.SPLUNK_HEC_TOKEN || 'test-token',
      index: 'genai_traces'
    },
    // Send to Elasticsearch for long-term storage
    {
      type: 'elasticsearch',
      hosts: [process.env.ES_HOST || 'http://localhost:9200'],
      index: 'genai-traces'
    },
    // Send to OTLP collector (can forward to Jaeger, Datadog, etc.)
    {
      type: 'otlp',
      endpoint: process.env.OTLP_ENDPOINT || 'http://localhost:4318'
    },
    // Also log to console for development
    {
      type: 'console',
      colored: true,
      verbose: false
    }
  ],
  batchSize: 10,
  flushInterval: 5
});

// Simulated LLM call
const chat = traceLLM(
  async (message: string) => {
    // Simulate API delay
    await new Promise(resolve => setTimeout(resolve, 100));
    
    return {
      choices: [{
        message: { content: `Response to: ${message}` }
      }],
      usage: {
        prompt_tokens: message.split(' ').length * 2,
        completion_tokens: 50
      }
    };
  },
  { modelName: 'gpt-4o', modelProvider: 'openai' }
);

async function main() {
  console.log('Multi-Backend Telemetry Example');
  console.log('================================\n');
  console.log('Sending traces to:');
  console.log('  - Splunk HEC');
  console.log('  - Elasticsearch');
  console.log('  - OTLP Collector');
  console.log('  - Console\n');

  // Make several calls
  for (let i = 1; i <= 5; i++) {
    console.log(`Making call ${i}...`);
    await chat(`This is test message number ${i}`);
  }

  // Manually send a custom span
  const telemetry = getTelemetry();
  await telemetry.sendSpan('TOOL', 'custom-operation', {
    durationMs: 42,
    toolName: 'example-tool',
    customField: 'custom-value'
  });

  console.log('\nDone! Traces sent to all configured backends.');
}

main().catch(console.error);
