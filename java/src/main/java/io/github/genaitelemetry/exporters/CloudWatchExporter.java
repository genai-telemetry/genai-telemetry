package io.github.genaitelemetry.exporters;

import io.github.genaitelemetry.core.SpanData;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.time.Instant;
import java.util.*;
import java.util.concurrent.*;

/**
 * Exporter that sends spans to AWS CloudWatch Logs.
 * 
 * Requires the AWS SDK (software.amazon.awssdk:cloudwatchlogs) to be on the classpath.
 */
public class CloudWatchExporter implements BaseExporter {
    
    private static final Logger logger = LoggerFactory.getLogger(CloudWatchExporter.class);
    
    private final String logGroup;
    private final String region;
    private final int batchSize;
    private final long flushIntervalMs;
    
    private final ObjectMapper objectMapper;
    private final List<SpanData> batch = new ArrayList<>();
    private final Object batchLock = new Object();
    private ScheduledExecutorService scheduler;
    private volatile boolean running = false;
    
    private final String logStreamName;
    private Object cloudWatchClient; // Dynamic to avoid hard dependency
    private String sequenceToken;
    
    public CloudWatchExporter(String logGroup, String region, int batchSize, long flushIntervalMs) {
        this.logGroup = logGroup;
        this.region = region;
        this.batchSize = batchSize;
        this.flushIntervalMs = flushIntervalMs;
        this.objectMapper = new ObjectMapper();
        
        // Create unique log stream name
        String timestamp = Instant.now().toString().replace(":", "-").replace(".", "-");
        this.logStreamName = "genai-telemetry-" + timestamp;
    }
    
    @Override
    public void start() {
        if (running) return;
        running = true;
        
        // Try to initialize AWS client
        try {
            initializeAwsClient();
            ensureLogStream();
        } catch (Exception e) {
            logger.warn("Could not initialize AWS CloudWatch client: {}. " +
                "Make sure software.amazon.awssdk:cloudwatchlogs is on the classpath.", e.getMessage());
        }
        
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
    
    private void initializeAwsClient() throws Exception {
        // Use reflection to avoid hard dependency on AWS SDK
        Class<?> clientBuilderClass = Class.forName("software.amazon.awssdk.services.cloudwatchlogs.CloudWatchLogsClient");
        Object builder = clientBuilderClass.getMethod("builder").invoke(null);
        
        Class<?> regionClass = Class.forName("software.amazon.awssdk.regions.Region");
        Object regionObj = regionClass.getMethod("of", String.class).invoke(null, region);
        
        builder.getClass().getMethod("region", Class.forName("software.amazon.awssdk.regions.Region"))
            .invoke(builder, regionObj);
        
        cloudWatchClient = builder.getClass().getMethod("build").invoke(builder);
    }
    
    private void ensureLogStream() throws Exception {
        if (cloudWatchClient == null) return;
        
        // Create log stream (ignore if exists)
        try {
            Class<?> requestClass = Class.forName("software.amazon.awssdk.services.cloudwatchlogs.model.CreateLogStreamRequest");
            Object requestBuilder = requestClass.getMethod("builder").invoke(null);
            requestBuilder.getClass().getMethod("logGroupName", String.class).invoke(requestBuilder, logGroup);
            requestBuilder.getClass().getMethod("logStreamName", String.class).invoke(requestBuilder, logStreamName);
            Object request = requestBuilder.getClass().getMethod("build").invoke(requestBuilder);
            
            cloudWatchClient.getClass().getMethod("createLogStream", requestClass).invoke(cloudWatchClient, request);
        } catch (Exception e) {
            // Stream might already exist, ignore
            logger.debug("Log stream creation: {}", e.getMessage());
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
        
        // Close AWS client if initialized
        if (cloudWatchClient != null) {
            try {
                cloudWatchClient.getClass().getMethod("close").invoke(cloudWatchClient);
            } catch (Exception e) {
                // Ignore close errors
            }
        }
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
            if (cloudWatchClient == null) {
                logger.warn("CloudWatch client not initialized. Spans will be logged locally.");
                for (SpanData span : spans) {
                    try {
                        logger.info("CloudWatch span: {}", objectMapper.writeValueAsString(span));
                    } catch (Exception e) {
                        logger.error("Failed to serialize span", e);
                    }
                }
                return true;
            }
            
            try {
                // Build log events
                List<Object> logEvents = new ArrayList<>();
                Class<?> logEventClass = Class.forName("software.amazon.awssdk.services.cloudwatchlogs.model.InputLogEvent");
                
                // Sort by timestamp
                spans.sort(Comparator.comparing(SpanData::getTimestamp));
                
                for (SpanData span : spans) {
                    Object eventBuilder = logEventClass.getMethod("builder").invoke(null);
                    long timestamp = Instant.parse(span.getTimestamp()).toEpochMilli();
                    eventBuilder.getClass().getMethod("timestamp", Long.class).invoke(eventBuilder, timestamp);
                    eventBuilder.getClass().getMethod("message", String.class)
                        .invoke(eventBuilder, objectMapper.writeValueAsString(span));
                    logEvents.add(eventBuilder.getClass().getMethod("build").invoke(eventBuilder));
                }
                
                // Build put request
                Class<?> requestClass = Class.forName("software.amazon.awssdk.services.cloudwatchlogs.model.PutLogEventsRequest");
                Object requestBuilder = requestClass.getMethod("builder").invoke(null);
                requestBuilder.getClass().getMethod("logGroupName", String.class).invoke(requestBuilder, logGroup);
                requestBuilder.getClass().getMethod("logStreamName", String.class).invoke(requestBuilder, logStreamName);
                requestBuilder.getClass().getMethod("logEvents", Collection.class).invoke(requestBuilder, logEvents);
                
                if (sequenceToken != null) {
                    requestBuilder.getClass().getMethod("sequenceToken", String.class).invoke(requestBuilder, sequenceToken);
                }
                
                Object request = requestBuilder.getClass().getMethod("build").invoke(requestBuilder);
                
                // Send
                Object response = cloudWatchClient.getClass().getMethod("putLogEvents", requestClass)
                    .invoke(cloudWatchClient, request);
                
                // Get next sequence token
                sequenceToken = (String) response.getClass().getMethod("nextSequenceToken").invoke(response);
                
                return true;
            } catch (Exception e) {
                logger.error("CloudWatch error: {}", e.getMessage());
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
        private String logGroup = "/genai/traces";
        private String region = "us-east-1";
        private int batchSize = 10;
        private long flushIntervalMs = 5000;
        
        public Builder logGroup(String logGroup) {
            this.logGroup = logGroup;
            return this;
        }
        
        public Builder region(String region) {
            this.region = region;
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
        
        public CloudWatchExporter build() {
            return new CloudWatchExporter(logGroup, region, batchSize, flushIntervalMs);
        }
    }
}
