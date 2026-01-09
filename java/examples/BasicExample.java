package io.github.genaitelemetry.examples;

import io.github.genaitelemetry.core.*;
import io.github.genaitelemetry.exporters.*;

import java.util.*;

/**
 * Basic example demonstrating GenAI Telemetry usage.
 */
public class BasicExample {
    
    public static void main(String[] args) {
        // Initialize telemetry with console output (for demo)
        GenAITelemetry telemetry = GenAITelemetry.builder()
            .workflowName("example-app")
            .exporter(ConsoleExporter.builder()
                .colored(true)
                .verbose(false)
                .build())
            .build();
        
        telemetry.start();
        
        try {
            // Example 1: Trace an LLM call
            System.out.println("Example 1: LLM Call");
            Map<String, Object> llmResult = telemetry.traceLLM(
                "chat",
                "gpt-4o",
                "openai",
                () -> {
                    // Simulate LLM call
                    simulateDelay(100);
                    return createMockLLMResponse();
                }
            );
            System.out.println("LLM Response received\n");
            
            // Example 2: Trace an embedding call
            System.out.println("Example 2: Embedding Call");
            Map<String, Object> embeddingResult = telemetry.traceEmbedding(
                "embed",
                "text-embedding-3-small",
                () -> {
                    simulateDelay(50);
                    return createMockEmbeddingResponse();
                }
            );
            System.out.println("Embedding received\n");
            
            // Example 3: Trace a tool call
            System.out.println("Example 3: Tool Call");
            String toolResult = telemetry.traceTool(
                "search",
                "web_search",
                () -> {
                    simulateDelay(200);
                    return "Search results...";
                }
            );
            System.out.println("Tool result: " + toolResult + "\n");
            
            // Example 4: Trace a chain/pipeline
            System.out.println("Example 4: Chain/Pipeline");
            String chainResult = telemetry.traceChain(
                "rag-pipeline",
                () -> {
                    // Simulate a RAG pipeline
                    telemetry.traceEmbedding("embed-query", "text-embedding-3-small", () -> {
                        simulateDelay(30);
                        return createMockEmbeddingResponse();
                    });
                    
                    telemetry.traceTool("retrieve", "vector_search", () -> {
                        simulateDelay(50);
                        return "Retrieved documents";
                    });
                    
                    return telemetry.traceLLM("generate", "gpt-4o", "openai", () -> {
                        simulateDelay(150);
                        return createMockLLMResponse();
                    }).toString();
                }
            );
            System.out.println("Chain completed\n");
            
            // Example 5: Manual span management
            System.out.println("Example 5: Manual Span");
            Span span = telemetry.startSpan("custom-operation", SpanType.TOOL);
            span.setToolName("custom-tool");
            span.setAttribute("custom_field", "custom_value");
            
            simulateDelay(75);
            
            telemetry.endSpan().join();
            System.out.println("Manual span completed\n");
            
        } finally {
            telemetry.stop();
        }
        
        System.out.println("Done! Check the console output above for traces.");
    }
    
    private static void simulateDelay(int ms) {
        try {
            Thread.sleep(ms);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }
    
    private static Map<String, Object> createMockLLMResponse() {
        Map<String, Object> usage = new HashMap<>();
        usage.put("prompt_tokens", 100);
        usage.put("completion_tokens", 50);
        usage.put("total_tokens", 150);
        
        Map<String, Object> message = new HashMap<>();
        message.put("role", "assistant");
        message.put("content", "This is a mock response from the LLM.");
        
        Map<String, Object> choice = new HashMap<>();
        choice.put("index", 0);
        choice.put("message", message);
        choice.put("finish_reason", "stop");
        
        Map<String, Object> response = new HashMap<>();
        response.put("id", "chatcmpl-123");
        response.put("object", "chat.completion");
        response.put("model", "gpt-4o");
        response.put("choices", List.of(choice));
        response.put("usage", usage);
        
        return response;
    }
    
    private static Map<String, Object> createMockEmbeddingResponse() {
        Map<String, Object> usage = new HashMap<>();
        usage.put("prompt_tokens", 10);
        usage.put("total_tokens", 10);
        
        double[] embedding = new double[1536];
        Arrays.fill(embedding, 0.1);
        
        Map<String, Object> data = new HashMap<>();
        data.put("object", "embedding");
        data.put("index", 0);
        data.put("embedding", embedding);
        
        Map<String, Object> response = new HashMap<>();
        response.put("object", "list");
        response.put("data", List.of(data));
        response.put("model", "text-embedding-3-small");
        response.put("usage", usage);
        
        return response;
    }
}
