package io.github.genaitelemetry.core;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.time.Instant;
import java.util.HashMap;
import java.util.Map;

/**
 * Represents the data for a single span in a trace.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class SpanData {
    
    @JsonProperty("trace_id")
    private String traceId;
    
    @JsonProperty("span_id")
    private String spanId;
    
    @JsonProperty("parent_span_id")
    private String parentSpanId;
    
    @JsonProperty("name")
    private String name;
    
    @JsonProperty("span_type")
    private String spanType;
    
    @JsonProperty("workflow_name")
    private String workflowName;
    
    @JsonProperty("timestamp")
    private String timestamp;
    
    @JsonProperty("duration_ms")
    private double durationMs;
    
    @JsonProperty("status")
    private String status = "OK";
    
    @JsonProperty("is_error")
    private int isError = 0;
    
    @JsonProperty("error_message")
    private String errorMessage;
    
    @JsonProperty("error_type")
    private String errorType;
    
    // LLM fields
    @JsonProperty("model_name")
    private String modelName;
    
    @JsonProperty("model_provider")
    private String modelProvider;
    
    @JsonProperty("input_tokens")
    private Integer inputTokens;
    
    @JsonProperty("output_tokens")
    private Integer outputTokens;
    
    @JsonProperty("total_tokens")
    private Integer totalTokens;
    
    @JsonProperty("temperature")
    private Double temperature;
    
    @JsonProperty("max_tokens")
    private Integer maxTokens;
    
    // Embedding fields
    @JsonProperty("embedding_model")
    private String embeddingModel;
    
    @JsonProperty("embedding_dimensions")
    private Integer embeddingDimensions;
    
    // Retrieval fields
    @JsonProperty("vector_store")
    private String vectorStore;
    
    @JsonProperty("documents_retrieved")
    private Integer documentsRetrieved;
    
    @JsonProperty("relevance_score")
    private Double relevanceScore;
    
    // Tool fields
    @JsonProperty("tool_name")
    private String toolName;
    
    // Agent fields
    @JsonProperty("agent_name")
    private String agentName;
    
    @JsonProperty("agent_type")
    private String agentType;
    
    // Custom attributes
    private Map<String, Object> customAttributes = new HashMap<>();
    
    public SpanData() {
        this.timestamp = Instant.now().toString();
    }
    
    // Builder pattern
    public static Builder builder() {
        return new Builder();
    }
    
    public static class Builder {
        private final SpanData spanData = new SpanData();
        
        public Builder traceId(String traceId) {
            spanData.traceId = traceId;
            return this;
        }
        
        public Builder spanId(String spanId) {
            spanData.spanId = spanId;
            return this;
        }
        
        public Builder parentSpanId(String parentSpanId) {
            spanData.parentSpanId = parentSpanId;
            return this;
        }
        
        public Builder name(String name) {
            spanData.name = name;
            return this;
        }
        
        public Builder spanType(SpanType spanType) {
            spanData.spanType = spanType.name();
            return this;
        }
        
        public Builder spanType(String spanType) {
            spanData.spanType = spanType;
            return this;
        }
        
        public Builder workflowName(String workflowName) {
            spanData.workflowName = workflowName;
            return this;
        }
        
        public Builder timestamp(String timestamp) {
            spanData.timestamp = timestamp;
            return this;
        }
        
        public Builder durationMs(double durationMs) {
            spanData.durationMs = durationMs;
            return this;
        }
        
        public Builder status(SpanStatus status) {
            spanData.status = status.name();
            return this;
        }
        
        public Builder isError(boolean isError) {
            spanData.isError = isError ? 1 : 0;
            return this;
        }
        
        public Builder errorMessage(String errorMessage) {
            spanData.errorMessage = errorMessage;
            return this;
        }
        
        public Builder errorType(String errorType) {
            spanData.errorType = errorType;
            return this;
        }
        
        public Builder modelName(String modelName) {
            spanData.modelName = modelName;
            return this;
        }
        
        public Builder modelProvider(String modelProvider) {
            spanData.modelProvider = modelProvider;
            return this;
        }
        
        public Builder inputTokens(int inputTokens) {
            spanData.inputTokens = inputTokens;
            return this;
        }
        
        public Builder outputTokens(int outputTokens) {
            spanData.outputTokens = outputTokens;
            return this;
        }
        
        public Builder totalTokens(int totalTokens) {
            spanData.totalTokens = totalTokens;
            return this;
        }
        
        public Builder temperature(double temperature) {
            spanData.temperature = temperature;
            return this;
        }
        
        public Builder maxTokens(int maxTokens) {
            spanData.maxTokens = maxTokens;
            return this;
        }
        
        public Builder embeddingModel(String embeddingModel) {
            spanData.embeddingModel = embeddingModel;
            return this;
        }
        
        public Builder embeddingDimensions(int embeddingDimensions) {
            spanData.embeddingDimensions = embeddingDimensions;
            return this;
        }
        
        public Builder vectorStore(String vectorStore) {
            spanData.vectorStore = vectorStore;
            return this;
        }
        
        public Builder documentsRetrieved(int documentsRetrieved) {
            spanData.documentsRetrieved = documentsRetrieved;
            return this;
        }
        
        public Builder relevanceScore(double relevanceScore) {
            spanData.relevanceScore = relevanceScore;
            return this;
        }
        
        public Builder toolName(String toolName) {
            spanData.toolName = toolName;
            return this;
        }
        
        public Builder agentName(String agentName) {
            spanData.agentName = agentName;
            return this;
        }
        
        public Builder agentType(String agentType) {
            spanData.agentType = agentType;
            return this;
        }
        
        public Builder attribute(String key, Object value) {
            spanData.customAttributes.put(key, value);
            return this;
        }
        
        public SpanData build() {
            // Calculate total tokens if not set
            if (spanData.totalTokens == null && 
                spanData.inputTokens != null && 
                spanData.outputTokens != null) {
                spanData.totalTokens = spanData.inputTokens + spanData.outputTokens;
            }
            return spanData;
        }
    }
    
    // Getters
    public String getTraceId() { return traceId; }
    public String getSpanId() { return spanId; }
    public String getParentSpanId() { return parentSpanId; }
    public String getName() { return name; }
    public String getSpanType() { return spanType; }
    public String getWorkflowName() { return workflowName; }
    public String getTimestamp() { return timestamp; }
    public double getDurationMs() { return durationMs; }
    public String getStatus() { return status; }
    public int getIsError() { return isError; }
    public String getErrorMessage() { return errorMessage; }
    public String getErrorType() { return errorType; }
    public String getModelName() { return modelName; }
    public String getModelProvider() { return modelProvider; }
    public Integer getInputTokens() { return inputTokens; }
    public Integer getOutputTokens() { return outputTokens; }
    public Integer getTotalTokens() { return totalTokens; }
    public Double getTemperature() { return temperature; }
    public Integer getMaxTokens() { return maxTokens; }
    public String getEmbeddingModel() { return embeddingModel; }
    public Integer getEmbeddingDimensions() { return embeddingDimensions; }
    public String getVectorStore() { return vectorStore; }
    public Integer getDocumentsRetrieved() { return documentsRetrieved; }
    public Double getRelevanceScore() { return relevanceScore; }
    public String getToolName() { return toolName; }
    public String getAgentName() { return agentName; }
    public String getAgentType() { return agentType; }
    public Map<String, Object> getCustomAttributes() { return customAttributes; }
    
    // Setters
    public void setTraceId(String traceId) { this.traceId = traceId; }
    public void setSpanId(String spanId) { this.spanId = spanId; }
    public void setParentSpanId(String parentSpanId) { this.parentSpanId = parentSpanId; }
    public void setName(String name) { this.name = name; }
    public void setSpanType(String spanType) { this.spanType = spanType; }
    public void setWorkflowName(String workflowName) { this.workflowName = workflowName; }
    public void setTimestamp(String timestamp) { this.timestamp = timestamp; }
    public void setDurationMs(double durationMs) { this.durationMs = durationMs; }
    public void setStatus(String status) { this.status = status; }
    public void setIsError(int isError) { this.isError = isError; }
    public void setErrorMessage(String errorMessage) { this.errorMessage = errorMessage; }
    public void setErrorType(String errorType) { this.errorType = errorType; }
    public void setModelName(String modelName) { this.modelName = modelName; }
    public void setModelProvider(String modelProvider) { this.modelProvider = modelProvider; }
    public void setInputTokens(Integer inputTokens) { this.inputTokens = inputTokens; }
    public void setOutputTokens(Integer outputTokens) { this.outputTokens = outputTokens; }
    public void setTotalTokens(Integer totalTokens) { this.totalTokens = totalTokens; }
    public void setTemperature(Double temperature) { this.temperature = temperature; }
    public void setMaxTokens(Integer maxTokens) { this.maxTokens = maxTokens; }
    public void setEmbeddingModel(String embeddingModel) { this.embeddingModel = embeddingModel; }
    public void setEmbeddingDimensions(Integer embeddingDimensions) { this.embeddingDimensions = embeddingDimensions; }
    public void setVectorStore(String vectorStore) { this.vectorStore = vectorStore; }
    public void setDocumentsRetrieved(Integer documentsRetrieved) { this.documentsRetrieved = documentsRetrieved; }
    public void setRelevanceScore(Double relevanceScore) { this.relevanceScore = relevanceScore; }
    public void setToolName(String toolName) { this.toolName = toolName; }
    public void setAgentName(String agentName) { this.agentName = agentName; }
    public void setAgentType(String agentType) { this.agentType = agentType; }
    
    public void setAttribute(String key, Object value) {
        this.customAttributes.put(key, value);
    }
}
