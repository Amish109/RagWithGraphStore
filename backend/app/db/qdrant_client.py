"""Qdrant vector database client and collection initialization.

Provides:
- qdrant_client: Singleton client instance for Qdrant connections
- close_qdrant(): Close the client connection
- init_qdrant_collection(): Initialize collection with proper configuration
"""

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, OptimizersConfigDiff

from app.config import settings

# Initialize Qdrant client (singleton)
# Conditional init: use API key for cloud, host/port for local
if settings.QDRANT_API_KEY:
    # Qdrant Cloud
    qdrant_client = QdrantClient(
        url=f"https://{settings.QDRANT_HOST}",
        api_key=settings.QDRANT_API_KEY,
        timeout=60,
    )
else:
    # Local Qdrant
    qdrant_client = QdrantClient(
        host=settings.QDRANT_HOST,
        port=settings.QDRANT_PORT,
        timeout=60,
    )


def close_qdrant() -> None:
    """Close Qdrant client connection."""
    qdrant_client.close()


def init_qdrant_collection() -> None:
    """Initialize Qdrant collection with proper configuration.

    CRITICAL: Vector dimension MUST match embedding model.
    Once created, dimension cannot be changed - requires recreation.

    Collection configuration:
    - size: OPENAI_EMBEDDING_DIMENSIONS (1536 for text-embedding-3-small)
    - distance: COSINE (standard for OpenAI embeddings)
    - Payload indexes on user_id and document_id for multi-tenant filtering
    """
    collection_name = settings.QDRANT_COLLECTION

    # Check if collection exists
    collections = qdrant_client.get_collections().collections
    if any(c.name == collection_name for c in collections):
        print(f"Qdrant collection '{collection_name}' already exists")
        return

    # Create collection
    qdrant_client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(
            size=settings.OPENAI_EMBEDDING_DIMENSIONS,  # MUST match embedding model
            distance=Distance.COSINE,  # Cosine similarity for OpenAI embeddings
        ),
        optimizers_config=OptimizersConfigDiff(
            indexing_threshold=10000,  # Start indexing after 10k vectors
        ),
    )

    # Create payload indexes for filtering (multi-tenancy)
    qdrant_client.create_payload_index(
        collection_name=collection_name,
        field_name="user_id",
        field_schema="keyword",  # Exact match filtering
    )

    qdrant_client.create_payload_index(
        collection_name=collection_name,
        field_name="document_id",
        field_schema="keyword",
    )

    print(f"Qdrant collection '{collection_name}' created with dimension {settings.OPENAI_EMBEDDING_DIMENSIONS}")
