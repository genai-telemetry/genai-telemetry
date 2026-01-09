package io.github.genaitelemetry.exporters;

import io.github.genaitelemetry.core.SpanData;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.*;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Exporter that sends metrics to Prometheus Push Gateway.
 */
public class PrometheusExporter implements BaseExporter {
    
    private static final Logger logger = LoggerFactory.getLogger(PrometheusExporter.class);
    
    private final String pushgatewayUrl;
    private final String jobName;
    private final HttpClient httpClient;
    
    // Metrics storage
    private final Map<String, List<Double>> llmDurations = new ConcurrentHashMap<>();
    private final Map<String, int[]> llmTokens = new ConcurrentHashMap<>();
    private final Map<String, Integer> llmErrors = new ConcurrentHashMap<>();
    private final Map<String, List<Double>> embeddingDurations = new ConcurrentHashMap<>();
    private final Map<String, List<Double>> retrieverDurations = new ConcurrentHashMap<>();
    private final Map<String, List<Integer>> retrieverDocs = new ConcurrentHashMap<>();
    
    public PrometheusExporter(String pushgatewayUrl, String jobName) {
        this.pushgatewayUrl = pushgatewayUrl.replaceAll("/$", "");
        this.jobName = jobName;
        this.httpClient = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(10))
            .build();
    }
    
    private void updateMetrics(SpanData span) {
        String key = (span.getWorkflowName() != null ? span.getWorkflowName() : "default") 
            + ":" + (span.getModelName() != null ? span.getModelName() : span.getName());
        
        switch (span.getSpanType()) {
            case "LLM":
                llmDurations.computeIfAbsent(key, k -> new ArrayList<>()).add(span.getDurationMs());
                
                int[] tokens = llmTokens.computeIfAbsent(key, k -> new int[]{0, 0});
                if (span.getInputTokens() != null) tokens[0] += span.getInputTokens();
                if (span.getOutputTokens() != null) tokens[1] += span.getOutputTokens();
                
                if (span.getIsError() == 1) {
                    llmErrors.merge(key, 1, Integer::sum);
                }
                break;
                
            case "EMBEDDING":
                embeddingDurations.computeIfAbsent(key, k -> new ArrayList<>()).add(span.getDurationMs());
                break;
                
            case "RETRIEVER":
                String rKey = (span.getWorkflowName() != null ? span.getWorkflowName() : "default")
                    + ":" + (span.getVectorStore() != null ? span.getVectorStore() : span.getName());
                retrieverDurations.computeIfAbsent(rKey, k -> new ArrayList<>()).add(span.getDurationMs());
                if (span.getDocumentsRetrieved() != null) {
                    retrieverDocs.computeIfAbsent(rKey, k -> new ArrayList<>()).add(span.getDocumentsRetrieved());
                }
                break;
        }
    }
    
    private String buildMetricsPayload() {
        StringBuilder sb = new StringBuilder();
        
        // LLM duration
        sb.append("# HELP genai_llm_duration_seconds LLM call duration\n");
        sb.append("# TYPE genai_llm_duration_seconds summary\n");
        for (Map.Entry<String, List<Double>> entry : llmDurations.entrySet()) {
            String[] parts = entry.getKey().split(":");
            String labels = String.format("workflow=\"%s\",model=\"%s\"", parts[0], parts.length > 1 ? parts[1] : "unknown");
            double sum = entry.getValue().stream().mapToDouble(Double::doubleValue).sum() / 1000.0;
            sb.append(String.format("genai_llm_duration_seconds_sum{%s} %.3f\n", labels, sum));
            sb.append(String.format("genai_llm_duration_seconds_count{%s} %d\n", labels, entry.getValue().size()));
        }
        
        // LLM tokens
        sb.append("# HELP genai_llm_tokens_total Total tokens used\n");
        sb.append("# TYPE genai_llm_tokens_total counter\n");
        for (Map.Entry<String, int[]> entry : llmTokens.entrySet()) {
            String[] parts = entry.getKey().split(":");
            String labels = String.format("workflow=\"%s\",model=\"%s\"", parts[0], parts.length > 1 ? parts[1] : "unknown");
            sb.append(String.format("genai_llm_tokens_total{%s,type=\"input\"} %d\n", labels, entry.getValue()[0]));
            sb.append(String.format("genai_llm_tokens_total{%s,type=\"output\"} %d\n", labels, entry.getValue()[1]));
        }
        
        // LLM errors
        sb.append("# HELP genai_llm_errors_total Total LLM errors\n");
        sb.append("# TYPE genai_llm_errors_total counter\n");
        for (Map.Entry<String, Integer> entry : llmErrors.entrySet()) {
            String[] parts = entry.getKey().split(":");
            String labels = String.format("workflow=\"%s\",model=\"%s\"", parts[0], parts.length > 1 ? parts[1] : "unknown");
            sb.append(String.format("genai_llm_errors_total{%s} %d\n", labels, entry.getValue()));
        }
        
        // Embedding duration
        sb.append("# HELP genai_embedding_duration_seconds Embedding call duration\n");
        sb.append("# TYPE genai_embedding_duration_seconds summary\n");
        for (Map.Entry<String, List<Double>> entry : embeddingDurations.entrySet()) {
            String[] parts = entry.getKey().split(":");
            String labels = String.format("workflow=\"%s\",model=\"%s\"", parts[0], parts.length > 1 ? parts[1] : "unknown");
            double sum = entry.getValue().stream().mapToDouble(Double::doubleValue).sum() / 1000.0;
            sb.append(String.format("genai_embedding_duration_seconds_sum{%s} %.3f\n", labels, sum));
            sb.append(String.format("genai_embedding_duration_seconds_count{%s} %d\n", labels, entry.getValue().size()));
        }
        
        // Retriever duration
        sb.append("# HELP genai_retriever_duration_seconds Retriever call duration\n");
        sb.append("# TYPE genai_retriever_duration_seconds summary\n");
        for (Map.Entry<String, List<Double>> entry : retrieverDurations.entrySet()) {
            String[] parts = entry.getKey().split(":");
            String labels = String.format("workflow=\"%s\",vector_store=\"%s\"", parts[0], parts.length > 1 ? parts[1] : "unknown");
            double sum = entry.getValue().stream().mapToDouble(Double::doubleValue).sum() / 1000.0;
            sb.append(String.format("genai_retriever_duration_seconds_sum{%s} %.3f\n", labels, sum));
            sb.append(String.format("genai_retriever_duration_seconds_count{%s} %d\n", labels, entry.getValue().size()));
        }
        
        // Retriever documents
        sb.append("# HELP genai_retriever_documents_total Documents retrieved\n");
        sb.append("# TYPE genai_retriever_documents_total counter\n");
        for (Map.Entry<String, List<Integer>> entry : retrieverDocs.entrySet()) {
            String[] parts = entry.getKey().split(":");
            String labels = String.format("workflow=\"%s\",vector_store=\"%s\"", parts[0], parts.length > 1 ? parts[1] : "unknown");
            int total = entry.getValue().stream().mapToInt(Integer::intValue).sum();
            sb.append(String.format("genai_retriever_documents_total{%s} %d\n", labels, total));
        }
        
        return sb.toString();
    }
    
    @Override
    public CompletableFuture<Boolean> export(SpanData spanData) {
        return CompletableFuture.supplyAsync(() -> {
            try {
                updateMetrics(spanData);
                String payload = buildMetricsPayload();
                
                HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(pushgatewayUrl + "/metrics/job/" + jobName))
                    .header("Content-Type", "text/plain")
                    .PUT(HttpRequest.BodyPublishers.ofString(payload))
                    .build();
                
                HttpResponse<String> response = httpClient.send(request,
                    HttpResponse.BodyHandlers.ofString());
                
                return response.statusCode() == 200 || response.statusCode() == 202;
            } catch (Exception e) {
                logger.error("Prometheus Push Gateway error: {}", e.getMessage());
                return false;
            }
        });
    }
    
    @Override
    public CompletableFuture<Boolean> healthCheck() {
        return CompletableFuture.supplyAsync(() -> {
            try {
                HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(pushgatewayUrl + "/-/healthy"))
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
        private String pushgatewayUrl = "http://localhost:9091";
        private String jobName = "genai_telemetry";
        
        public Builder pushgatewayUrl(String pushgatewayUrl) {
            this.pushgatewayUrl = pushgatewayUrl;
            return this;
        }
        
        public Builder jobName(String jobName) {
            this.jobName = jobName;
            return this;
        }
        
        public PrometheusExporter build() {
            return new PrometheusExporter(pushgatewayUrl, jobName);
        }
    }
}
