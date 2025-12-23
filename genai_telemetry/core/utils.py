"""
Utility functions for token and content extraction from LLM responses.
"""

from typing import Any, Tuple


def extract_tokens_from_response(response: Any) -> Tuple[int, int]:
    """
    Extract input/output tokens from various LLM response formats.
    
    Supports:
    - OpenAI ChatCompletion responses
    - OpenAI Completion responses
    - Anthropic Message responses
    - Dict responses
    
    Args:
        response: The LLM response object
    
    Returns:
        tuple: (input_tokens, output_tokens)
    """
    input_tokens = 0
    output_tokens = 0
    
    # Check if response has usage attribute
    if hasattr(response, "usage") and response.usage is not None:
        usage = response.usage
        
        # OpenAI ChatCompletion / Completion response object
        # Check for prompt_tokens (OpenAI-specific)
        if hasattr(usage, "prompt_tokens"):
            prompt_val = getattr(usage, "prompt_tokens", None)
            if prompt_val is not None:
                input_tokens = prompt_val or 0
                output_tokens = getattr(usage, "completion_tokens", 0) or 0
                return (input_tokens, output_tokens)
        
        # Anthropic Message response
        # Check for input_tokens (Anthropic-specific)
        if hasattr(usage, "input_tokens"):
            input_val = getattr(usage, "input_tokens", None)
            if input_val is not None:
                input_tokens = input_val or 0
                output_tokens = getattr(usage, "output_tokens", 0) or 0
                return (input_tokens, output_tokens)
    
    # Dict response (some libraries return this)
    if isinstance(response, dict):
        usage = response.get("usage", {})
        if usage:
            # OpenAI style
            if "prompt_tokens" in usage:
                input_tokens = usage.get("prompt_tokens", 0) or 0
                output_tokens = usage.get("completion_tokens", 0) or 0
            # Anthropic style
            elif "input_tokens" in usage:
                input_tokens = usage.get("input_tokens", 0) or 0
                output_tokens = usage.get("output_tokens", 0) or 0
            return (input_tokens, output_tokens)
    
    return (input_tokens, output_tokens)


def extract_content_from_response(response: Any, model_provider: str = "openai") -> str:
    """
    Extract text content from various LLM response formats.
    
    Args:
        response: The LLM response object
        model_provider: The provider name (openai, anthropic, etc.)
    
    Returns:
        str: The extracted text content
    """
    # Already a string
    if isinstance(response, str):
        return response
    
    # OpenAI ChatCompletion
    if hasattr(response, "choices") and response.choices:
        choice = response.choices[0]
        if hasattr(choice, "message") and hasattr(choice.message, "content"):
            return choice.message.content or ""
        # Legacy completion format
        if hasattr(choice, "text"):
            return choice.text or ""
    
    # Anthropic Message
    if hasattr(response, "content") and isinstance(response.content, list):
        texts = []
        for block in response.content:
            if hasattr(block, "text"):
                texts.append(block.text)
        return "".join(texts)
    
    # Dict response
    if isinstance(response, dict):
        # OpenAI style
        if "choices" in response and response["choices"]:
            choice = response["choices"][0]
            if "message" in choice:
                return choice["message"].get("content", "")
            if "text" in choice:
                return choice.get("text", "")
        # Anthropic style
        if "content" in response and isinstance(response["content"], list):
            texts = []
            for block in response["content"]:
                if isinstance(block, dict) and "text" in block:
                    texts.append(block["text"])
            return "".join(texts)
    
    return str(response)


# Aliases for backwards compatibility
_extract_tokens_from_response = extract_tokens_from_response
_extract_content_from_response = extract_content_from_response
