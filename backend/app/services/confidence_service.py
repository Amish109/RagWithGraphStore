"""Confidence scoring service for LLM responses.

This module provides confidence calculation for query responses.
When the provider supports logprobs (OpenAI), uses token-level probability data.
When logprobs are unavailable (Ollama), falls back to self-assessment prompting.

Phase 5 - Success Criteria #6: System provides confidence scores on responses
so users know when to verify answers.
"""

from typing import Dict, List, Optional

import numpy as np
from langchain_core.prompts import ChatPromptTemplate

from app.services.llm_provider import get_llm, supports_logprobs


def calculate_confidence_from_logprobs(logprobs: List[Dict]) -> dict:
    """Calculate confidence score from OpenAI logprobs.

    Uses multiple methods to assess confidence:
    1. Average token probability
    2. Joint probability (product of all token probs)
    3. Geometric mean (most stable for sequences)
    4. Perplexity (lower = more confident)

    Args:
        logprobs: List of logprob dictionaries with 'logprob' key.

    Returns:
        Dict with:
        - score: Confidence score (0.0 to 1.0)
        - level: "high", "medium", "low", or "unknown"
        - interpretation: Human-readable explanation
        - metrics: Detailed calculation metrics
    """
    # Handle empty/null logprobs gracefully
    if not logprobs:
        return {
            "score": 0.5,
            "level": "unknown",
            "interpretation": "No logprob data available",
            "metrics": {
                "average_probability": None,
                "geometric_mean": None,
                "perplexity": None,
                "tokens_analyzed": 0,
            },
        }

    # Extract log probabilities, filtering out None values
    log_probs = [
        lp.get("logprob") for lp in logprobs if lp.get("logprob") is not None
    ]

    if not log_probs:
        return {
            "score": 0.5,
            "level": "unknown",
            "interpretation": "No logprob data available",
            "metrics": {
                "average_probability": None,
                "geometric_mean": None,
                "perplexity": None,
                "tokens_analyzed": 0,
            },
        }

    # Convert to numpy array for efficient calculation
    log_probs_array = np.array(log_probs)

    # Convert log probabilities to linear probabilities
    probabilities = np.exp(log_probs_array)

    # Method 1: Average probability
    avg_prob = float(np.mean(probabilities))

    # Method 2: Geometric mean (most stable for sequence comparison)
    # This is equivalent to exp(mean(log_probs))
    geometric_mean = float(np.exp(np.mean(log_probs_array)))

    # Method 3: Perplexity (lower = more confident)
    # Perplexity = exp(-mean(log_probs))
    perplexity = float(np.exp(-np.mean(log_probs_array)))

    # Final confidence score using geometric mean (0-1 range)
    # Clamp to [0, 1] to handle edge cases
    confidence_score = min(max(geometric_mean, 0.0), 1.0)

    # Determine confidence level and interpretation
    if confidence_score >= 0.85:
        level = "high"
        interpretation = "The model is highly confident in this response."
    elif confidence_score >= 0.60:
        level = "medium"
        interpretation = (
            "The model is moderately confident. Consider verifying key claims."
        )
    else:
        level = "low"
        interpretation = (
            "The model has low confidence. Please verify this response "
            "with authoritative sources."
        )

    return {
        "score": round(confidence_score, 3),
        "level": level,
        "interpretation": interpretation,
        "metrics": {
            "average_probability": round(avg_prob, 3),
            "geometric_mean": round(geometric_mean, 3),
            "perplexity": round(perplexity, 2),
            "tokens_analyzed": len(log_probs),
        },
    }


async def generate_answer_with_confidence(
    query: str, context: List[Dict]
) -> dict:
    """Generate answer using LLM with confidence scoring.

    When the provider supports logprobs (OpenAI), uses token-level probability data.
    When logprobs are unavailable (Ollama), falls back to LLM self-assessment.

    Args:
        query: User's question.
        context: List of context chunks with 'text' and optional 'filename' keys.

    Returns:
        Dict with:
        - answer: Generated answer string
        - confidence: Confidence score dict from calculate_confidence_from_logprobs
    """
    # Assemble context from chunks (same pattern as generation_service.py)
    context_text = "\n\n".join(
        [
            f"[Document: {chunk.get('filename', 'Unknown')}]\n{chunk['text']}"
            for chunk in context
        ]
    )

    use_logprobs = supports_logprobs()

    # Create LLM (with logprobs if supported)
    llm = get_llm(temperature=0, logprobs=use_logprobs)

    # Same prompt template as generation_service.py for consistency
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """You are a helpful document Q&A assistant. Answer questions ONLY based on the provided context.

CRITICAL INSTRUCTIONS:
- If the context does not contain information to answer the question, respond EXACTLY with: "I don't know. I couldn't find information about this in the provided documents."
- Do not use any knowledge outside the provided context
- Cite the document name when referencing information
- Be concise and direct""",
            ),
            (
                "user",
                """Context:
{context}

Question: {query}

Answer:""",
            ),
        ]
    )

    # Generate response
    messages = prompt.format_messages(context=context_text, query=query)
    response = await llm.ainvoke(messages)

    if use_logprobs:
        # Extract logprobs from response metadata (OpenAI)
        logprobs_data = []
        if hasattr(response, "response_metadata") and response.response_metadata:
            logprobs_content = response.response_metadata.get("logprobs", {})
            if logprobs_content:
                content_logprobs = logprobs_content.get("content", [])
                logprobs_data = [
                    {"token": item.get("token"), "logprob": item.get("logprob")}
                    for item in content_logprobs
                    if item.get("logprob") is not None
                ]

        confidence = calculate_confidence_from_logprobs(logprobs_data)
    else:
        # Fallback: LLM self-assessment for providers without logprobs
        confidence = await _estimate_confidence_via_self_assessment(
            llm, response.content, context_text, query
        )

    return {
        "answer": response.content,
        "confidence": confidence,
    }


async def _estimate_confidence_via_self_assessment(
    llm, answer: str, context: str, query: str
) -> dict:
    """Estimate confidence via LLM self-assessment when logprobs are unavailable.

    Asks the LLM to rate its own confidence based on how well the context
    supports its answer. This is a heuristic fallback, not as precise as logprobs.

    Args:
        llm: The LLM instance to use.
        answer: The generated answer to assess.
        context: The context used to generate the answer.
        query: The original user query.

    Returns:
        Confidence dict matching the logprobs format.
    """
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """You are a confidence assessment expert. Rate how well the given answer is supported by the provided context.
Respond with ONLY a single number between 0 and 100 representing your confidence percentage. No other text.""",
            ),
            (
                "user",
                """Context:
{context}

Question: {query}

Answer given: {answer}

Confidence (0-100):""",
            ),
        ]
    )

    try:
        messages = prompt.format_messages(context=context[:2000], query=query, answer=answer)
        response = await llm.ainvoke(messages)
        score = float(response.content.strip().rstrip("%")) / 100.0
        score = min(max(score, 0.0), 1.0)
    except (ValueError, TypeError):
        score = 0.5

    if score >= 0.85:
        level = "high"
        interpretation = "The model is highly confident in this response."
    elif score >= 0.60:
        level = "medium"
        interpretation = "The model is moderately confident. Consider verifying key claims."
    else:
        level = "low"
        interpretation = "The model has low confidence. Please verify this response with authoritative sources."

    return {
        "score": round(score, 3),
        "level": level,
        "interpretation": interpretation,
        "metrics": {
            "method": "self_assessment",
            "average_probability": None,
            "geometric_mean": None,
            "perplexity": None,
            "tokens_analyzed": 0,
        },
    }
