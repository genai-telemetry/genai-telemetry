"""
Example: RAG Pipeline with GenAI Telemetry
==========================================

This example shows how to instrument a Retrieval-Augmented Generation (RAG)
pipeline with multiple trace decorators.

Prerequisites:
    pip install genai-telemetry openai

Usage:
    export OPENAI_API_KEY="your-api-key"
    python rag_pipeline.py
"""

from typing import List, Dict
from genai_telemetry import (
    setup_telemetry,
    trace_llm,
    trace_embedding,
    trace_retrieval,
    trace_chain,
)

# Initialize telemetry
setup_telemetry(
    workflow_name="rag-pipeline",
    exporter="console"
)

# Simulated document store
DOCUMENTS = [
    {"id": 1, "text": "Paris is the capital of France.", "embedding": [0.1, 0.2, 0.3]},
    {"id": 2, "text": "London is the capital of England.", "embedding": [0.2, 0.3, 0.4]},
    {"id": 3, "text": "Berlin is the capital of Germany.", "embedding": [0.3, 0.4, 0.5]},
    {"id": 4, "text": "Tokyo is the capital of Japan.", "embedding": [0.4, 0.5, 0.6]},
]


@trace_embedding(model="text-embedding-3-small")
def get_query_embedding(query: str) -> List[float]:
    """Generate embedding for the query."""
    # In production, use actual embedding API
    # from openai import OpenAI
    # client = OpenAI()
    # response = client.embeddings.create(
    #     model="text-embedding-3-small",
    #     input=query
    # )
    # return response.data[0].embedding
    
    # Simulated embedding
    return [0.15, 0.25, 0.35]


@trace_retrieval(vector_store="in-memory", embedding_model="text-embedding-3-small")
def retrieve_documents(query_embedding: List[float], top_k: int = 2) -> List[Dict]:
    """Retrieve relevant documents based on embedding similarity."""
    # In production, use actual vector store
    # Simulated retrieval - just return first top_k documents
    return DOCUMENTS[:top_k]


@trace_llm(model_name="gpt-4o-mini", model_provider="openai", extract_content=True)
def generate_answer(query: str, context: str) -> str:
    """Generate answer using LLM with retrieved context."""
    # In production, use actual LLM API
    # from openai import OpenAI
    # client = OpenAI()
    # response = client.chat.completions.create(
    #     model="gpt-4o-mini",
    #     messages=[
    #         {"role": "system", "content": f"Answer based on this context: {context}"},
    #         {"role": "user", "content": query}
    #     ]
    # )
    # return response
    
    # Simulated response
    class MockResponse:
        class Choices:
            class Message:
                content = f"Based on the context, the answer to '{query}' is found in the documents."
            message = Message()
        choices = [Choices()]
        class Usage:
            prompt_tokens = 50
            completion_tokens = 25
        usage = Usage()
    
    return MockResponse()


@trace_chain(name="rag-pipeline")
def rag_query(question: str) -> str:
    """
    Full RAG pipeline:
    1. Generate query embedding
    2. Retrieve relevant documents
    3. Generate answer using LLM
    """
    # Step 1: Generate embedding
    query_embedding = get_query_embedding(question)
    
    # Step 2: Retrieve documents
    relevant_docs = retrieve_documents(query_embedding, top_k=2)
    
    # Step 3: Build context
    context = "\n".join([doc["text"] for doc in relevant_docs])
    
    # Step 4: Generate answer
    answer = generate_answer(question, context)
    
    return answer


if __name__ == "__main__":
    print("=" * 60)
    print("RAG Pipeline Example")
    print("=" * 60)
    
    question = "What is the capital of France?"
    print(f"\nQuestion: {question}")
    
    answer = rag_query(question)
    print(f"\nAnswer: {answer}")
    
    print("\n" + "=" * 60)
    print("Check the console output above for the full trace!")
    print("=" * 60)
