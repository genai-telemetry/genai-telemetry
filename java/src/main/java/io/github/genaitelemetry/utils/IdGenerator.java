package io.github.genaitelemetry.utils;

import java.util.Random;
import java.util.concurrent.ThreadLocalRandom;

/**
 * Utility class for generating trace and span IDs.
 */
public final class IdGenerator {
    
    private static final char[] HEX_CHARS = "0123456789abcdef".toCharArray();
    
    private IdGenerator() {
        // Utility class
    }
    
    /**
     * Generate a random hex string of the specified length.
     */
    public static String randomHex(int length) {
        Random random = ThreadLocalRandom.current();
        char[] result = new char[length];
        for (int i = 0; i < length; i++) {
            result[i] = HEX_CHARS[random.nextInt(16)];
        }
        return new String(result);
    }
    
    /**
     * Generate a new trace ID (32 hex characters).
     */
    public static String generateTraceId() {
        return randomHex(32);
    }
    
    /**
     * Generate a new span ID (16 hex characters).
     */
    public static String generateSpanId() {
        return randomHex(16);
    }
}
