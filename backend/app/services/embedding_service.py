"""Embedding service with dimension validation and multi-provider support.

This module provides async embedding generation for document indexing
and query embedding. Supports OpenAI and Ollama providers.
Includes startup validation to prevent dimension mismatch.
"""

from typing import List

from app.config import settings
from app.services.llm_provider import get_embedding_model


def _get_model():
    """Get a fresh embedding model instance (avoids stale event loop references)."""
    return get_embedding_model()


async def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """Generate embeddings for a list of texts.

    Args:
        texts: List of text strings to embed.

    Returns:
        List of embedding vectors (each vector is a list of floats).
    """
    return await _get_model().aembed_documents(texts)


async def generate_query_embedding(query: str) -> List[float]:
    """Generate embedding for a single query string.

    Convenience wrapper around the embedding model for single queries.

    Args:
        query: The query text to embed.

    Returns:
        Embedding vector as list of floats.
    """
    return await _get_model().aembed_query(query)


async def validate_embedding_dimensions() -> None:
    """Validate embedding dimensions match configuration at startup.

    CRITICAL: Prevents Pitfall #3 - Dimension mismatch causes cryptic errors.
    Call this during FastAPI lifespan startup.

    Raises:
        ValueError: If actual embedding dimensions don't match configured dimensions.
    """
    embeddings = await generate_embeddings(["test"])
    actual_dim = len(embeddings[0])
    expected_dim = settings.EMBEDDING_DIMENSIONS

    if actual_dim != expected_dim:
        raise ValueError(
            f"Embedding dimension mismatch! Expected {expected_dim}, got {actual_dim}. "
            f"Check your embedding model and dimensions config for provider '{settings.EMBEDDING_PROVIDER}'."
        )
