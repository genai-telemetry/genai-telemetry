package io.github.genaitelemetry.exporters;

import io.github.genaitelemetry.core.SpanData;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.*;

/**
 * Exporter that sends spans to Datadog.
 */
public class DatadogExporter implements BaseExporter {
    
    private static final Logger logger = LoggerFactory.getLogger(DatadogExporter.class);
    
    private final String apiKey;
    private final String site;
    private final String serviceName;
    private final int batchSize;
    private final long flushIntervalMs;
    
    private final HttpClient httpClient;
    private final ObjectMapper objectMapper;
    private final List<SpanData> batch = new ArrayList<>();
    private final Object batchLock = new Object();
    private ScheduledExecutorService scheduler;
    private volatile boolean running = false;
    
    public DatadogExporter(String apiKey, String site, String serviceName,
                           int batchSize, long flushIntervalMs) {
        this.apiKey = apiKey;
        this.site = site;
        this.serviceName = serviceName;
        this.batchSize = batchSize;
        this.flushIntervalMs = flushIntervalMs;
        
        this.httpClient = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(10))
            .build();
        this.objectMapper = new ObjectMapper();
    }
    
    private long hexToLong(String hex) {
        // Take last 16 chars and convert to long
        String truncated = hex.length() > 16 ? hex.substring(hex.length() - 16) : hex;
        return Long.parseUnsignedLong(truncated, 16);
    }
    
    @Override
    public void start() {
        if (running) return;
        running = true;
        
        if (batchSize > 1) {
            scheduler = Executors.newSingleThreadScheduledExecutor();
            scheduler.scheduleAtFixedRate(
                () -> flush().join(),
                flushIntervalMs,
                flushIntervalMs,
                TimeUnit.MILLISECONDS
            );
        }
    }
    
    @Override
    public void stop() {
        running = false;
        if (scheduler != null) {
            scheduler.shutdown();
            try {
                scheduler.awaitTermination(5, TimeUnit.SECONDS);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
        }
        flush().join();
    }
    
    @Override
    public CompletableFuture<Void> flush() {
        List<SpanData> toSend;
        synchronized (batchLock) {
            if (batch.isEmpty()) {
                return CompletableFuture.completedFuture(null);
            }
            toSend = new ArrayList<>(batch);
            batch.clear();
        }
        
        return sendBatch(toSend).thenApply(success -> null);
    }
    
    private Map<String, Object> spanToDatadog(SpanData span) {
        Instant timestamp = Instant.parse(span.getTimestamp());
        long startNano = timestamp.toEpochMilli() * 1_000_000;
        long durationNano = (long) (span.getDurationMs() * 1_000_000);
        
        Map<String, String> meta = new HashMap<>();
        meta.put("gen_ai.span_type", span.getSpanType());
        
        if (span.getWorkflowName() != null) meta.put("gen_ai.workflow_name", span.getWorkflowName());
        if (span.getModelName() != null) meta.put("gen_ai.model.name", span.getModelName());
        if (span.getModelProvider() != null) meta.put("gen_ai.model.provider", span.getModelProvider());
        if (span.getEmbeddingModel() != null) meta.put("gen_ai.embedding.model", span.getEmbeddingModel());
        if (span.getVectorStore() != null) meta.put("gen_ai.vector_store", span.getVectorStore());
        if (span.getToolName() != null) meta.put("gen_ai.tool.name", span.getToolName());
        if (span.getAgentName() != null) meta.put("gen_ai.agent.name", span.getAgentName());
        if (span.getAgentType() != null) meta.put("gen_ai.agent.type", span.getAgentType());
        
        if (span.getIsError() == 1) {
            if (span.getErrorMessage() != null) meta.put("error.message", span.getErrorMessage());
            if (span.getErrorType() != null) meta.put("error.type", span.getErrorType());
        }
        
        Map<String, Number> metrics = new HashMap<>();
        if (span.getInputTokens() != null) metrics.put("gen_ai.usage.input_tokens", span.getInputTokens());
        if (span.getOutputTokens() != null) metrics.put("gen_ai.usage.output_tokens", span.getOutputTokens());
        if (span.getTotalTokens() != null) metrics.put("gen_ai.usage.total_tokens", span.getTotalTokens());
        if (span.getDocumentsRetrieved() != null) metrics.put("gen_ai.documents_retrieved", span.getDocumentsRetrieved());
        
        Map<String, Object> ddSpan = new HashMap<>();
        ddSpan.put("trace_id", hexToLong(span.getTraceId()));
        ddSpan.put("span_id", hexToLong(span.getSpanId()));
        if (span.getParentSpanId() != null) {
            ddSpan.put("parent_id", hexToLong(span.getParentSpanId()));
        }
        ddSpan.put("name", span.getSpanType().toLowerCase());
        ddSpan.put("resource", span.getName());
        ddSpan.put("service", serviceName);
        ddSpan.put("type", "custom");
        ddSpan.put("start", startNano);
        ddSpan.put("duration", durationNano);
        ddSpan.put("meta", meta);
        ddSpan.put("metrics", metrics);
        ddSpan.put("error", span.getIsError());
        
        return ddSpan;
    }
    
    private CompletableFuture<Boolean> sendBatch(List<SpanData> spans) {
        if (spans.isEmpty()) {
            return CompletableFuture.completedFuture(true);
        }
        
        return CompletableFuture.supplyAsync(() -> {
            try {
                List<Map<String, Object>> ddSpans = spans.stream()
                    .map(this::spanToDatadog)
                    .toList();
                
                // Datadog expects array of traces, each trace is array of spans
                List<List<Map<String, Object>>> payload = List.of(ddSpans);
                
                HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create("https://trace.agent." + site + "/api/v0.2/traces"))
                    .header("Content-Type", "application/json")
                    .header("DD-API-KEY", apiKey)
                    .PUT(HttpRequest.BodyPublishers.ofString(
                        objectMapper.writeValueAsString(payload)))
                    .build();
                
                HttpResponse<String> response = httpClient.send(request,
                    HttpResponse.BodyHandlers.ofString());
                
                return response.statusCode() == 200;
            } catch (Exception e) {
                logger.error("Datadog error: {}", e.getMessage());
                return false;
            }
        });
    }
    
    @Override
    public CompletableFuture<Boolean> export(SpanData spanData) {
        if (batchSize <= 1) {
            return sendBatch(Collections.singletonList(spanData));
        }
        
        boolean shouldFlush;
        synchronized (batchLock) {
            batch.add(spanData);
            shouldFlush = batch.size() >= batchSize;
        }
        
        if (shouldFlush) {
            return flush().thenApply(v -> true);
        }
        
        return CompletableFuture.completedFuture(true);
    }
    
    public static Builder builder() {
        return new Builder();
    }
    
    public static class Builder {
        private String apiKey;
        private String site = "datadoghq.com";
        private String serviceName = "genai-app";
        private int batchSize = 10;
        private long flushIntervalMs = 5000;
        
        public Builder apiKey(String apiKey) {
            this.apiKey = apiKey;
            return this;
        }
        
        public Builder site(String site) {
            this.site = site;
            return this;
        }
        
        public Builder serviceName(String serviceName) {
            this.serviceName = serviceName;
            return this;
        }
        
        public Builder batchSize(int batchSize) {
            this.batchSize = batchSize;
            return this;
        }
        
        public Builder flushIntervalMs(long flushIntervalMs) {
            this.flushIntervalMs = flushIntervalMs;
            return this;
        }
        
        public DatadogExporter build() {
            if (apiKey == null) {
                throw new IllegalArgumentException("apiKey is required");
            }
            return new DatadogExporter(apiKey, site, serviceName, batchSize, flushIntervalMs);
        }
    }
}
