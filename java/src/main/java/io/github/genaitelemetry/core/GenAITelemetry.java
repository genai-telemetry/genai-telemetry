package io.github.genaitelemetry.core;

import io.github.genaitelemetry.exporters.BaseExporter;
import io.github.genaitelemetry.utils.IdGenerator;
import io.github.genaitelemetry.utils.TokenExtractor;

import java.time.Instant;
import java.util.ArrayDeque;
import java.util.Deque;
import java.util.concurrent.CompletableFuture;
import java.util.function.Function;
import java.util.function.Supplier;

/**
 * Main telemetry manager for GenAI applications.
 */
public class GenAITelemetry {
    
    private static GenAITelemetry instance;
    
    private final String workflowName;
    private final String serviceName;
    private final BaseExporter exporter;
    
    private final ThreadLocal<String> traceId = new ThreadLocal<>();
    private final ThreadLocal<Deque<Span>> spanStack = ThreadLocal.withInitial(ArrayDeque::new);
    
    private GenAITelemetry(String workflowName, String serviceName, BaseExporter exporter) {
        this.workflowName = workflowName;
        this.serviceName = serviceName != null ? serviceName : workflowName;
        this.exporter = exporter;
    }
    
    public String getTraceId() {
        String id = traceId.get();
        if (id == null) {
            id = IdGenerator.generateTraceId();
            traceId.set(id);
        }
        return id;
    }
    
    public void setTraceId(String id) {
        traceId.set(id);
    }
    
    public String newTrace() {
        String id = IdGenerator.generateTraceId();
        traceId.set(id);
        return id;
    }
    
    public Span currentSpan() {
        Deque<Span> stack = spanStack.get();
        return stack.isEmpty() ? null : stack.peek();
    }
    
    public void start() {
        exporter.start();
    }
    
    public void stop() {
        exporter.stop();
    }
    
    public Span startSpan(String name, SpanType spanType) {
        Span parent = currentSpan();
        String parentId = parent != null ? parent.getSpanId() : null;
        
        Span span = new Span(getTraceId(), IdGenerator.generateSpanId(), name,
            spanType, workflowName, parentId);
        
        spanStack.get().push(span);
        return span;
    }
    
    public CompletableFuture<Void> endSpan() {
        return endSpan(null);
    }
    
    public CompletableFuture<Void> endSpan(Throwable error) {
        Deque<Span> stack = spanStack.get();
        if (stack.isEmpty()) {
            return CompletableFuture.completedFuture(null);
        }
        
        Span span = stack.pop();
        span.finish(error);
        
        return exporter.export(span.toSpanData()).thenApply(v -> null);
    }
    
    public CompletableFuture<Boolean> sendSpan(SpanType spanType, String name, 
                                                SpanData.Builder builder) {
        Span parent = currentSpan();
        
        SpanData spanData = builder
            .traceId(getTraceId())
            .spanId(IdGenerator.generateSpanId())
            .parentSpanId(parent != null ? parent.getSpanId() : null)
            .spanType(spanType)
            .name(name)
            .workflowName(workflowName)
            .timestamp(Instant.now().toString())
            .build();
        
        return exporter.export(spanData);
    }
    
    /**
     * Trace an LLM call.
     */
    public <T> T traceLLM(String name, String modelName, String modelProvider,
                          Supplier<T> operation) {
        long start = System.nanoTime();
        
        try {
            T result = operation.get();
            double duration = (System.nanoTime() - start) / 1_000_000.0;
            
            int[] tokens = TokenExtractor.extractTokens(result);
            
            sendSpan(SpanType.LLM, name, SpanData.builder()
                .modelName(modelName)
                .modelProvider(modelProvider)
                .durationMs(duration)
                .inputTokens(tokens[0])
                .outputTokens(tokens[1])
                .status(SpanStatus.OK)
            ).join();
            
            return result;
        } catch (Exception e) {
            double duration = (System.nanoTime() - start) / 1_000_000.0;
            
            sendSpan(SpanType.LLM, name, SpanData.builder()
                .modelName(modelName)
                .modelProvider(modelProvider)
                .durationMs(duration)
                .status(SpanStatus.ERROR)
                .isError(true)
                .errorMessage(e.getMessage())
                .errorType(e.getClass().getSimpleName())
            ).join();
            
            throw e;
        }
    }
    
    /**
     * Trace an embedding call.
     */
    public <T> T traceEmbedding(String name, String model, Supplier<T> operation) {
        long start = System.nanoTime();
        
        try {
            T result = operation.get();
            double duration = (System.nanoTime() - start) / 1_000_000.0;
            
            int[] tokens = TokenExtractor.extractTokens(result);
            
            sendSpan(SpanType.EMBEDDING, name, SpanData.builder()
                .embeddingModel(model)
                .durationMs(duration)
                .inputTokens(tokens[0])
                .status(SpanStatus.OK)
            ).join();
            
            return result;
        } catch (Exception e) {
            double duration = (System.nanoTime() - start) / 1_000_000.0;
            
            sendSpan(SpanType.EMBEDDING, name, SpanData.builder()
                .embeddingModel(model)
                .durationMs(duration)
                .status(SpanStatus.ERROR)
                .isError(true)
                .errorMessage(e.getMessage())
            ).join();
            
            throw e;
        }
    }
    
    /**
     * Trace a retrieval operation.
     */
    public <T> T traceRetrieval(String name, String vectorStore, String embeddingModel,
                                 Function<Void, T> operation, int documentsRetrieved) {
        long start = System.nanoTime();
        
        try {
            T result = operation.apply(null);
            double duration = (System.nanoTime() - start) / 1_000_000.0;
            
            sendSpan(SpanType.RETRIEVER, name, SpanData.builder()
                .vectorStore(vectorStore)
                .embeddingModel(embeddingModel)
                .documentsRetrieved(documentsRetrieved)
                .durationMs(duration)
                .status(SpanStatus.OK)
            ).join();
            
            return result;
        } catch (Exception e) {
            double duration = (System.nanoTime() - start) / 1_000_000.0;
            
            sendSpan(SpanType.RETRIEVER, name, SpanData.builder()
                .vectorStore(vectorStore)
                .durationMs(duration)
                .status(SpanStatus.ERROR)
                .isError(true)
                .errorMessage(e.getMessage())
            ).join();
            
            throw e;
        }
    }
    
    /**
     * Trace a tool call.
     */
    public <T> T traceTool(String name, String toolName, Supplier<T> operation) {
        long start = System.nanoTime();
        
        try {
            T result = operation.get();
            double duration = (System.nanoTime() - start) / 1_000_000.0;
            
            sendSpan(SpanType.TOOL, name, SpanData.builder()
                .toolName(toolName)
                .durationMs(duration)
                .status(SpanStatus.OK)
            ).join();
            
            return result;
        } catch (Exception e) {
            double duration = (System.nanoTime() - start) / 1_000_000.0;
            
            sendSpan(SpanType.TOOL, name, SpanData.builder()
                .toolName(toolName)
                .durationMs(duration)
                .status(SpanStatus.ERROR)
                .isError(true)
                .errorMessage(e.getMessage())
            ).join();
            
            throw e;
        }
    }
    
    /**
     * Trace a chain/pipeline.
     */
    public <T> T traceChain(String name, Supplier<T> operation) {
        newTrace();
        long start = System.nanoTime();
        
        try {
            T result = operation.get();
            double duration = (System.nanoTime() - start) / 1_000_000.0;
            
            sendSpan(SpanType.CHAIN, name, SpanData.builder()
                .durationMs(duration)
                .status(SpanStatus.OK)
            ).join();
            
            return result;
        } catch (Exception e) {
            double duration = (System.nanoTime() - start) / 1_000_000.0;
            
            sendSpan(SpanType.CHAIN, name, SpanData.builder()
                .durationMs(duration)
                .status(SpanStatus.ERROR)
                .isError(true)
                .errorMessage(e.getMessage())
            ).join();
            
            throw e;
        }
    }
    
    /**
     * Trace an agent call.
     */
    public <T> T traceAgent(String name, String agentName, String agentType,
                            Supplier<T> operation) {
        newTrace();
        long start = System.nanoTime();
        
        try {
            T result = operation.get();
            double duration = (System.nanoTime() - start) / 1_000_000.0;
            
            sendSpan(SpanType.AGENT, name, SpanData.builder()
                .agentName(agentName)
                .agentType(agentType)
                .durationMs(duration)
                .status(SpanStatus.OK)
            ).join();
            
            return result;
        } catch (Exception e) {
            double duration = (System.nanoTime() - start) / 1_000_000.0;
            
            sendSpan(SpanType.AGENT, name, SpanData.builder()
                .agentName(agentName)
                .agentType(agentType)
                .durationMs(duration)
                .status(SpanStatus.ERROR)
                .isError(true)
                .errorMessage(e.getMessage())
            ).join();
            
            throw e;
        }
    }
    
    // Getters
    public String getWorkflowName() { return workflowName; }
    public String getServiceName() { return serviceName; }
    public BaseExporter getExporter() { return exporter; }
    
    // Singleton access
    public static GenAITelemetry getInstance() {
        if (instance == null) {
            throw new IllegalStateException("Call setupTelemetry() first");
        }
        return instance;
    }
    
    public static GenAITelemetry setupTelemetry(String workflowName, BaseExporter exporter) {
        return setupTelemetry(workflowName, null, exporter);
    }
    
    public static GenAITelemetry setupTelemetry(String workflowName, String serviceName,
                                                 BaseExporter exporter) {
        instance = new GenAITelemetry(workflowName, serviceName, exporter);
        instance.start();
        return instance;
    }
    
    public static Builder builder() {
        return new Builder();
    }
    
    public static class Builder {
        private String workflowName;
        private String serviceName;
        private BaseExporter exporter;
        
        public Builder workflowName(String workflowName) {
            this.workflowName = workflowName;
            return this;
        }
        
        public Builder serviceName(String serviceName) {
            this.serviceName = serviceName;
            return this;
        }
        
        public Builder exporter(BaseExporter exporter) {
            this.exporter = exporter;
            return this;
        }
        
        public GenAITelemetry build() {
            if (workflowName == null) {
                throw new IllegalArgumentException("workflowName is required");
            }
            if (exporter == null) {
                throw new IllegalArgumentException("exporter is required");
            }
            instance = new GenAITelemetry(workflowName, serviceName, exporter);
            return instance;
        }
    }
}
