"""
Example: Auto-Instrumentation with genai-telemetry
==================================================

This example demonstrates how to use auto-instrumentation to trace
all your LLM calls with ZERO code changes to your existing code.

Before auto-instrumentation, you had to add decorators to every function:

    @trace_llm(model_name="gpt-4o", model_provider="openai")
    def chat(message):
        return client.chat.completions.create(...)

With auto-instrumentation, you just call auto_instrument() once and 
ALL LLM calls are automatically traced!
"""

from genai_telemetry import setup_telemetry, auto_instrument

# ============================================================================
# STEP 1: Setup telemetry (choose your backend)
# ============================================================================

# Option A: Send to Splunk
setup_telemetry(
    workflow_name="my-chatbot",
    exporter="splunk",
    splunk_url="https://your-splunk:8088",
    splunk_token="your-hec-token",
    splunk_index="genai_traces",
)

# Option B: Send to Console (for testing)
# setup_telemetry(
#     workflow_name="my-chatbot",
#     exporter="console",
# )

# Option C: Send to multiple backends
# setup_telemetry(
#     workflow_name="my-chatbot",
#     exporter=[
#         {"type": "splunk", "url": "...", "token": "..."},
#         {"type": "console"},
#         {"type": "file", "path": "traces.jsonl"},
#     ]
# )


# ============================================================================
# STEP 2: Enable auto-instrumentation
# ============================================================================

# Instrument ALL available frameworks (OpenAI, Anthropic, LangChain, etc.)
results = auto_instrument()
print(f"Instrumented frameworks: {results}")

# Or instrument specific frameworks only:
# auto_instrument(frameworks=["openai", "langchain"])

# Or exclude specific frameworks:
# auto_instrument(exclude=["anthropic"])


# ============================================================================
# STEP 3: Use your LLM libraries normally - they're now traced!
# ============================================================================

# Example with OpenAI
from openai import OpenAI

client = OpenAI()

# This call is AUTOMATICALLY traced and sent to Splunk!
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "What is Splunk?"}]
)
print(response.choices[0].message.content)


# Example with Anthropic
# from anthropic import Anthropic
# client = Anthropic()
# response = client.messages.create(
#     model="claude-3-sonnet-20240229",
#     messages=[{"role": "user", "content": "What is observability?"}]
# )
# print(response.content[0].text)  # Also automatically traced!


# Example with LangChain
# from langchain_openai import ChatOpenAI
# llm = ChatOpenAI(model="gpt-4o")
# response = llm.invoke("Explain GenAI observability")
# print(response.content)  # Also automatically traced!


# ============================================================================
# STEP 4: Check what's instrumented (optional)
# ============================================================================

from genai_telemetry import get_instrumented_frameworks, is_instrumented

print(f"\nCurrently instrumented: {get_instrumented_frameworks()}")
print(f"Is OpenAI instrumented? {is_instrumented('openai')}")
print(f"Is LangChain instrumented? {is_instrumented('langchain')}")


# ============================================================================
# STEP 5: Disable instrumentation when done (optional)
# ============================================================================

# from genai_telemetry import uninstrument
# uninstrument()  # Remove all instrumentation
# uninstrument(frameworks=["openai"])  # Remove specific frameworks only
