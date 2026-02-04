"""LLM generation service for document Q&A with strict context constraints.

This module provides answer generation using OpenAI models via LangChain.
Implements strict "I don't know" fallback to prevent hallucination.
"""

from typing import Dict, List

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.config import settings


# Initialize LLM with deterministic settings
llm = ChatOpenAI(
    model=settings.OPENAI_MODEL,
    temperature=0,  # Deterministic for consistency
    openai_api_key=settings.OPENAI_API_KEY,
)


async def generate_answer(query: str, context: List[Dict]) -> str:
    """Generate answer using LLM with strict context-only constraint.

    CRITICAL: Prevents hallucination by enforcing "I don't know" fallback.
    Addresses QRY-04 requirement.

    Args:
        query: User's question.
        context: List of context chunks with 'text' and optional 'filename' keys.

    Returns:
        Generated answer string.
    """
    # Assemble context from chunks
    context_text = "\n\n".join([
        f"[Document: {chunk.get('filename', 'Unknown')}]\n{chunk['text']}"
        for chunk in context
    ])

    # Prompt template with strict constraints
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a helpful document Q&A assistant. Answer questions ONLY based on the provided context.

CRITICAL INSTRUCTIONS:
- If the context does not contain information to answer the question, respond EXACTLY with: "I don't know. I couldn't find information about this in the provided documents."
- Do not use any knowledge outside the provided context
- Cite the document name when referencing information
- Be concise and direct"""),
        ("user", """Context:
{context}

Question: {query}

Answer:""")
    ])

    # Generate response
    messages = prompt.format_messages(context=context_text, query=query)
    response = await llm.ainvoke(messages)

    return response.content


async def generate_answer_no_context() -> str:
    """Return standard "I don't know" response when no context available.

    Returns:
        Standard fallback message.
    """
    return "I don't know. I couldn't find any relevant information in your documents."
