"""Qdrant vector database client and collection initialization.

Provides:
- qdrant_client: Singleton client instance for Qdrant connections
- close_qdrant(): Close the client connection
- init_qdrant_collection(): Initialize collection with proper configuration
- upsert_chunks(): Insert or update document chunks with embeddings
"""

from typing import Dict, List

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchAny,
    MatchValue,
    PointStruct,
    VectorParams,
    OptimizersConfigDiff,
)

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
    - size: EMBEDDING_DIMENSIONS (varies by provider and model)
    - distance: COSINE (standard for semantic similarity)
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
            size=settings.EMBEDDING_DIMENSIONS,  # MUST match embedding model
            distance=Distance.COSINE,  # Cosine similarity for embeddings
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

    print(f"Qdrant collection '{collection_name}' created with dimension {settings.EMBEDDING_DIMENSIONS}")


def upsert_chunks(chunks: List[Dict]) -> None:
    """Insert or update document chunks with embeddings in Qdrant.

    Args:
        chunks: List of chunk dictionaries with keys:
            - id: UUID string for the chunk
            - vector: Embedding vector (list of floats)
            - text: Chunk text content
            - document_id: UUID of parent document
            - user_id: ID of owning user
            - position: Position index in document

    CRITICAL: Always includes user_id in payload for multi-tenant filtering.
    Prevents Pitfall #6 (no multi-tenant filtering).
    """
    points = [
        PointStruct(
            id=chunk["id"],
            vector=chunk["vector"],
            payload={
                "text": chunk["text"],
                "document_id": chunk["document_id"],
                "user_id": chunk["user_id"],  # CRITICAL: Required for multi-tenant isolation
                "position": chunk["position"],
            },
        )
        for chunk in chunks
    ]

    qdrant_client.upsert(
        collection_name=settings.QDRANT_COLLECTION,
        points=points,
    )


def delete_by_document_id(document_id: str) -> None:
    """Delete all vectors associated with a document.

    CRITICAL: Called BEFORE Neo4j deletion for consistency.
    Qdrant deletion by filter is atomic for matching points.

    Args:
        document_id: UUID of the document to delete vectors for.
    """
    from qdrant_client.models import FilterSelector

    qdrant_client.delete(
        collection_name=settings.QDRANT_COLLECTION,
        points_selector=FilterSelector(
            filter=Filter(
                must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]
            )
        ),
        wait=True,  # Wait for deletion to complete
    )


def search_similar_chunks(
    query_vector: List[float],
    user_id: str,
    limit: int = 10,
    include_shared: bool = True,
) -> List[Dict]:
    """Search for similar chunks filtered by user_id, optionally including shared docs.

    CRITICAL: Always filter by user_id for multi-tenant isolation.
    Shared documents (uploaded by admin with __shared__ user_id) are included
    for authenticated users so company knowledge is searchable by everyone.

    Args:
        query_vector: Embedding vector for the query.
        user_id: ID of the user to filter results for.
        limit: Maximum number of results to return.
        include_shared: If True, also include shared knowledge documents.

    Returns:
        List of chunk dictionaries with id, score, text, document_id, position.
    """
    # Include both user's own docs and shared docs
    if include_shared and user_id != settings.SHARED_MEMORY_USER_ID:
        user_filter = Filter(
            must=[
                FieldCondition(
                    key="user_id",
                    match=MatchAny(any=[user_id, settings.SHARED_MEMORY_USER_ID]),
                )
            ]
        )
    else:
        user_filter = Filter(
            must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))]
        )

    response = qdrant_client.query_points(
        collection_name=settings.QDRANT_COLLECTION,
        query=query_vector,
        query_filter=user_filter,
        limit=limit,
        with_payload=True,
        with_vectors=False,
    )

    return [
        {
            "id": str(result.id),
            "score": result.score,
            "text": result.payload.get("text", ""),
            "document_id": result.payload.get("document_id", ""),
            "position": result.payload.get("position", 0),
        }
        for result in response.points
    ]
