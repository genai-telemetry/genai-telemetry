# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.3] - 2024-12-23

### Fixed
- Fixed token extraction to work even when returning `response.choices[0].message.content`
- Added automatic OpenAI/Anthropic client response interception

### Added
- Added `extract_content` parameter to `@trace_llm` decorator to automatically extract content while preserving token counts
- Added helper functions `extract_tokens_from_response()` and `extract_content_from_response()`

## [1.0.2] - 2024-12-15

### Added
- AWS CloudWatch Logs exporter
- File exporter with rotation support
- Multi-exporter for sending to multiple backends

### Changed
- Improved batch processing performance
- Better error handling in all exporters

## [1.0.1] - 2024-12-01

### Added
- Prometheus Push Gateway exporter
- Grafana Loki exporter
- Health check methods for all exporters

### Fixed
- Thread safety issues in batch processing
- Memory leak in long-running applications

## [1.0.0] - 2024-11-15

### Added
- Initial release
- Splunk HEC exporter
- Elasticsearch exporter
- OpenTelemetry (OTLP) exporter
- Datadog exporter
- Console exporter for development
- Decorators: `@trace_llm`, `@trace_embedding`, `@trace_retrieval`, `@trace_tool`, `@trace_chain`, `@trace_agent`
- Automatic token extraction from OpenAI and Anthropic responses
- Batching and async flushing support
- Context manager for manual span creation
