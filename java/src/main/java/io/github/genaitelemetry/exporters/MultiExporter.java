package io.github.genaitelemetry.exporters;

import io.github.genaitelemetry.core.SpanData;

import java.util.Arrays;
import java.util.List;
import java.util.concurrent.CompletableFuture;

/**
 * Exporter that sends spans to multiple exporters simultaneously.
 */
public class MultiExporter implements BaseExporter {
    
    private final List<BaseExporter> exporters;
    
    public MultiExporter(List<BaseExporter> exporters) {
        this.exporters = exporters;
    }
    
    public MultiExporter(BaseExporter... exporters) {
        this.exporters = Arrays.asList(exporters);
    }
    
    @Override
    public void start() {
        for (BaseExporter exporter : exporters) {
            exporter.start();
        }
    }
    
    @Override
    public void stop() {
        for (BaseExporter exporter : exporters) {
            exporter.stop();
        }
    }
    
    @Override
    public CompletableFuture<Void> flush() {
        CompletableFuture<?>[] futures = exporters.stream()
            .map(BaseExporter::flush)
            .toArray(CompletableFuture[]::new);
        
        return CompletableFuture.allOf(futures);
    }
    
    @Override
    public CompletableFuture<Boolean> export(SpanData spanData) {
        CompletableFuture<Boolean>[] futures = exporters.stream()
            .map(e -> e.export(spanData))
            .toArray(CompletableFuture[]::new);
        
        return CompletableFuture.allOf(futures)
            .thenApply(v -> {
                // Return true if at least one succeeded
                for (CompletableFuture<Boolean> f : futures) {
                    if (f.join()) return true;
                }
                return false;
            });
    }
    
    @Override
    public CompletableFuture<Boolean> exportBatch(List<SpanData> spans) {
        CompletableFuture<Boolean>[] futures = exporters.stream()
            .map(e -> e.exportBatch(spans))
            .toArray(CompletableFuture[]::new);
        
        return CompletableFuture.allOf(futures)
            .thenApply(v -> {
                for (CompletableFuture<Boolean> f : futures) {
                    if (f.join()) return true;
                }
                return false;
            });
    }
    
    @Override
    public CompletableFuture<Boolean> healthCheck() {
        CompletableFuture<Boolean>[] futures = exporters.stream()
            .map(BaseExporter::healthCheck)
            .toArray(CompletableFuture[]::new);
        
        return CompletableFuture.allOf(futures)
            .thenApply(v -> {
                for (CompletableFuture<Boolean> f : futures) {
                    if (f.join()) return true;
                }
                return false;
            });
    }
    
    /**
     * Get the list of exporters.
     */
    public List<BaseExporter> getExporters() {
        return exporters;
    }
}
