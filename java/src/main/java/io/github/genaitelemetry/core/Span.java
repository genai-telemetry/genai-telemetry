package io.github.genaitelemetry.core;

import java.time.Instant;
import java.util.HashMap;
import java.util.Map;

/**
 * Represents a single span in a trace.
 * Tracks timing, status, and attributes for a specific operation.
 */
public class Span {
    
    private final String traceId;
    private final String spanId;
    private final String name;
    private final SpanType spanType;
    private final String workflowName;
    private final String parentSpanId;
    private final long startTimeNanos;
    
    private Long endTimeNanos;
    private Double durationMs;
    private SpanStatus status = SpanStatus.OK;
    private boolean isError = false;
    private String errorMessage;
    private String errorType;
    
    // LLM fields
    private String modelName;
    private String modelProvider;
    private int inputTokens = 0;
    private int outputTokens = 0;
    private Double temperature;
    private Integer maxTokens;
    
    // Embedding fields
    private String embeddingModel;
    private Integer embeddingDimensions;
    
    // Retrieval fields
    private String vectorStore;
    private int documentsRetrieved = 0;
    private Double relevanceScore;
    
    // Tool fields
    private String toolName;
    
    // Agent fields
    private String agentName;
    private String agentType;
    
    // Custom attributes
    private final Map<String, Object> attributes = new HashMap<>();
    
    /**
     * Create a new span.
     */
    public Span(String traceId, String spanId, String name, SpanType spanType, 
                String workflowName, String parentSpanId) {
        this.traceId = traceId;
        this.spanId = spanId;
        this.name = name;
        this.spanType = spanType;
        this.workflowName = workflowName;
        this.parentSpanId = parentSpanId;
        this.startTimeNanos = System.nanoTime();
    }
    
    /**
     * Set a custom attribute.
     */
    public Span setAttribute(String key, Object value) {
        this.attributes.put(key, value);
        return this;
    }
    
    /**
     * Set error information.
     */
    public Span setError(Throwable error) {
        this.status = SpanStatus.ERROR;
        this.isError = true;
        this.errorMessage = error.getMessage();
        this.errorType = error.getClass().getSimpleName();
        return this;
    }
    
    /**
     * Finish the span and calculate duration.
     */
    public void finish() {
        finish(null);
    }
    
    /**
     * Finish the span with an optional error.
     */
    public void finish(Throwable error) {
        this.endTimeNanos = System.nanoTime();
        this.durationMs = (this.endTimeNanos - this.startTimeNanos) / 1_000_000.0;
        this.durationMs = Math.round(this.durationMs * 100.0) / 100.0;
        
        if (error != null) {
            setError(error);
        }
    }
    
    /**
     * Convert span to SpanData for export.
     */
    public SpanData toSpanData() {
        SpanData.Builder builder = SpanData.builder()
            .traceId(traceId)
            .spanId(spanId)
            .name(name)
            .spanType(spanType)
            .workflowName(workflowName)
            .parentSpanId(parentSpanId)
            .timestamp(Instant.now().toString())
            .durationMs(durationMs != null ? durationMs : 0)
            .status(status)
            .isError(isError);
        
        if (errorMessage != null) builder.errorMessage(errorMessage);
        if (errorType != null) builder.errorType(errorType);
        if (modelName != null) builder.modelName(modelName);
        if (modelProvider != null) builder.modelProvider(modelProvider);
        
        if (spanType == SpanType.LLM) {
            builder.inputTokens(inputTokens);
            builder.outputTokens(outputTokens);
            builder.totalTokens(inputTokens + outputTokens);
        } else {
            if (inputTokens > 0) builder.inputTokens(inputTokens);
            if (outputTokens > 0) builder.outputTokens(outputTokens);
        }
        
        if (temperature != null) builder.temperature(temperature);
        if (maxTokens != null) builder.maxTokens(maxTokens);
        if (embeddingModel != null) builder.embeddingModel(embeddingModel);
        if (embeddingDimensions != null) builder.embeddingDimensions(embeddingDimensions);
        if (vectorStore != null) builder.vectorStore(vectorStore);
        if (documentsRetrieved > 0) builder.documentsRetrieved(documentsRetrieved);
        if (relevanceScore != null) builder.relevanceScore(relevanceScore);
        if (toolName != null) builder.toolName(toolName);
        if (agentName != null) builder.agentName(agentName);
        if (agentType != null) builder.agentType(agentType);
        
        for (Map.Entry<String, Object> entry : attributes.entrySet()) {
            builder.attribute(entry.getKey(), entry.getValue());
        }
        
        return builder.build();
    }
    
    // Getters and setters
    public String getTraceId() { return traceId; }
    public String getSpanId() { return spanId; }
    public String getName() { return name; }
    public SpanType getSpanType() { return spanType; }
    public String getWorkflowName() { return workflowName; }
    public String getParentSpanId() { return parentSpanId; }
    public Double getDurationMs() { return durationMs; }
    public SpanStatus getStatus() { return status; }
    public boolean isError() { return isError; }
    public String getErrorMessage() { return errorMessage; }
    public String getErrorType() { return errorType; }
    
    public String getModelName() { return modelName; }
    public Span setModelName(String modelName) { this.modelName = modelName; return this; }
    
    public String getModelProvider() { return modelProvider; }
    public Span setModelProvider(String modelProvider) { this.modelProvider = modelProvider; return this; }
    
    public int getInputTokens() { return inputTokens; }
    public Span setInputTokens(int inputTokens) { this.inputTokens = inputTokens; return this; }
    
    public int getOutputTokens() { return outputTokens; }
    public Span setOutputTokens(int outputTokens) { this.outputTokens = outputTokens; return this; }
    
    public Double getTemperature() { return temperature; }
    public Span setTemperature(Double temperature) { this.temperature = temperature; return this; }
    
    public Integer getMaxTokens() { return maxTokens; }
    public Span setMaxTokens(Integer maxTokens) { this.maxTokens = maxTokens; return this; }
    
    public String getEmbeddingModel() { return embeddingModel; }
    public Span setEmbeddingModel(String embeddingModel) { this.embeddingModel = embeddingModel; return this; }
    
    public Integer getEmbeddingDimensions() { return embeddingDimensions; }
    public Span setEmbeddingDimensions(Integer embeddingDimensions) { this.embeddingDimensions = embeddingDimensions; return this; }
    
    public String getVectorStore() { return vectorStore; }
    public Span setVectorStore(String vectorStore) { this.vectorStore = vectorStore; return this; }
    
    public int getDocumentsRetrieved() { return documentsRetrieved; }
    public Span setDocumentsRetrieved(int documentsRetrieved) { this.documentsRetrieved = documentsRetrieved; return this; }
    
    public Double getRelevanceScore() { return relevanceScore; }
    public Span setRelevanceScore(Double relevanceScore) { this.relevanceScore = relevanceScore; return this; }
    
    public String getToolName() { return toolName; }
    public Span setToolName(String toolName) { this.toolName = toolName; return this; }
    
    public String getAgentName() { return agentName; }
    public Span setAgentName(String agentName) { this.agentName = agentName; return this; }
    
    public String getAgentType() { return agentType; }
    public Span setAgentType(String agentType) { this.agentType = agentType; return this; }
}
