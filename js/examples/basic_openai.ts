/**
 * Basic OpenAI Example
 * 
 * This example demonstrates how to use genai-telemetry with OpenAI.
 * 
 * Prerequisites:
 *   npm install openai genai-telemetry
 *   export OPENAI_API_KEY=your-key
 */

import { setupTelemetry, traceLLM, traceEmbedding } from 'genai-telemetry';
import OpenAI from 'openai';

// Initialize telemetry with console output (for demo)
// In production, use Splunk, Elasticsearch, or another backend
setupTelemetry({
  workflowName: 'openai-example',
  exporter: 'console',
});

// Or use Splunk:
// setupTelemetry({
//   workflowName: 'openai-example',
//   exporter: 'splunk',
//   splunkUrl: 'http://splunk:8088',
//   splunkToken: 'your-token'
// });

const client = new OpenAI();

// Wrap the chat completion function
const chat = traceLLM(
  async (message: string) => {
    return await client.chat.completions.create({
      model: 'gpt-4o-mini',
      messages: [{ role: 'user', content: message }],
    });
  },
  { modelName: 'gpt-4o-mini', modelProvider: 'openai' }
);

// Wrap the embedding function
const embed = traceEmbedding(
  async (text: string) => {
    return await client.embeddings.create({
      model: 'text-embedding-3-small',
      input: text,
    });
  },
  { model: 'text-embedding-3-small' }
);

// Main function
async function main() {
  console.log('Starting OpenAI example...\n');

  // Chat completion
  console.log('1. Chat Completion:');
  const chatResponse = await chat('What is the capital of France?');
  console.log('Response:', chatResponse.choices[0].message.content);
  console.log('');

  // Embedding
  console.log('2. Embedding:');
  const embeddingResponse = await embed('Hello, world!');
  console.log('Embedding dimensions:', embeddingResponse.data[0].embedding.length);
  console.log('');

  // Multiple calls to show tracing
  console.log('3. Multiple calls:');
  const questions = [
    'What is 2+2?',
    'Who wrote Romeo and Juliet?',
    'What is the speed of light?',
  ];

  for (const question of questions) {
    const response = await chat(question);
    console.log(`Q: ${question}`);
    console.log(`A: ${response.choices[0].message.content}\n`);
  }

  console.log('Done! Check your telemetry backend for traces.');
}

main().catch(console.error);
