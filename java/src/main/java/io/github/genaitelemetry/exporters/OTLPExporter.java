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
 * Exporter that sends spans using OpenTelemetry Protocol (OTLP) over HTTP.
 */
public class OTLPExporter implements BaseExporter {
    
    private static final Logger logger = LoggerFactory.getLogger(OTLPExporter.class);
    
    private final String endpoint;
    private final Map<String, String> headers;
    private final String serviceName;
    private final int batchSize;
    private final long flushIntervalMs;
    
    private final HttpClient httpClient;
    private final ObjectMapper objectMapper;
    private final List<SpanData> batch = new ArrayList<>();
    private final Object batchLock = new Object();
    private ScheduledExecutorService scheduler;
    private volatile boolean running = false;
    
    public OTLPExporter(String endpoint, Map<String, String> headers, String serviceName,
                        int batchSize, long flushIntervalMs) {
        String url = endpoint.replaceAll("/$", "");
        if (!url.contains("/v1/traces")) {
            url += "/v1/traces";
        }
        
        this.endpoint = url;
        this.headers = headers != null ? headers : new HashMap<>();
        this.serviceName = serviceName;
        this.batchSize = batchSize;
        this.flushIntervalMs = flushIntervalMs;
        
        this.httpClient = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(10))
            .build();
        this.objectMapper = new ObjectMapper();
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
    
    private Map<String, Object> spanToOTLP(SpanData span) {
        Instant timestamp = Instant.parse(span.getTimestamp());
        long startTimeNano = timestamp.toEpochMilli() * 1_000_000;
        long durationNano = (long) (span.getDurationMs() * 1_000_000);
        
        List<Map<String, Object>> attributes = new ArrayList<>();
        
        addAttribute(attributes, "gen_ai.span_type", span.getSpanType());
        addAttribute(attributes, "gen_ai.workflow_name", span.getWorkflowName());
        addAttribute(attributes, "gen_ai.model.name", span.getModelName());
        addAttribute(attributes, "gen_ai.model.provider", span.getModelProvider());
        addAttribute(attributes, "gen_ai.usage.input_tokens", span.getInputTokens());
        addAttribute(attributes, "gen_ai.usage.output_tokens", span.getOutputTokens());
        addAttribute(attributes, "gen_ai.usage.total_tokens", span.getTotalTokens());
        addAttribute(attributes, "gen_ai.embedding.model", span.getEmbeddingModel());
        addAttribute(attributes, "gen_ai.vector_store", span.getVectorStore());
        addAttribute(attributes, "gen_ai.documents_retrieved", span.getDocumentsRetrieved());
        addAttribute(attributes, "gen_ai.tool.name", span.getToolName());
        addAttribute(attributes, "gen_ai.agent.name", span.getAgentName());
        addAttribute(attributes, "gen_ai.agent.type", span.getAgentType());
        
        if (span.getIsError() == 1) {
            addAttribute(attributes, "error.message", span.getErrorMessage());
            addAttribute(attributes, "error.type", span.getErrorType());
        }
        
        Map<String, Object> otlpSpan = new HashMap<>();
        otlpSpan.put("traceId", span.getTraceId());
        otlpSpan.put("spanId", span.getSpanId());
        if (span.getParentSpanId() != null) {
            otlpSpan.put("parentSpanId", span.getParentSpanId());
        }
        otlpSpan.put("name", span.getName());
        otlpSpan.put("kind", 1); // SPAN_KIND_INTERNAL
        otlpSpan.put("startTimeUnixNano", String.valueOf(startTimeNano));
        otlpSpan.put("endTimeUnixNano", String.valueOf(startTimeNano + durationNano));
        otlpSpan.put("attributes", attributes);
        otlpSpan.put("status", Map.of(
            "code", span.getIsError() == 1 ? 2 : 1,
            "message", span.getErrorMessage() != null ? span.getErrorMessage() : ""
        ));
        
        return otlpSpan;
    }
    
    private void addAttribute(List<Map<String, Object>> attributes, String key, Object value) {
        if (value == null) return;
        
        Map<String, Object> attr = new HashMap<>();
        attr.put("key", key);
        
        if (value instanceof String) {
            attr.put("value", Map.of("stringValue", value));
        } else if (value instanceof Integer) {
            attr.put("value", Map.of("intValue", String.valueOf(value)));
        } else if (value instanceof Double) {
            attr.put("value", Map.of("doubleValue", value));
        } else {
            attr.put("value", Map.of("stringValue", String.valueOf(value)));
        }
        
        attributes.add(attr);
    }
    
    private CompletableFuture<Boolean> sendBatch(List<SpanData> spans) {
        if (spans.isEmpty()) {
            return CompletableFuture.completedFuture(true);
        }
        
        return CompletableFuture.supplyAsync(() -> {
            try {
                List<Map<String, Object>> otlpSpans = spans.stream()
                    .map(this::spanToOTLP)
                    .toList();
                
                Map<String, Object> payload = Map.of(
                    "resourceSpans", List.of(Map.of(
                        "resource", Map.of(
                            "attributes", List.of(
                                Map.of("key", "service.name", 
                                       "value", Map.of("stringValue", serviceName)),
                                Map.of("key", "telemetry.sdk.name",
                                       "value", Map.of("stringValue", "genai-telemetry")),
                                Map.of("key", "telemetry.sdk.language",
                                       "value", Map.of("stringValue", "java"))
                            )
                        ),
                        "scopeSpans", List.of(Map.of(
                            "scope", Map.of("name", "genai-telemetry"),
                            "spans", otlpSpans
                        ))
                    ))
                );
                
                HttpRequest.Builder requestBuilder = HttpRequest.newBuilder()
                    .uri(URI.create(endpoint))
                    .header("Content-Type", "application/json")
                    .POST(HttpRequest.BodyPublishers.ofString(
                        objectMapper.writeValueAsString(payload)));
                
                for (Map.Entry<String, String> header : headers.entrySet()) {
                    requestBuilder.header(header.getKey(), header.getValue());
                }
                
                HttpResponse<String> response = httpClient.send(requestBuilder.build(),
                    HttpResponse.BodyHandlers.ofString());
                
                return response.statusCode() == 200;
            } catch (Exception e) {
                logger.error("OTLP error: {}", e.getMessage());
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
        private String endpoint = "http://localhost:4318";
        private Map<String, String> headers = new HashMap<>();
        private String serviceName = "genai-app";
        private int batchSize = 10;
        private long flushIntervalMs = 5000;
        
        public Builder endpoint(String endpoint) {
            this.endpoint = endpoint;
            return this;
        }
        
        public Builder headers(Map<String, String> headers) {
            this.headers = headers;
            return this;
        }
        
        public Builder header(String key, String value) {
            this.headers.put(key, value);
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
        
        public OTLPExporter build() {
            return new OTLPExporter(endpoint, headers, serviceName, batchSize, flushIntervalMs);
        }
    }
}
