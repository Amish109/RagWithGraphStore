"""Mem0 memory client configuration for Phase 2 integration.

Phase 1: Basic configuration only. Full integration in Phase 2.
NOTE: Uses separate "memory" collection from "documents" to prevent
confusion between RAG documents and user memory (Pitfall #1).
"""

from typing import Optional

from mem0 import Memory

from app.config import settings


def init_mem0() -> Memory:
    """Initialize Mem0 with dual stores (Neo4j + Qdrant).

    Phase 1: Basic configuration only. Full integration in Phase 2.
    NOTE: Uses separate "memory" collection from documents to prevent
    confusion between RAG documents and user memory (Pitfall #1).

    Returns:
        Configured Mem0 Memory instance.
    """
    config = {
        "version": "v1.1",
        "llm": {
            "provider": "openai",
            "config": {
                "model": settings.OPENAI_MODEL,
                "temperature": 0.1,
            },
        },
        "embedder": {
            "provider": "openai",
            "config": {
                "model": settings.OPENAI_EMBEDDING_MODEL,
            },
        },
        "vector_store": {
            "provider": "qdrant",
            "config": {
                "collection_name": "memory",  # SEPARATE from documents collection
                "host": settings.QDRANT_HOST,
                "port": settings.QDRANT_PORT,
            },
        },
        "graph_store": {
            "provider": "neo4j",
            "config": {
                "url": settings.NEO4J_URI,
                "username": settings.NEO4J_USERNAME,
                "password": settings.NEO4J_PASSWORD,
            },
        },
    }

    # Add API key for Qdrant Cloud if configured
    if settings.QDRANT_API_KEY:
        config["vector_store"]["config"]["api_key"] = settings.QDRANT_API_KEY

    memory = Memory.from_config(config)
    return memory


# Lazy initialization (will be used in Phase 2)
_mem0_memory: Optional[Memory] = None


def get_mem0() -> Memory:
    """Get or initialize Mem0 memory instance.

    Uses lazy initialization pattern to defer connection until first use.

    Returns:
        Mem0 Memory instance.
    """
    global _mem0_memory
    if _mem0_memory is None:
        _mem0_memory = init_mem0()
    return _mem0_memory
