/**
 * Telemetry exporters for various backends.
 * 
 * <p>This package contains exporters for sending telemetry data to various
 * observability platforms:
 * <ul>
 *   <li>{@link io.github.genaitelemetry.exporters.SplunkHECExporter} - Splunk HTTP Event Collector</li>
 *   <li>{@link io.github.genaitelemetry.exporters.ElasticsearchExporter} - Elasticsearch</li>
 *   <li>{@link io.github.genaitelemetry.exporters.OTLPExporter} - OpenTelemetry Protocol</li>
 *   <li>{@link io.github.genaitelemetry.exporters.DatadogExporter} - Datadog</li>
 *   <li>{@link io.github.genaitelemetry.exporters.PrometheusExporter} - Prometheus Push Gateway</li>
 *   <li>{@link io.github.genaitelemetry.exporters.LokiExporter} - Grafana Loki</li>
 *   <li>{@link io.github.genaitelemetry.exporters.CloudWatchExporter} - AWS CloudWatch Logs</li>
 *   <li>{@link io.github.genaitelemetry.exporters.ConsoleExporter} - Console output</li>
 *   <li>{@link io.github.genaitelemetry.exporters.FileExporter} - File output (JSONL)</li>
 *   <li>{@link io.github.genaitelemetry.exporters.MultiExporter} - Multiple exporters</li>
 * </ul>
 */
package io.github.genaitelemetry.exporters;
