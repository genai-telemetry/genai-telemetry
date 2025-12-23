"""
Example: Basic OpenAI integration with GenAI Telemetry
=====================================================

This example shows how to instrument a simple OpenAI chat application
with genai-telemetry for observability.

Prerequisites:
    pip install genai-telemetry openai

Usage:
    export OPENAI_API_KEY="your-api-key"
    python basic_openai.py
"""

from genai_telemetry import setup_telemetry, trace_llm

# Initialize telemetry with console output for development
setup_telemetry(
    workflow_name="openai-chatbot",
    exporter="console"  # Use "splunk", "elasticsearch", etc. in production
)


@trace_llm(model_name="gpt-4o-mini", model_provider="openai")
def chat(message: str) -> str:
    """
    Send a message to OpenAI and get a response.
    
    NOTE: We return the FULL response object to capture token counts,
    then extract the content for our return value.
    """
    from openai import OpenAI
    
    client = OpenAI()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": message}]
    )
    
    # Return full response - telemetry captures tokens
    return response


@trace_llm(model_name="gpt-4o-mini", model_provider="openai", extract_content=True)
def chat_simple(message: str) -> str:
    """
    Alternative: Use extract_content=True to automatically get just the text.
    """
    from openai import OpenAI
    
    client = OpenAI()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": message}]
    )
    
    return response  # Returns full response, but decorator extracts content


if __name__ == "__main__":
    print("=" * 60)
    print("Example 1: Full response (extract content manually)")
    print("=" * 60)
    
    response = chat("What is the capital of France?")
    print(f"\nResponse: {response.choices[0].message.content}")
    
    print("\n" + "=" * 60)
    print("Example 2: Auto-extracted content")
    print("=" * 60)
    
    content = chat_simple("What is 2 + 2?")
    print(f"\nResponse: {content}")
    
    print("\n" + "=" * 60)
    print("Check the console output above for telemetry data!")
    print("=" * 60)
