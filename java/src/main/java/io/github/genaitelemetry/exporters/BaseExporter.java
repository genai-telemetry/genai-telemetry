package io.github.genaitelemetry.exporters;

import io.github.genaitelemetry.core.SpanData;

import java.util.List;
import java.util.concurrent.CompletableFuture;

/**
 * Base interface for all telemetry exporters.
 */
public interface BaseExporter {
    
    /**
     * Export a single span.
     *
     * @param spanData The span data to export
     * @return CompletableFuture that completes with true if successful
     */
    CompletableFuture<Boolean> export(SpanData spanData);
    
    /**
     * Export multiple spans in a batch.
     *
     * @param spans The list of spans to export
     * @return CompletableFuture that completes with true if all exports were successful
     */
    default CompletableFuture<Boolean> exportBatch(List<SpanData> spans) {
        CompletableFuture<Boolean>[] futures = spans.stream()
            .map(this::export)
            .toArray(CompletableFuture[]::new);
        
        return CompletableFuture.allOf(futures)
            .thenApply(v -> {
                for (CompletableFuture<Boolean> f : futures) {
                    if (!f.join()) return false;
                }
                return true;
            });
    }
    
    /**
     * Start the exporter.
     */
    default void start() {
        // Override in subclasses if needed
    }
    
    /**
     * Stop the exporter and flush pending data.
     */
    default void stop() {
        // Override in subclasses if needed
    }
    
    /**
     * Flush any buffered data.
     */
    default CompletableFuture<Void> flush() {
        return CompletableFuture.completedFuture(null);
    }
    
    /**
     * Check if the exporter is healthy.
     *
     * @return CompletableFuture that completes with true if healthy
     */
    default CompletableFuture<Boolean> healthCheck() {
        return CompletableFuture.completedFuture(true);
    }
}
