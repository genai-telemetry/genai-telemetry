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
import java.util.concurrent.atomic.AtomicInteger;

/**
 * Exporter that sends spans to Elasticsearch.
 */
public class ElasticsearchExporter implements BaseExporter {
    
    private static final Logger logger = LoggerFactory.getLogger(ElasticsearchExporter.class);
    
    private final List<String> hosts;
    private final String index;
    private final String apiKey;
    private final String username;
    private final String password;
    private final int batchSize;
    private final long flushIntervalMs;
    
    private final HttpClient httpClient;
    private final ObjectMapper objectMapper;
    private final AtomicInteger hostIndex = new AtomicInteger(0);
    private final List<SpanData> batch = new ArrayList<>();
    private final Object batchLock = new Object();
    private ScheduledExecutorService scheduler;
    private volatile boolean running = false;
    
    public ElasticsearchExporter(List<String> hosts, String index, String apiKey,
                                  String username, String password, 
                                  int batchSize, long flushIntervalMs) {
        this.hosts = hosts.stream()
            .map(h -> h.replaceAll("/$", ""))
            .toList();
        this.index = index;
        this.apiKey = apiKey;
        this.username = username;
        this.password = password;
        this.batchSize = batchSize;
        this.flushIntervalMs = flushIntervalMs;
        
        this.httpClient = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(10))
            .build();
        this.objectMapper = new ObjectMapper();
    }
    
    private String getHost() {
        int idx = hostIndex.getAndUpdate(i -> (i + 1) % hosts.size());
        return hosts.get(idx);
    }
    
    private HttpRequest.Builder addAuthHeaders(HttpRequest.Builder builder) {
        if (apiKey != null && !apiKey.isEmpty()) {
            builder.header("Authorization", "ApiKey " + apiKey);
        } else if (username != null && password != null) {
            String auth = Base64.getEncoder().encodeToString(
                (username + ":" + password).getBytes());
            builder.header("Authorization", "Basic " + auth);
        }
        return builder;
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
                    // Bulk API requires action line followed by document
                    Map<String, Object> action = new HashMap<>();
                    action.put("index", Map.of("_index", index));
                    payload.append(objectMapper.writeValueAsString(action));
                    payload.append("\n");
                    payload.append(objectMapper.writeValueAsString(span));
                    payload.append("\n");
                }
                
                String host = getHost();
                HttpRequest request = addAuthHeaders(HttpRequest.newBuilder())
                    .uri(URI.create(host + "/_bulk"))
                    .header("Content-Type", "application/json")
                    .POST(HttpRequest.BodyPublishers.ofString(payload.toString()))
                    .build();
                
                HttpResponse<String> response = httpClient.send(request,
                    HttpResponse.BodyHandlers.ofString());
                
                if (response.statusCode() != 200) {
                    logger.error("Elasticsearch error: {}", response.body());
                    return false;
                }
                
                // Check for errors in response
                Map<?, ?> result = objectMapper.readValue(response.body(), Map.class);
                return !Boolean.TRUE.equals(result.get("errors"));
            } catch (Exception e) {
                logger.error("Elasticsearch error: {}", e.getMessage());
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
                String host = getHost();
                HttpRequest request = addAuthHeaders(HttpRequest.newBuilder())
                    .uri(URI.create(host + "/_cluster/health"))
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
        private List<String> hosts = List.of("http://localhost:9200");
        private String index = "genai-traces";
        private String apiKey;
        private String username;
        private String password;
        private int batchSize = 1;
        private long flushIntervalMs = 5000;
        
        public Builder hosts(List<String> hosts) {
            this.hosts = hosts;
            return this;
        }
        
        public Builder hosts(String... hosts) {
            this.hosts = Arrays.asList(hosts);
            return this;
        }
        
        public Builder index(String index) {
            this.index = index;
            return this;
        }
        
        public Builder apiKey(String apiKey) {
            this.apiKey = apiKey;
            return this;
        }
        
        public Builder username(String username) {
            this.username = username;
            return this;
        }
        
        public Builder password(String password) {
            this.password = password;
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
        
        public ElasticsearchExporter build() {
            return new ElasticsearchExporter(hosts, index, apiKey, username, password,
                batchSize, flushIntervalMs);
        }
    }
}
