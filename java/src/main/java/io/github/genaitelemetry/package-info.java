/**
 * GenAI Telemetry - Observability SDK for LLM Applications
 * 
 * <p>A platform-agnostic telemetry library for tracing GenAI/LLM applications.
 * Supports multiple backends: Splunk, Elasticsearch, OpenTelemetry, Datadog,
 * Prometheus, Grafana Loki, AWS CloudWatch, and more.
 * 
 * <h2>Quick Start</h2>
 * <pre>{@code
 * import io.github.genaitelemetry.GenAITelemetrySDK;
 * import io.github.genaitelemetry.core.GenAITelemetry;
 * import io.github.genaitelemetry.exporters.SplunkHECExporter;
 * 
 * // Initialize telemetry
 * GenAITelemetry telemetry = GenAITelemetry.builder()
 *     .workflowName("my-chatbot")
 *     .exporter(SplunkHECExporter.builder()
 *         .hecUrl("http://splunk:8088")
 *         .hecToken("your-token")
 *         .build())
 *     .build();
 * 
 * telemetry.start();
 * 
 * // Trace an LLM call
 * String result = telemetry.traceLLM("chat", "gpt-4o", "openai", () -> {
 *     return callOpenAI(message);
 * });
 * 
 * // Clean up
 * telemetry.stop();
 * }</pre>
 * 
 * @author Kamal Singh Bisht
 * @version 1.0.3
 */
package io.github.genaitelemetry;
