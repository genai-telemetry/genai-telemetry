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
import java.util.*;
import java.util.concurrent.*;

/**
 * Exporter that sends spans to Splunk via HTTP Event Collector (HEC).
 */
public class SplunkHECExporter implements BaseExporter {
    
    private static final Logger logger = LoggerFactory.getLogger(SplunkHECExporter.class);
    
    private final String hecUrl;
    private final String hecToken;
    private final String index;
    private final String sourcetype;
    private final int batchSize;
    private final long flushIntervalMs;
    
    private final HttpClient httpClient;
    private final ObjectMapper objectMapper;
    private final List<SpanData> batch = new ArrayList<>();
    private final Object batchLock = new Object();
    private ScheduledExecutorService scheduler;
    private volatile boolean running = false;
    
    public SplunkHECExporter(String hecUrl, String hecToken, String index, 
                              String sourcetype, int batchSize, long flushIntervalMs) {
        String url = hecUrl.replaceAll("/$", "");
        if (!url.endsWith("/services/collector/event")) {
            url += "/services/collector/event";
        }
        
        this.hecUrl = url;
        this.hecToken = hecToken;
        this.index = index;
        this.sourcetype = sourcetype;
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
    
    private CompletableFuture<Boolean> sendBatch(List<SpanData> spans) {
        if (spans.isEmpty()) {
            return CompletableFuture.completedFuture(true);
        }
        
        return CompletableFuture.supplyAsync(() -> {
            try {
                StringBuilder payload = new StringBuilder();
                for (SpanData span : spans) {
                    Map<String, Object> event = new HashMap<>();
                    event.put("index", index);
                    event.put("sourcetype", sourcetype);
                    event.put("source", "genai-telemetry");
                    event.put("event", span);
                    
                    payload.append(objectMapper.writeValueAsString(event));
                    payload.append("\n");
                }
                
                HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(hecUrl))
                    .header("Authorization", "Splunk " + hecToken)
                    .header("Content-Type", "application/json")
                    .POST(HttpRequest.BodyPublishers.ofString(payload.toString()))
                    .build();
                
                HttpResponse<String> response = httpClient.send(request, 
                    HttpResponse.BodyHandlers.ofString());
                
                return response.statusCode() == 200;
            } catch (Exception e) {
                logger.error("Splunk HEC error: {}", e.getMessage());
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
        SpanData testSpan = SpanData.builder()
            .name("health_check")
            .spanType("HEALTH")
            .build();
        return sendBatch(Collections.singletonList(testSpan));
    }
    
    public static Builder builder() {
        return new Builder();
    }
    
    public static class Builder {
        private String hecUrl;
        private String hecToken;
        private String index = "genai_traces";
        private String sourcetype = "genai:trace";
        private int batchSize = 1;
        private long flushIntervalMs = 5000;
        
        public Builder hecUrl(String hecUrl) {
            this.hecUrl = hecUrl;
            return this;
        }
        
        public Builder hecToken(String hecToken) {
            this.hecToken = hecToken;
            return this;
        }
        
        public Builder index(String index) {
            this.index = index;
            return this;
        }
        
        public Builder sourcetype(String sourcetype) {
            this.sourcetype = sourcetype;
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
        
        public SplunkHECExporter build() {
            if (hecUrl == null || hecToken == null) {
                throw new IllegalArgumentException("hecUrl and hecToken are required");
            }
            return new SplunkHECExporter(hecUrl, hecToken, index, sourcetype, 
                batchSize, flushIntervalMs);
        }
    }
}
