package io.github.genaitelemetry.exporters;

import io.github.genaitelemetry.core.SpanData;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.io.BufferedWriter;
import java.io.FileWriter;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.locks.ReentrantLock;

/**
 * Exporter that writes spans to a JSONL file.
 */
public class FileExporter implements BaseExporter {
    
    private final String filePath;
    private final ObjectMapper objectMapper;
    private final ReentrantLock lock = new ReentrantLock();
    private BufferedWriter writer;
    
    public FileExporter(String filePath) {
        this.filePath = filePath;
        this.objectMapper = new ObjectMapper();
    }
    
    @Override
    public void start() {
        try {
            Path path = Paths.get(filePath);
            if (!Files.exists(path.getParent())) {
                Files.createDirectories(path.getParent());
            }
            this.writer = new BufferedWriter(new FileWriter(filePath, true));
        } catch (IOException e) {
            throw new RuntimeException("Failed to open file: " + filePath, e);
        }
    }
    
    @Override
    public void stop() {
        flush().join();
        lock.lock();
        try {
            if (writer != null) {
                writer.close();
                writer = null;
            }
        } catch (IOException e) {
            // Ignore close errors
        } finally {
            lock.unlock();
        }
    }
    
    @Override
    public CompletableFuture<Void> flush() {
        return CompletableFuture.runAsync(() -> {
            lock.lock();
            try {
                if (writer != null) {
                    writer.flush();
                }
            } catch (IOException e) {
                // Ignore flush errors
            } finally {
                lock.unlock();
            }
        });
    }
    
    @Override
    public CompletableFuture<Boolean> export(SpanData spanData) {
        return CompletableFuture.supplyAsync(() -> {
            lock.lock();
            try {
                if (writer == null) {
                    start();
                }
                String json = objectMapper.writeValueAsString(spanData);
                writer.write(json);
                writer.newLine();
                return true;
            } catch (IOException e) {
                System.err.println("FileExporter error: " + e.getMessage());
                return false;
            } finally {
                lock.unlock();
            }
        });
    }
    
    public static Builder builder() {
        return new Builder();
    }
    
    public static class Builder {
        private String filePath = "genai_traces.jsonl";
        
        public Builder filePath(String filePath) {
            this.filePath = filePath;
            return this;
        }
        
        public FileExporter build() {
            return new FileExporter(filePath);
        }
    }
}
