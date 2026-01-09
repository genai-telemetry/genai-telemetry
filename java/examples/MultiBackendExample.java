package io.github.genaitelemetry.examples;

import io.github.genaitelemetry.core.*;
import io.github.genaitelemetry.exporters.*;

import java.util.*;

/**
 * Example demonstrating sending telemetry to multiple backends.
 */
public class MultiBackendExample {
    
    public static void main(String[] args) {
        // Create multiple exporters
        BaseExporter splunkExporter = SplunkHECExporter.builder()
            .hecUrl(System.getenv("SPLUNK_HEC_URL") != null 
                ? System.getenv("SPLUNK_HEC_URL") 
                : "http://localhost:8088")
            .hecToken(System.getenv("SPLUNK_HEC_TOKEN") != null 
                ? System.getenv("SPLUNK_HEC_TOKEN") 
                : "test-token")
            .index("genai_traces")
            .batchSize(10)
            .build();
        
        BaseExporter esExporter = ElasticsearchExporter.builder()
            .hosts(System.getenv("ES_HOST") != null 
                ? System.getenv("ES_HOST") 
                : "http://localhost:9200")
            .index("genai-traces")
            .batchSize(10)
            .build();
        
        BaseExporter otlpExporter = OTLPExporter.builder()
            .endpoint(System.getenv("OTLP_ENDPOINT") != null 
                ? System.getenv("OTLP_ENDPOINT") 
                : "http://localhost:4318")
            .serviceName("multi-backend-example")
            .batchSize(10)
            .build();
        
        BaseExporter consoleExporter = ConsoleExporter.builder()
            .colored(true)
            .build();
        
        // Combine into multi-exporter
        MultiExporter multiExporter = new MultiExporter(
            splunkExporter,
            esExporter,
            otlpExporter,
            consoleExporter
        );
        
        // Initialize telemetry
        GenAITelemetry telemetry = GenAITelemetry.builder()
            .workflowName("multi-backend-app")
            .exporter(multiExporter)
            .build();
        
        telemetry.start();
        
        try {
            System.out.println("Multi-Backend Telemetry Example");
            System.out.println("================================\n");
            System.out.println("Sending traces to:");
            System.out.println("  - Splunk HEC");
            System.out.println("  - Elasticsearch");
            System.out.println("  - OTLP Collector");
            System.out.println("  - Console\n");
            
            // Make several traced calls
            for (int i = 1; i <= 5; i++) {
                System.out.printf("Making call %d...%n", i);
                
                final int callNum = i;
                telemetry.traceLLM("chat-" + i, "gpt-4o", "openai", () -> {
                    try {
                        Thread.sleep(100);
                    } catch (InterruptedException e) {
                        Thread.currentThread().interrupt();
                    }
                    
                    Map<String, Object> response = new HashMap<>();
                    Map<String, Object> usage = new HashMap<>();
                    usage.put("prompt_tokens", 50 + callNum * 10);
                    usage.put("completion_tokens", 25 + callNum * 5);
                    response.put("usage", usage);
                    return response;
                });
            }
            
            // Send a custom span
            telemetry.sendSpan(SpanType.TOOL, "custom-operation", SpanData.builder()
                .toolName("example-tool")
                .durationMs(42)
                .attribute("custom_field", "custom_value")
                .status(SpanStatus.OK)
            ).join();
            
            System.out.println("\nDone! Traces sent to all configured backends.");
            
        } finally {
            telemetry.stop();
        }
    }
}
