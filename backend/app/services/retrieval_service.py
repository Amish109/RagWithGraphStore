"""Retrieval service for document context retrieval using vector search.

Phase 1: Vector-only retrieval from Qdrant with Neo4j metadata enrichment.
Phase 2+: Add graph-based retrieval for relationship-aware context.
"""

from typing import Dict, List

from app.config import settings
from app.db.neo4j_client import neo4j_driver
from app.db.qdrant_client import search_similar_chunks
from app.services.embedding_service import generate_query_embedding


async def retrieve_relevant_context(
    query: str, user_id: str, max_results: int = 3
) -> Dict:
    """Retrieve relevant context using vector search.

    Phase 1: Vector-only retrieval from Qdrant.
    Phase 2+: Add graph enrichment with Neo4j relationships.

    CRITICAL: Always filter by user_id for multi-tenant isolation.

    Args:
        query: User's question or search query.
        user_id: ID of the user (for multi-tenant filtering).
        max_results: Maximum number of context chunks to return.

    Returns:
        Dict with 'chunks' key containing list of enriched context chunks.
        Each chunk has: id, score, text, document_id, position, filename.
    """
    # Step 1: Generate query embedding
    query_embedding = await generate_query_embedding(query)

    # Step 2: Vector search in Qdrant (filtered by user_id)
    similar_chunks = search_similar_chunks(
        query_vector=query_embedding,
        user_id=user_id,
        limit=max_results,
    )

    # Step 3: Enrich with document metadata from Neo4j
    enriched_chunks = []
    with neo4j_driver.session(database=settings.NEO4J_DATABASE) as session:
        for chunk in similar_chunks:
            result = session.run(
                """
                MATCH (c:Chunk {id: $chunk_id})<-[:CONTAINS]-(d:Document)
                RETURN d.filename AS filename, d.id AS document_id
                """,
                chunk_id=chunk["id"],
            )

            record = result.single()
            if record:
                enriched_chunks.append(
                    {
                        **chunk,
                        "filename": record["filename"],
                        "document_id": record["document_id"],
                    }
                )
            else:
                # Fallback: include chunk even without Neo4j metadata
                enriched_chunks.append(
                    {
                        **chunk,
                        "filename": "Unknown",
                    }
                )

    return {"chunks": enriched_chunks}
