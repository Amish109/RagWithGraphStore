"""GraphRAG multi-hop retrieval service using Neo4j graph traversal.

Provides:
- expand_graph_context(): Expand chunk context via entity relationships
- retrieve_with_graph_expansion(): Full retrieval pipeline with graph expansion

Enables cross-document entity relationship traversal for richer context
(Phase 4 Success Criteria #2).
"""

import logging
from typing import Dict, List, Optional

from app.config import settings
from app.db.neo4j_client import neo4j_driver

logger = logging.getLogger(__name__)

# Multi-hop graph traversal query
# Finds related entities and their appearances in other chunks
# CRITICAL: Always use LIMIT to prevent query explosion (Pitfall #3)
MULTI_HOP_QUERY = """
MATCH (c:Chunk {id: $chunk_id})<-[:CONTAINS]-(d:Document)
OPTIONAL MATCH (e:Entity)-[:APPEARS_IN]->(c)
OPTIONAL MATCH (e)-[r:RELATES_TO]-(related:Entity)-[:APPEARS_IN]->(other_chunk:Chunk)
WHERE other_chunk.id <> c.id
RETURN c.id AS chunk_id,
       d.id AS document_id,
       d.filename AS filename,
       collect(DISTINCT {
           entity: e.name,
           type: labels(e)[0],
           related_entity: related.name,
           relation: type(r),
           related_chunk_id: other_chunk.id
       })[0..10] AS entity_relations
LIMIT 50
"""

# Simpler query for when Entity nodes don't exist yet
# Falls back to document-level relationships
DOCUMENT_CONTEXT_QUERY = """
MATCH (c:Chunk {id: $chunk_id})<-[:CONTAINS]-(d:Document)
OPTIONAL MATCH (d)-[:CONTAINS]->(sibling:Chunk)
WHERE sibling.id <> c.id
WITH c, d, collect(DISTINCT sibling.id)[0..5] AS sibling_chunk_ids
RETURN c.id AS chunk_id,
       d.id AS document_id,
       d.filename AS filename,
       sibling_chunk_ids AS related_chunks
LIMIT 1
"""


async def expand_graph_context(
    chunk_ids: List[str],
    max_hops: int = 2
) -> Dict[str, List[Dict]]:
    """Expand chunk context via Neo4j graph traversal.

    Traverses entity relationships to find related content across documents.
    This enables multi-hop reasoning where one chunk's entities connect
    to entities in other chunks.

    Args:
        chunk_ids: List of chunk IDs to expand context for.
        max_hops: Maximum relationship hops (default 2 for performance).

    Returns:
        Dict mapping chunk_id to list of entity_relations dicts.
        Each relation has: entity, type, related_entity, relation, related_chunk_id.
    """
    context: Dict[str, List[Dict]] = {}

    with neo4j_driver.session(database=settings.NEO4J_DATABASE) as session:
        for chunk_id in chunk_ids:
            # Try multi-hop query first (requires Entity nodes)
            result = session.run(MULTI_HOP_QUERY, chunk_id=chunk_id)
            record = result.single()

            if record:
                entity_relations = record.get("entity_relations", [])
                # Filter out None values from optional matches
                valid_relations = [
                    rel for rel in entity_relations
                    if rel.get("entity") is not None
                ]
                context[chunk_id] = {
                    "document_id": record.get("document_id"),
                    "filename": record.get("filename"),
                    "entity_relations": valid_relations,
                }
            else:
                # Fall back to simpler document-level context
                fallback_result = session.run(
                    DOCUMENT_CONTEXT_QUERY, chunk_id=chunk_id
                )
                fallback_record = fallback_result.single()

                if fallback_record:
                    context[chunk_id] = {
                        "document_id": fallback_record.get("document_id"),
                        "filename": fallback_record.get("filename"),
                        "related_chunks": fallback_record.get("related_chunks", []),
                        "entity_relations": [],  # No entity nodes yet
                    }
                else:
                    context[chunk_id] = {
                        "document_id": None,
                        "filename": None,
                        "entity_relations": [],
                    }

    logger.debug(f"Expanded graph context for {len(chunk_ids)} chunks")
    return context


async def retrieve_with_graph_expansion(
    query: str,
    user_id: str,
    document_ids: Optional[List[str]] = None,
    max_results: int = 5
) -> Dict:
    """Retrieve chunks with graph-expanded context.

    Full retrieval pipeline that:
    1. Gets vector-similar chunks from Qdrant
    2. Enriches with Neo4j document metadata
    3. Expands context via entity graph traversal

    Args:
        query: User's question or search query.
        user_id: ID of the user (for multi-tenant filtering).
        document_ids: Optional list of document IDs to filter by.
        max_results: Maximum number of chunks to return.

    Returns:
        Dict with 'chunks' key containing list of enriched context chunks.
        Each chunk has: id, score, text, document_id, filename, entity_relations.
    """
    # Import here to avoid circular dependency
    from app.services.retrieval_service import retrieve_relevant_context

    # Step 1: Get base retrieval results (vector + Neo4j metadata)
    base_results = await retrieve_relevant_context(
        query=query,
        user_id=user_id,
        max_results=max_results
    )

    chunks = base_results.get("chunks", [])
    if not chunks:
        return {"chunks": [], "graph_expanded": False}

    # Filter by document_ids if specified
    if document_ids:
        chunks = [c for c in chunks if c.get("document_id") in document_ids]

    # Step 2: Extract chunk IDs for graph expansion
    chunk_ids = [c["id"] for c in chunks]

    # Step 3: Expand context via graph traversal
    graph_context = await expand_graph_context(chunk_ids)

    # Step 4: Merge graph context into chunks
    enriched_chunks = []
    for chunk in chunks:
        chunk_id = chunk["id"]
        ctx = graph_context.get(chunk_id, {})
        enriched_chunks.append({
            **chunk,
            "entity_relations": ctx.get("entity_relations", []),
            "related_chunks": ctx.get("related_chunks", []),
        })

    return {
        "chunks": enriched_chunks,
        "graph_expanded": True,
    }
