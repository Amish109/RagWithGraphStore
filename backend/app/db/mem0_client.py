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
    # Build LLM config based on provider
    llm_provider = settings.LLM_PROVIDER.lower()
    if llm_provider == "ollama":
        llm_config = {
            "provider": "ollama",
            "config": {
                "model": settings.OLLAMA_MODEL,
                "temperature": 0.1,
                "ollama_base_url": settings.OLLAMA_BASE_URL,
            },
        }
    elif llm_provider == "anthropic":
        llm_config = {
            "provider": "anthropic",
            "config": {
                "model": settings.ANTHROPIC_MODEL,
                "temperature": 0.1,
            },
        }
    elif llm_provider == "openrouter":
        openrouter_llm_config = {
            "model": settings.OPENROUTER_MODEL,
            "temperature": 0.1,
            "api_key": settings.OPENROUTER_API_KEY,
            "openrouter_base_url": settings.OPENROUTER_BASE_URL,
        }
        if settings.OPENROUTER_MAX_TOKENS:
            openrouter_llm_config["max_tokens"] = settings.OPENROUTER_MAX_TOKENS
        llm_config = {
            "provider": "openai",
            "config": openrouter_llm_config,
        }
        # Mem0 also checks os.environ for OPENROUTER_API_KEY
        import os
        os.environ.setdefault("OPENROUTER_API_KEY", settings.OPENROUTER_API_KEY or "")
    else:
        llm_config = {
            "provider": "openai",
            "config": {
                "model": settings.OPENAI_MODEL,
                "temperature": 0.1,
            },
        }

    # Build embedder config based on provider
    embedding_provider = settings.EMBEDDING_PROVIDER.lower()
    if embedding_provider == "ollama":
        embedder_config = {
            "provider": "ollama",
            "config": {
                "model": settings.OLLAMA_EMBEDDING_MODEL,
                "ollama_base_url": settings.OLLAMA_BASE_URL,
                "embedding_dims": settings.OLLAMA_EMBEDDING_DIMENSIONS,
            },
        }
    else:
        embedder_config = {
            "provider": "openai",
            "config": {
                "model": settings.OPENAI_EMBEDDING_MODEL,
                "embedding_dims": settings.OPENAI_EMBEDDING_DIMENSIONS,
            },
        }

    config = {
        "version": "v1.1",
        "llm": llm_config,
        "embedder": embedder_config,
        "vector_store": {
            "provider": "qdrant",
            "config": {
                "collection_name": "memory",  # SEPARATE from documents collection
                "host": settings.QDRANT_HOST,
                "port": settings.QDRANT_PORT,
                "embedding_model_dims": settings.EMBEDDING_DIMENSIONS,
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
