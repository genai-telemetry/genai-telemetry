package io.github.genaitelemetry.core;

/**
 * Types of spans supported by GenAI Telemetry.
 */
public enum SpanType {
    /** Large Language Model call */
    LLM,
    /** Embedding generation */
    EMBEDDING,
    /** Vector store retrieval */
    RETRIEVER,
    /** Tool/function call */
    TOOL,
    /** Chain/pipeline execution */
    CHAIN,
    /** Agent execution */
    AGENT
}
