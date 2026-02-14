"""GraphRAG multi-hop retrieval service using Neo4j graph traversal.

Provides:
- expand_graph_context(): Expand chunk context via entity relationships
- get_entity_chunks_for_query(): Find chunks via entity matching on query
- retrieve_with_graph_expansion(): Full retrieval pipeline with graph expansion

Enables cross-document entity relationship traversal for richer context.
"""

import logging
from typing import Dict, List, Optional

from app.config import settings
from app.db.neo4j_client import neo4j_driver

logger = logging.getLogger(__name__)

# Multi-hop graph traversal query
# Finds related entities and their appearances in other chunks
# Includes related_chunk_text so generation can use it directly
# CRITICAL: Always use LIMIT to prevent query explosion
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
           entity_type: e.type,
           related_entity: related.name,
           related_entity_type: related.type,
           relation: type(r),
           related_chunk_id: other_chunk.id,
           related_chunk_text: other_chunk.text
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

# Query to find chunks containing specific entities (by normalized name)
ENTITY_LOOKUP_QUERY = """
UNWIND $names AS name
MATCH (e:Entity {normalized_name: name})-[:APPEARS_IN]->(c:Chunk)<-[:CONTAINS]-(d:Document)
RETURN DISTINCT c.id AS chunk_id,
       c.text AS chunk_text,
       c.position AS position,
       d.id AS document_id,
       d.filename AS filename,
       e.name AS matched_entity,
       e.type AS entity_type
LIMIT $limit
"""


async def expand_graph_context(
    chunk_ids: List[str],
    max_hops: int = 2
) -> Dict[str, Dict]:
    """Expand chunk context via Neo4j graph traversal.

    Traverses entity relationships to find related content across documents.
    This enables multi-hop reasoning where one chunk's entities connect
    to entities in other chunks.

    Args:
        chunk_ids: List of chunk IDs to expand context for.
        max_hops: Maximum relationship hops (default 2 for performance).

    Returns:
        Dict mapping chunk_id to context dict with entity_relations and metadata.
    """
    context: Dict[str, Dict] = {}

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
                        "entity_relations": [],
                    }
                else:
                    context[chunk_id] = {
                        "document_id": None,
                        "filename": None,
                        "entity_relations": [],
                    }

    logger.debug(f"Expanded graph context for {len(chunk_ids)} chunks")
    return context


async def get_entity_chunks_for_query(
    query: str,
    limit: int = 5,
) -> List[Dict]:
    """Find chunks by extracting entities from the query and looking them up in Neo4j.

    This provides a graph-based retrieval path that complements vector search.
    Entities mentioned in the query are matched against the knowledge graph
    to find chunks where those entities appear.

    Args:
        query: User's query text.
        limit: Maximum chunks to return.

    Returns:
        List of chunk dicts with id, text, document_id, filename, matched_entity.
    """
    from app.services.entity_extraction_service import (
        extract_entities_from_chunk,
        normalize_entity_name,
    )

    # Extract entities from the query
    query_extraction = await extract_entities_from_chunk(query)
    query_entities = query_extraction.get("entities", [])

    if not query_entities:
        return []

    # Look up normalized names in Neo4j
    normalized_names = [
        normalize_entity_name(e["name"]) for e in query_entities
    ]

    with neo4j_driver.session(database=settings.NEO4J_DATABASE) as session:
        result = session.run(
            ENTITY_LOOKUP_QUERY,
            names=normalized_names,
            limit=limit,
        )
        chunks = []
        for record in result:
            chunks.append({
                "id": record["chunk_id"],
                "text": record["chunk_text"],
                "position": record.get("position", 0),
                "document_id": record["document_id"],
                "filename": record["filename"],
                "matched_entity": record["matched_entity"],
                "entity_type": record["entity_type"],
                "score": 0.5,  # Default score for graph-retrieved chunks
            })

    if chunks:
        logger.info(
            f"Graph entity lookup found {len(chunks)} chunks for "
            f"entities: {normalized_names}"
        )
    return chunks


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
