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
 * Exporter that sends spans to Grafana Loki.
 */
public class LokiExporter implements BaseExporter {
    
    private static final Logger logger = LoggerFactory.getLogger(LokiExporter.class);
    
    private final String url;
    private final String tenantId;
    private final int batchSize;
    private final long flushIntervalMs;
    
    private final HttpClient httpClient;
    private final ObjectMapper objectMapper;
    private final List<SpanData> batch = new ArrayList<>();
    private final Object batchLock = new Object();
    private ScheduledExecutorService scheduler;
    private volatile boolean running = false;
    
    public LokiExporter(String url, String tenantId, int batchSize, long flushIntervalMs) {
        String lokiUrl = url.replaceAll("/$", "");
        if (!lokiUrl.contains("/loki/api/v1/push")) {
            lokiUrl += "/loki/api/v1/push";
        }
        
        this.url = lokiUrl;
        this.tenantId = tenantId;
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
    
    private List<Map<String, Object>> spansToLokiStreams(List<SpanData> spans) {
        // Group spans by their labels
        Map<String, List<SpanData>> streamGroups = new HashMap<>();
        
        for (SpanData span : spans) {
            String key = String.format("%s:%s:%s:%s",
                span.getSpanType(),
                span.getWorkflowName() != null ? span.getWorkflowName() : "default",
                span.getStatus(),
                span.getModelName() != null ? span.getModelName() : "");
            
            streamGroups.computeIfAbsent(key, k -> new ArrayList<>()).add(span);
        }
        
        List<Map<String, Object>> streams = new ArrayList<>();
        
        for (Map.Entry<String, List<SpanData>> entry : streamGroups.entrySet()) {
            String[] keyParts = entry.getKey().split(":");
            
            Map<String, String> labels = new LinkedHashMap<>();
            labels.put("job", "genai-telemetry");
            labels.put("span_type", keyParts[0]);
            labels.put("workflow", keyParts[1]);
            labels.put("status", keyParts[2]);
            if (!keyParts[3].isEmpty()) {
                labels.put("model", keyParts[3]);
            }
            
            List<List<String>> values = new ArrayList<>();
            for (SpanData span : entry.getValue()) {
                try {
                    Instant timestamp = Instant.parse(span.getTimestamp());
                    long nanos = timestamp.toEpochMilli() * 1_000_000;
                    String logLine = objectMapper.writeValueAsString(span);
                    values.add(Arrays.asList(String.valueOf(nanos), logLine));
                } catch (Exception e) {
                    logger.warn("Failed to serialize span: {}", e.getMessage());
                }
            }
            
            Map<String, Object> stream = new HashMap<>();
            stream.put("stream", labels);
            stream.put("values", values);
            streams.add(stream);
        }
        
        return streams;
    }
    
    private CompletableFuture<Boolean> sendBatch(List<SpanData> spans) {
        if (spans.isEmpty()) {
            return CompletableFuture.completedFuture(true);
        }
        
        return CompletableFuture.supplyAsync(() -> {
            try {
                List<Map<String, Object>> streams = spansToLokiStreams(spans);
                Map<String, Object> payload = Map.of("streams", streams);
                
                HttpRequest.Builder requestBuilder = HttpRequest.newBuilder()
                    .uri(URI.create(url))
                    .header("Content-Type", "application/json")
                    .POST(HttpRequest.BodyPublishers.ofString(
                        objectMapper.writeValueAsString(payload)));
                
                if (tenantId != null && !tenantId.isEmpty()) {
                    requestBuilder.header("X-Scope-OrgID", tenantId);
                }
                
                HttpResponse<String> response = httpClient.send(requestBuilder.build(),
                    HttpResponse.BodyHandlers.ofString());
                
                return response.statusCode() == 200 || response.statusCode() == 204;
            } catch (Exception e) {
                logger.error("Loki error: {}", e.getMessage());
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
    
    @Override
    public CompletableFuture<Boolean> healthCheck() {
        return CompletableFuture.supplyAsync(() -> {
            try {
                String baseUrl = url.replace("/loki/api/v1/push", "");
                HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(baseUrl + "/ready"))
                    .GET()
                    .build();
                
                HttpResponse<String> response = httpClient.send(request,
                    HttpResponse.BodyHandlers.ofString());
                
                return response.statusCode() == 200;
            } catch (Exception e) {
                return false;
            }
        });
    }
    
    public static Builder builder() {
        return new Builder();
    }
    
    public static class Builder {
        private String url = "http://localhost:3100";
        private String tenantId;
        private int batchSize = 10;
        private long flushIntervalMs = 5000;
        
        public Builder url(String url) {
            this.url = url;
            return this;
        }
        
        public Builder tenantId(String tenantId) {
            this.tenantId = tenantId;
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
        
        public LokiExporter build() {
            return new LokiExporter(url, tenantId, batchSize, flushIntervalMs);
        }
    }
}
