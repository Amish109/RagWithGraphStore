"""Retrieval service for document context retrieval using vector search.

Phase 1: Vector-only retrieval from Qdrant with Neo4j metadata enrichment.
Phase 4+: Add graph-based retrieval for relationship-aware context via GraphRAG.
"""

from typing import Dict, List, Optional

from app.config import settings
from app.db.neo4j_client import neo4j_driver
from app.db.qdrant_client import search_similar_chunks, qdrant_client
from app.services.embedding_service import generate_query_embedding
from qdrant_client.models import Filter, FieldCondition, MatchValue, MatchAny


async def retrieve_relevant_context(
    query: str,
    user_id: str,
    max_results: int = 3,
    include_graph_context: bool = False,
) -> Dict:
    """Retrieve relevant context using vector search.

    Phase 1: Vector-only retrieval from Qdrant.
    Phase 4+: Optional graph enrichment with Neo4j relationships via GraphRAG.

    CRITICAL: Always filter by user_id for multi-tenant isolation.

    Args:
        query: User's question or search query.
        user_id: ID of the user (for multi-tenant filtering).
        max_results: Maximum number of context chunks to return.
        include_graph_context: If True, expand context via entity graph traversal.

    Returns:
        Dict with 'chunks' key containing list of enriched context chunks.
        Each chunk has: id, score, text, document_id, position, filename.
        If include_graph_context=True, also includes entity_relations.
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

    # Step 4: Optionally expand with graph context
    if include_graph_context and enriched_chunks:
        from app.services.graphrag_service import expand_graph_context

        chunk_ids = [c["id"] for c in enriched_chunks]
        graph_context = await expand_graph_context(chunk_ids)

        # Merge graph context into chunks
        for chunk in enriched_chunks:
            ctx = graph_context.get(chunk["id"], {})
            chunk["entity_relations"] = ctx.get("entity_relations", [])
            chunk["related_chunks"] = ctx.get("related_chunks", [])

    return {"chunks": enriched_chunks}


async def retrieve_for_documents(
    query: str,
    user_id: str,
    document_ids: List[str],
    max_results: int = 5,
    include_graph_context: bool = True,
) -> Dict:
    """Retrieve relevant context filtered by specific documents.

    Similar to retrieve_relevant_context but filters by document_ids.
    Designed for document comparison workflows where we need chunks
    from specific documents only.

    Args:
        query: User's question or search query.
        user_id: ID of the user (for multi-tenant filtering).
        document_ids: List of document IDs to filter results to.
        max_results: Maximum number of context chunks to return.
        include_graph_context: If True, expand context via entity graph traversal.

    Returns:
        Dict with 'chunks' key containing list of enriched context chunks.
        Each chunk includes entity_relations when include_graph_context=True.
    """
    # Step 1: Generate query embedding
    query_embedding = await generate_query_embedding(query)

    # Step 2: Vector search in Qdrant with document filtering
    # Build filter for user_id AND document_id
    search_filter = Filter(
        must=[
            FieldCondition(key="user_id", match=MatchValue(value=user_id)),
            FieldCondition(key="document_id", match=MatchAny(any=document_ids)),
        ]
    )

    search_results = qdrant_client.search(
        collection_name=settings.QDRANT_COLLECTION,
        query_vector=query_embedding,
        query_filter=search_filter,
        limit=max_results,
        with_payload=True,
    )

    # Convert to standard chunk format
    chunks = []
    for result in search_results:
        chunks.append({
            "id": result.payload.get("chunk_id", str(result.id)),
            "score": result.score,
            "text": result.payload.get("text", ""),
            "position": result.payload.get("position", 0),
            "document_id": result.payload.get("document_id"),
        })

    # Step 3: Enrich with Neo4j metadata
    enriched_chunks = []
    with neo4j_driver.session(database=settings.NEO4J_DATABASE) as session:
        for chunk in chunks:
            result = session.run(
                """
                MATCH (c:Chunk {id: $chunk_id})<-[:CONTAINS]-(d:Document)
                RETURN d.filename AS filename, d.id AS document_id
                """,
                chunk_id=chunk["id"],
            )

            record = result.single()
            if record:
                enriched_chunks.append({
                    **chunk,
                    "filename": record["filename"],
                    "document_id": record["document_id"],
                })
            else:
                enriched_chunks.append({
                    **chunk,
                    "filename": "Unknown",
                })

    # Step 4: Optionally expand with graph context
    if include_graph_context and enriched_chunks:
        from app.services.graphrag_service import expand_graph_context

        chunk_ids = [c["id"] for c in enriched_chunks]
        graph_context = await expand_graph_context(chunk_ids)

        # Merge graph context into chunks
        for chunk in enriched_chunks:
            ctx = graph_context.get(chunk["id"], {})
            chunk["entity_relations"] = ctx.get("entity_relations", [])
            chunk["related_chunks"] = ctx.get("related_chunks", [])

    return {
        "chunks": enriched_chunks,
        "document_ids": document_ids,
        "graph_expanded": include_graph_context,
    }
