package io.github.genaitelemetry;

import io.github.genaitelemetry.core.*;
import io.github.genaitelemetry.exporters.*;
import io.github.genaitelemetry.utils.*;
import org.junit.jupiter.api.*;
import org.mockito.*;

import java.util.*;
import java.util.concurrent.*;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class GenAITelemetryTest {
    
    private GenAITelemetry telemetry;
    private BaseExporter mockExporter;
    
    @BeforeEach
    void setUp() {
        mockExporter = mock(BaseExporter.class);
        when(mockExporter.export(any())).thenReturn(CompletableFuture.completedFuture(true));
        
        telemetry = GenAITelemetry.builder()
            .workflowName("test-workflow")
            .exporter(mockExporter)
            .build();
    }
    
    @Test
    void testTraceIdGeneration() {
        String traceId = telemetry.getTraceId();
        
        assertNotNull(traceId);
        assertEquals(32, traceId.length());
    }
    
    @Test
    void testNewTrace() {
        String oldTraceId = telemetry.getTraceId();
        String newTraceId = telemetry.newTrace();
        
        assertNotEquals(oldTraceId, newTraceId);
        assertEquals(32, newTraceId.length());
        assertEquals(newTraceId, telemetry.getTraceId());
    }
    
    @Test
    void testTraceLLM() {
        Map<String, Object> result = telemetry.traceLLM(
            "test-chat",
            "gpt-4o",
            "openai",
            () -> {
                Map<String, Object> response = new HashMap<>();
                Map<String, Object> usage = new HashMap<>();
                usage.put("prompt_tokens", 100);
                usage.put("completion_tokens", 50);
                response.put("usage", usage);
                return response;
            }
        );
        
        assertNotNull(result);
        verify(mockExporter, times(1)).export(argThat(span -> 
            "LLM".equals(span.getSpanType()) &&
            "test-chat".equals(span.getName()) &&
            "gpt-4o".equals(span.getModelName())
        ));
    }
    
    @Test
    void testTraceLLMError() {
        RuntimeException expectedException = new RuntimeException("API Error");
        
        assertThrows(RuntimeException.class, () -> {
            telemetry.traceLLM("error-chat", "gpt-4o", "openai", () -> {
                throw expectedException;
            });
        });
        
        verify(mockExporter, times(1)).export(argThat(span ->
            span.getIsError() == 1 &&
            "API Error".equals(span.getErrorMessage())
        ));
    }
    
    @Test
    void testTraceEmbedding() {
        telemetry.traceEmbedding("test-embed", "text-embedding-3-small", () -> {
            Map<String, Object> response = new HashMap<>();
            Map<String, Object> usage = new HashMap<>();
            usage.put("prompt_tokens", 10);
            response.put("usage", usage);
            return response;
        });
        
        verify(mockExporter, times(1)).export(argThat(span ->
            "EMBEDDING".equals(span.getSpanType()) &&
            "text-embedding-3-small".equals(span.getEmbeddingModel())
        ));
    }
    
    @Test
    void testTraceTool() {
        String result = telemetry.traceTool("test-tool", "web_search", () -> "search results");
        
        assertEquals("search results", result);
        verify(mockExporter, times(1)).export(argThat(span ->
            "TOOL".equals(span.getSpanType()) &&
            "web_search".equals(span.getToolName())
        ));
    }
    
    @Test
    void testTraceChain() {
        String result = telemetry.traceChain("test-chain", () -> "chain result");
        
        assertEquals("chain result", result);
        verify(mockExporter, times(1)).export(argThat(span ->
            "CHAIN".equals(span.getSpanType())
        ));
    }
    
    @Test
    void testManualSpan() throws Exception {
        Span span = telemetry.startSpan("manual-span", SpanType.TOOL);
        span.setToolName("custom-tool");
        span.setAttribute("custom_key", "custom_value");
        
        Thread.sleep(10);
        
        telemetry.endSpan().get();
        
        verify(mockExporter, times(1)).export(argThat(spanData ->
            "manual-span".equals(spanData.getName()) &&
            "custom-tool".equals(spanData.getToolName())
        ));
    }
}

class SpanTest {
    
    @Test
    void testSpanCreation() {
        Span span = new Span(
            "trace123",
            "span456",
            "test-span",
            SpanType.LLM,
            "test-workflow",
            null
        );
        
        assertEquals("trace123", span.getTraceId());
        assertEquals("span456", span.getSpanId());
        assertEquals("test-span", span.getName());
        assertEquals(SpanType.LLM, span.getSpanType());
        assertEquals(SpanStatus.OK, span.getStatus());
        assertFalse(span.isError());
    }
    
    @Test
    void testSpanFinish() throws Exception {
        Span span = new Span("trace", "span", "test", SpanType.LLM, "workflow", null);
        
        Thread.sleep(10);
        span.finish();
        
        assertNotNull(span.getDurationMs());
        assertTrue(span.getDurationMs() >= 10);
    }
    
    @Test
    void testSpanError() {
        Span span = new Span("trace", "span", "test", SpanType.LLM, "workflow", null);
        span.setError(new RuntimeException("Test error"));
        
        assertEquals(SpanStatus.ERROR, span.getStatus());
        assertTrue(span.isError());
        assertEquals("Test error", span.getErrorMessage());
        assertEquals("RuntimeException", span.getErrorType());
    }
    
    @Test
    void testSpanToSpanData() {
        Span span = new Span("trace123", "span456", "test", SpanType.LLM, "workflow", null);
        span.setModelName("gpt-4o");
        span.setModelProvider("openai");
        span.setInputTokens(100);
        span.setOutputTokens(50);
        span.finish();
        
        SpanData data = span.toSpanData();
        
        assertEquals("trace123", data.getTraceId());
        assertEquals("span456", data.getSpanId());
        assertEquals("test", data.getName());
        assertEquals("LLM", data.getSpanType());
        assertEquals("gpt-4o", data.getModelName());
        assertEquals("openai", data.getModelProvider());
        assertEquals(100, data.getInputTokens());
        assertEquals(50, data.getOutputTokens());
        assertEquals(150, data.getTotalTokens());
    }
}

class TokenExtractorTest {
    
    @Test
    void testExtractOpenAITokens() {
        Map<String, Object> usage = new HashMap<>();
        usage.put("prompt_tokens", 100);
        usage.put("completion_tokens", 50);
        
        Map<String, Object> response = new HashMap<>();
        response.put("usage", usage);
        
        int[] tokens = TokenExtractor.extractTokens(response);
        
        assertEquals(100, tokens[0]);
        assertEquals(50, tokens[1]);
    }
    
    @Test
    void testExtractAnthropicTokens() {
        Map<String, Object> usage = new HashMap<>();
        usage.put("input_tokens", 80);
        usage.put("output_tokens", 40);
        
        Map<String, Object> response = new HashMap<>();
        response.put("usage", usage);
        
        int[] tokens = TokenExtractor.extractTokens(response);
        
        assertEquals(80, tokens[0]);
        assertEquals(40, tokens[1]);
    }
    
    @Test
    void testExtractNullResponse() {
        int[] tokens = TokenExtractor.extractTokens(null);
        
        assertEquals(0, tokens[0]);
        assertEquals(0, tokens[1]);
    }
    
    @Test
    void testExtractContentOpenAI() {
        Map<String, Object> message = new HashMap<>();
        message.put("content", "Hello, world!");
        
        Map<String, Object> choice = new HashMap<>();
        choice.put("message", message);
        
        Map<String, Object> response = new HashMap<>();
        response.put("choices", List.of(choice));
        
        String content = TokenExtractor.extractContent(response, "openai");
        
        assertEquals("Hello, world!", content);
    }
}

class IdGeneratorTest {
    
    @Test
    void testGenerateTraceId() {
        String traceId = IdGenerator.generateTraceId();
        
        assertNotNull(traceId);
        assertEquals(32, traceId.length());
        assertTrue(traceId.matches("[0-9a-f]+"));
    }
    
    @Test
    void testGenerateSpanId() {
        String spanId = IdGenerator.generateSpanId();
        
        assertNotNull(spanId);
        assertEquals(16, spanId.length());
        assertTrue(spanId.matches("[0-9a-f]+"));
    }
    
    @Test
    void testUniqueIds() {
        Set<String> ids = new HashSet<>();
        for (int i = 0; i < 1000; i++) {
            ids.add(IdGenerator.generateTraceId());
        }
        
        assertEquals(1000, ids.size());
    }
}

class ConsoleExporterTest {
    
    @Test
    void testExport() throws Exception {
        ConsoleExporter exporter = ConsoleExporter.builder()
            .colored(false)
            .build();
        
        SpanData span = SpanData.builder()
            .traceId("trace123")
            .spanId("span456")
            .name("test-span")
            .spanType(SpanType.LLM)
            .durationMs(100)
            .status(SpanStatus.OK)
            .build();
        
        boolean result = exporter.export(span).get();
        
        assertTrue(result);
    }
}

class MultiExporterTest {
    
    @Test
    void testExportToAll() throws Exception {
        BaseExporter exporter1 = mock(BaseExporter.class);
        BaseExporter exporter2 = mock(BaseExporter.class);
        
        when(exporter1.export(any())).thenReturn(CompletableFuture.completedFuture(true));
        when(exporter2.export(any())).thenReturn(CompletableFuture.completedFuture(true));
        
        MultiExporter multi = new MultiExporter(exporter1, exporter2);
        
        SpanData span = SpanData.builder()
            .traceId("trace")
            .spanId("span")
            .name("test")
            .spanType(SpanType.LLM)
            .build();
        
        boolean result = multi.export(span).get();
        
        assertTrue(result);
        verify(exporter1, times(1)).export(span);
        verify(exporter2, times(1)).export(span);
    }
    
    @Test
    void testPartialSuccess() throws Exception {
        BaseExporter exporter1 = mock(BaseExporter.class);
        BaseExporter exporter2 = mock(BaseExporter.class);
        
        when(exporter1.export(any())).thenReturn(CompletableFuture.completedFuture(true));
        when(exporter2.export(any())).thenReturn(CompletableFuture.completedFuture(false));
        
        MultiExporter multi = new MultiExporter(exporter1, exporter2);
        
        SpanData span = SpanData.builder()
            .traceId("trace")
            .spanId("span")
            .name("test")
            .spanType(SpanType.LLM)
            .build();
        
        boolean result = multi.export(span).get();
        
        assertTrue(result); // At least one succeeded
    }
}
