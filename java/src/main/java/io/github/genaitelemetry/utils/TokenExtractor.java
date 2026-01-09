package io.github.genaitelemetry.utils;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.lang.reflect.Method;
import java.util.Map;

/**
 * Utility class for extracting token usage from LLM responses.
 */
public final class TokenExtractor {
    
    private static final ObjectMapper objectMapper = new ObjectMapper();
    
    private TokenExtractor() {
        // Utility class
    }
    
    /**
     * Extract input and output tokens from an LLM response.
     * 
     * @param response The response object from an LLM call
     * @return Array of [inputTokens, outputTokens]
     */
    public static int[] extractTokens(Object response) {
        if (response == null) {
            return new int[]{0, 0};
        }
        
        try {
            // Try to get usage via reflection (for SDK objects)
            Object usage = getUsageViaReflection(response);
            if (usage != null) {
                return extractFromUsage(usage);
            }
            
            // Try to convert to Map or JsonNode
            if (response instanceof Map) {
                return extractFromMap((Map<?, ?>) response);
            }
            
            if (response instanceof String) {
                JsonNode node = objectMapper.readTree((String) response);
                return extractFromJsonNode(node);
            }
            
            // Try to convert object to JSON
            JsonNode node = objectMapper.valueToTree(response);
            return extractFromJsonNode(node);
            
        } catch (Exception e) {
            return new int[]{0, 0};
        }
    }
    
    private static Object getUsageViaReflection(Object response) {
        try {
            Method getUsage = response.getClass().getMethod("getUsage");
            return getUsage.invoke(response);
        } catch (Exception e) {
            try {
                Method usage = response.getClass().getMethod("usage");
                return usage.invoke(response);
            } catch (Exception e2) {
                return null;
            }
        }
    }
    
    private static int[] extractFromUsage(Object usage) {
        int input = 0;
        int output = 0;
        
        try {
            // OpenAI format
            try {
                Method getPromptTokens = usage.getClass().getMethod("getPromptTokens");
                Object result = getPromptTokens.invoke(usage);
                if (result instanceof Number) {
                    input = ((Number) result).intValue();
                }
            } catch (Exception ignored) {}
            
            try {
                Method getCompletionTokens = usage.getClass().getMethod("getCompletionTokens");
                Object result = getCompletionTokens.invoke(usage);
                if (result instanceof Number) {
                    output = ((Number) result).intValue();
                }
            } catch (Exception ignored) {}
            
            // Anthropic format
            if (input == 0) {
                try {
                    Method getInputTokens = usage.getClass().getMethod("getInputTokens");
                    Object result = getInputTokens.invoke(usage);
                    if (result instanceof Number) {
                        input = ((Number) result).intValue();
                    }
                } catch (Exception ignored) {}
            }
            
            if (output == 0) {
                try {
                    Method getOutputTokens = usage.getClass().getMethod("getOutputTokens");
                    Object result = getOutputTokens.invoke(usage);
                    if (result instanceof Number) {
                        output = ((Number) result).intValue();
                    }
                } catch (Exception ignored) {}
            }
            
        } catch (Exception e) {
            // Ignore reflection errors
        }
        
        return new int[]{input, output};
    }
    
    private static int[] extractFromMap(Map<?, ?> map) {
        int input = 0;
        int output = 0;
        
        Object usage = map.get("usage");
        if (usage instanceof Map) {
            Map<?, ?> usageMap = (Map<?, ?>) usage;
            
            // OpenAI format
            Object promptTokens = usageMap.get("prompt_tokens");
            if (promptTokens instanceof Number) {
                input = ((Number) promptTokens).intValue();
            }
            
            Object completionTokens = usageMap.get("completion_tokens");
            if (completionTokens instanceof Number) {
                output = ((Number) completionTokens).intValue();
            }
            
            // Anthropic format
            if (input == 0) {
                Object inputTokens = usageMap.get("input_tokens");
                if (inputTokens instanceof Number) {
                    input = ((Number) inputTokens).intValue();
                }
            }
            
            if (output == 0) {
                Object outputTokens = usageMap.get("output_tokens");
                if (outputTokens instanceof Number) {
                    output = ((Number) outputTokens).intValue();
                }
            }
        }
        
        return new int[]{input, output};
    }
    
    private static int[] extractFromJsonNode(JsonNode node) {
        int input = 0;
        int output = 0;
        
        JsonNode usage = node.get("usage");
        if (usage != null) {
            // OpenAI format
            JsonNode promptTokens = usage.get("prompt_tokens");
            if (promptTokens != null && promptTokens.isNumber()) {
                input = promptTokens.asInt();
            }
            
            JsonNode completionTokens = usage.get("completion_tokens");
            if (completionTokens != null && completionTokens.isNumber()) {
                output = completionTokens.asInt();
            }
            
            // Anthropic format
            if (input == 0) {
                JsonNode inputTokens = usage.get("input_tokens");
                if (inputTokens != null && inputTokens.isNumber()) {
                    input = inputTokens.asInt();
                }
            }
            
            if (output == 0) {
                JsonNode outputTokens = usage.get("output_tokens");
                if (outputTokens != null && outputTokens.isNumber()) {
                    output = outputTokens.asInt();
                }
            }
        }
        
        return new int[]{input, output};
    }
    
    /**
     * Extract content from an LLM response.
     * 
     * @param response The response object
     * @param provider The provider name (openai, anthropic, etc.)
     * @return The content string
     */
    public static String extractContent(Object response, String provider) {
        if (response == null) {
            return "";
        }
        
        if (response instanceof String) {
            return (String) response;
        }
        
        try {
            JsonNode node;
            if (response instanceof JsonNode) {
                node = (JsonNode) response;
            } else {
                node = objectMapper.valueToTree(response);
            }
            
            // Anthropic format
            if ("anthropic".equalsIgnoreCase(provider) || "claude".equalsIgnoreCase(provider)) {
                JsonNode content = node.get("content");
                if (content != null && content.isArray() && content.size() > 0) {
                    StringBuilder sb = new StringBuilder();
                    for (JsonNode block : content) {
                        if ("text".equals(block.path("type").asText())) {
                            sb.append(block.path("text").asText());
                        }
                    }
                    if (sb.length() > 0) {
                        return sb.toString();
                    }
                }
            }
            
            // OpenAI format
            JsonNode choices = node.get("choices");
            if (choices != null && choices.isArray() && choices.size() > 0) {
                JsonNode firstChoice = choices.get(0);
                JsonNode message = firstChoice.get("message");
                if (message != null) {
                    JsonNode content = message.get("content");
                    if (content != null && content.isTextual()) {
                        return content.asText();
                    }
                }
                JsonNode text = firstChoice.get("text");
                if (text != null && text.isTextual()) {
                    return text.asText();
                }
            }
            
            // Simple content field
            JsonNode content = node.get("content");
            if (content != null && content.isTextual()) {
                return content.asText();
            }
            
        } catch (Exception e) {
            // Ignore
        }
        
        return response.toString();
    }
}
