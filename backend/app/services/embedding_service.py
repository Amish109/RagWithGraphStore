"""OpenAI embedding service with dimension validation.

This module provides async embedding generation for document indexing
and query embedding. Includes startup validation to prevent dimension mismatch.
"""

import asyncio
from typing import List

from openai import AsyncOpenAI

from app.config import settings


# Initialize async OpenAI client
openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


async def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """Generate embeddings for a list of texts.

    Args:
        texts: List of text strings to embed.

    Returns:
        List of embedding vectors (each vector is a list of floats).
    """
    response = await openai_client.embeddings.create(
        input=texts,
        model=settings.OPENAI_EMBEDDING_MODEL,
        encoding_format="float",
    )

    # Extract embeddings in order (response.data is sorted by index)
    return [item.embedding for item in response.data]


async def generate_query_embedding(query: str) -> List[float]:
    """Generate embedding for a single query string.

    Convenience wrapper around generate_embeddings for single queries.

    Args:
        query: The query text to embed.

    Returns:
        Embedding vector as list of floats.
    """
    embeddings = await generate_embeddings([query])
    return embeddings[0]


def validate_embedding_dimensions() -> None:
    """Validate embedding dimensions match configuration at startup.

    CRITICAL: Prevents Pitfall #3 - Dimension mismatch causes cryptic errors.
    Call this during FastAPI lifespan startup.

    Raises:
        ValueError: If actual embedding dimensions don't match configured dimensions.
    """
    # Run async embedding generation in sync context
    embeddings = asyncio.run(generate_embeddings(["test"]))
    actual_dim = len(embeddings[0])
    expected_dim = settings.OPENAI_EMBEDDING_DIMENSIONS

    if actual_dim != expected_dim:
        raise ValueError(
            f"Embedding dimension mismatch! Expected {expected_dim}, got {actual_dim}. "
            f"Check OPENAI_EMBEDDING_MODEL and OPENAI_EMBEDDING_DIMENSIONS config."
        )
