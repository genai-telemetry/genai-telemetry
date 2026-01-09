package io.github.genaitelemetry.exporters;

import io.github.genaitelemetry.core.SpanData;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;

import java.util.concurrent.CompletableFuture;

/**
 * Exporter that outputs spans to the console.
 * Useful for development and debugging.
 */
public class ConsoleExporter implements BaseExporter {
    
    private final boolean colored;
    private final boolean verbose;
    private final ObjectMapper objectMapper;
    
    // ANSI color codes
    private static final String RESET = "\u001B[0m";
    private static final String RED = "\u001B[31m";
    private static final String GREEN = "\u001B[32m";
    private static final String YELLOW = "\u001B[33m";
    private static final String CYAN = "\u001B[36m";
    
    public ConsoleExporter() {
        this(true, false);
    }
    
    public ConsoleExporter(boolean colored, boolean verbose) {
        this.colored = colored;
        this.verbose = verbose;
        this.objectMapper = new ObjectMapper();
        this.objectMapper.enable(SerializationFeature.INDENT_OUTPUT);
    }
    
    @Override
    public CompletableFuture<Boolean> export(SpanData spanData) {
        return CompletableFuture.supplyAsync(() -> {
            try {
                String timestamp = spanData.getTimestamp();
                String spanType = spanData.getSpanType();
                String name = spanData.getName();
                double duration = spanData.getDurationMs();
                String status = spanData.getStatus();
                
                String message;
                if (colored) {
                    String statusColor = "ERROR".equals(status) ? RED : GREEN;
                    message = String.format("%s[%s]%s %s%s%s %s %s%s%s (%.2fms)",
                        CYAN, timestamp, RESET,
                        YELLOW, spanType, RESET,
                        name,
                        statusColor, status, RESET,
                        duration);
                } else {
                    message = String.format("[%s] %s %s %s (%.2fms)",
                        timestamp, spanType, name, status, duration);
                }
                
                System.out.println(message);
                
                if (verbose) {
                    String json = objectMapper.writeValueAsString(spanData);
                    System.out.println(json);
                }
                
                return true;
            } catch (Exception e) {
                System.err.println("ConsoleExporter error: " + e.getMessage());
                return false;
            }
        });
    }
    
    public static Builder builder() {
        return new Builder();
    }
    
    public static class Builder {
        private boolean colored = true;
        private boolean verbose = false;
        
        public Builder colored(boolean colored) {
            this.colored = colored;
            return this;
        }
        
        public Builder verbose(boolean verbose) {
            this.verbose = verbose;
            return this;
        }
        
        public ConsoleExporter build() {
            return new ConsoleExporter(colored, verbose);
        }
    }
}
