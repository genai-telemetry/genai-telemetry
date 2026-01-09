/**
 * RAG Pipeline Example
 * 
 * This example demonstrates how to trace a complete RAG pipeline
 * including embeddings, retrieval, and LLM calls.
 */

import { 
  setupTelemetry, 
  traceLLM, 
  traceEmbedding, 
  traceRetrieval,
  traceChain,
  getTelemetry
} from 'genai-telemetry';

// Initialize telemetry
setupTelemetry({
  workflowName: 'rag-pipeline',
  exporter: 'console',
  // Or use multiple exporters:
  // exporter: [
  //   { type: 'splunk', url: 'http://splunk:8088', token: 'xxx' },
  //   { type: 'console' }
  // ]
});

// Simulated vector store
const documents = [
  { id: 1, content: 'Paris is the capital of France.', embedding: [] },
  { id: 2, content: 'London is the capital of the United Kingdom.', embedding: [] },
  { id: 3, content: 'Tokyo is the capital of Japan.', embedding: [] },
  { id: 4, content: 'The Eiffel Tower is located in Paris.', embedding: [] },
  { id: 5, content: 'Big Ben is a famous clock tower in London.', embedding: [] },
];

// Simulated embedding function
const generateEmbedding = traceEmbedding(
  async (text: string): Promise<{ data: [{ embedding: number[] }], usage: { total_tokens: number } }> => {
    // Simulate API delay
    await new Promise(resolve => setTimeout(resolve, 50));
    
    // Return mock embedding
    return {
      data: [{ embedding: Array(1536).fill(0).map(() => Math.random()) }],
      usage: { total_tokens: text.split(' ').length }
    };
  },
  { model: 'text-embedding-3-small' }
);

// Simulated vector search
const searchDocuments = traceRetrieval(
  async (query: string): Promise<typeof documents> => {
    // Simulate search delay
    await new Promise(resolve => setTimeout(resolve, 100));
    
    // Simple keyword search (in real app, use vector similarity)
    const keywords = query.toLowerCase().split(' ');
    const results = documents.filter(doc => 
      keywords.some(kw => doc.content.toLowerCase().includes(kw))
    );
    
    return results.slice(0, 3);
  },
  { vectorStore: 'in-memory', embeddingModel: 'text-embedding-3-small' }
);

// Simulated LLM call
const generateAnswer = traceLLM(
  async (prompt: string): Promise<{
    choices: [{ message: { content: string } }],
    usage: { prompt_tokens: number, completion_tokens: number }
  }> => {
    // Simulate API delay
    await new Promise(resolve => setTimeout(resolve, 200));
    
    // Mock response
    return {
      choices: [{
        message: {
          content: `Based on the context provided, here is my answer: ${prompt.slice(0, 100)}...`
        }
      }],
      usage: {
        prompt_tokens: prompt.split(' ').length,
        completion_tokens: 50
      }
    };
  },
  { modelName: 'gpt-4o', modelProvider: 'openai' }
);

// Complete RAG pipeline
const ragPipeline = traceChain(
  async (question: string): Promise<string> => {
    const telemetry = getTelemetry();
    
    console.log(`\nProcessing question: ${question}`);
    
    // Step 1: Generate embedding for the query
    console.log('1. Generating query embedding...');
    await generateEmbedding(question);
    
    // Step 2: Search for relevant documents
    console.log('2. Searching for relevant documents...');
    const relevantDocs = await searchDocuments(question);
    console.log(`   Found ${relevantDocs.length} relevant documents`);
    
    // Step 3: Build context from retrieved documents
    const context = relevantDocs.map(doc => doc.content).join('\n');
    
    // Step 4: Generate answer using LLM
    console.log('3. Generating answer...');
    const prompt = `Context:\n${context}\n\nQuestion: ${question}\n\nAnswer:`;
    const response = await generateAnswer(prompt);
    
    return response.choices[0].message.content;
  },
  { name: 'rag-qa-pipeline' }
);

// Main function
async function main() {
  console.log('='.repeat(60));
  console.log('RAG Pipeline Example');
  console.log('='.repeat(60));

  const questions = [
    'What is the capital of France?',
    'Tell me about famous landmarks in London.',
    'What do you know about Tokyo?',
  ];

  for (const question of questions) {
    console.log('\n' + '-'.repeat(60));
    const answer = await ragPipeline(question);
    console.log('\nAnswer:', answer);
  }

  console.log('\n' + '='.repeat(60));
  console.log('Done! Check your telemetry backend for the complete trace.');
}

main().catch(console.error);
