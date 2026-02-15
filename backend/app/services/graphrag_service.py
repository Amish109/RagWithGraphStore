"""GraphRAG multi-hop retrieval service using Neo4j graph traversal.

Provides:
- expand_graph_context(): Expand chunk context via entity relationships (true multi-hop)
- get_entity_chunks_for_query(): Find chunks via entity matching on query (with user_id filtering)
- get_entity_co_occurrences(): Find cross-document entity clusters
- retrieve_with_graph_expansion(): Full retrieval pipeline with graph expansion

Enables cross-document entity relationship traversal for richer context.
"""

import logging
from typing import Dict, List, Optional

from app.config import settings
from app.db.neo4j_client import neo4j_driver

logger = logging.getLogger(__name__)

# True multi-hop graph traversal query using variable-length paths.
# Traverses 1..N hops through entity relationships to discover
# indirect connections (A->B->C) that 1-hop queries miss.
# The path length is controlled by $max_hops parameter.
MULTI_HOP_QUERY = """
MATCH (c:Chunk {id: $chunk_id})<-[:CONTAINS]-(d:Document)
OPTIONAL MATCH (e:Entity)-[:APPEARS_IN]->(c)
OPTIONAL MATCH path = (e)-[:RELATES_TO*1..2]-(related:Entity)
WHERE related <> e
OPTIONAL MATCH (related)-[:APPEARS_IN]->(other_chunk:Chunk)
WHERE other_chunk.id <> c.id
WITH c, d, e, related, other_chunk,
     length(CASE WHEN path IS NOT NULL THEN path END) AS hop_distance
RETURN c.id AS chunk_id,
       d.id AS document_id,
       d.filename AS filename,
       collect(DISTINCT {
           entity: e.name,
           entity_type: e.type,
           related_entity: related.name,
           related_entity_type: related.type,
           hop_distance: hop_distance,
           related_chunk_id: other_chunk.id,
           related_chunk_text: other_chunk.text
       })[0..15] AS entity_relations
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

# Entity lookup query with user_id filtering for multi-tenant safety.
# Finds chunks containing specific entities, filtered to the user's documents.
ENTITY_LOOKUP_QUERY = """
UNWIND $names AS name
MATCH (e:Entity {normalized_name: name})-[:APPEARS_IN]->(c:Chunk)<-[:CONTAINS]-(d:Document)
WHERE d.user_id IN $user_ids
RETURN DISTINCT c.id AS chunk_id,
       c.text AS chunk_text,
       c.position AS position,
       d.id AS document_id,
       d.filename AS filename,
       e.name AS matched_entity,
       e.type AS entity_type
LIMIT $limit
"""

# Entity lookup with document_ids filtering (for document-scoped chat).
ENTITY_LOOKUP_BY_DOCS_QUERY = """
UNWIND $names AS name
MATCH (e:Entity {normalized_name: name})-[:APPEARS_IN]->(c:Chunk)<-[:CONTAINS]-(d:Document)
WHERE d.user_id IN $user_ids AND d.id IN $document_ids
RETURN DISTINCT c.id AS chunk_id,
       c.text AS chunk_text,
       c.position AS position,
       d.id AS document_id,
       d.filename AS filename,
       e.name AS matched_entity,
       e.type AS entity_type
LIMIT $limit
"""

# Entity co-occurrence query: finds entities that appear together across
# multiple documents. These "bridge entities" connect document clusters
# and reveal cross-document themes.
ENTITY_CO_OCCURRENCE_QUERY = """
MATCH (e:Entity)-[:APPEARS_IN]->(c:Chunk)<-[:CONTAINS]-(d:Document)
WHERE d.user_id IN $user_ids
WITH e, collect(DISTINCT d.id) AS doc_ids, count(DISTINCT d.id) AS doc_count
WHERE doc_count >= 2
RETURN e.name AS entity_name,
       e.type AS entity_type,
       e.normalized_name AS normalized_name,
       doc_ids,
       doc_count
ORDER BY doc_count DESC
LIMIT $limit
"""

# Find chunks where co-occurring entities appear, for enriching context
# with cross-document connections.
CO_OCCURRENCE_CHUNKS_QUERY = """
UNWIND $entity_names AS name
MATCH (e:Entity {normalized_name: name})-[:APPEARS_IN]->(c:Chunk)<-[:CONTAINS]-(d:Document)
WHERE d.user_id IN $user_ids
RETURN DISTINCT c.id AS chunk_id,
       c.text AS chunk_text,
       c.position AS position,
       d.id AS document_id,
       d.filename AS filename,
       e.name AS entity_name,
       e.type AS entity_type
LIMIT $limit
"""


async def expand_graph_context(
    chunk_ids: List[str],
    max_hops: int = 2
) -> Dict[str, Dict]:
    """Expand chunk context via Neo4j graph traversal with true multi-hop paths.

    Traverses entity relationships up to max_hops deep to find related content
    across documents. This enables multi-hop reasoning where one chunk's entities
    connect to entities in other chunks through intermediate relationships.

    Args:
        chunk_ids: List of chunk IDs to expand context for.
        max_hops: Maximum relationship hops (default 2).

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
    user_id: str,
    document_ids: Optional[List[str]] = None,
    limit: int = 5,
) -> List[Dict]:
    """Find chunks by extracting entities from the query and looking them up in Neo4j.

    This provides a graph-based retrieval path that complements vector search.
    Entities mentioned in the query are matched against the knowledge graph
    to find chunks where those entities appear.

    Multi-tenant safe: filters by user_id to only return the user's documents
    (plus shared documents).

    Args:
        query: User's query text.
        user_id: ID of the user (for multi-tenant filtering).
        document_ids: Optional list of document IDs to scope to.
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

    # Include user's docs + shared docs
    user_ids = [user_id, settings.SHARED_MEMORY_USER_ID]

    with neo4j_driver.session(database=settings.NEO4J_DATABASE) as session:
        if document_ids:
            result = session.run(
                ENTITY_LOOKUP_BY_DOCS_QUERY,
                names=normalized_names,
                user_ids=user_ids,
                document_ids=document_ids,
                limit=limit,
            )
        else:
            result = session.run(
                ENTITY_LOOKUP_QUERY,
                names=normalized_names,
                user_ids=user_ids,
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
                "score": 0.7,  # Graph-retrieved chunks get decent score
                "retrieval_method": "graph_entity_lookup",
            })

    if chunks:
        logger.info(
            f"Graph entity lookup found {len(chunks)} chunks for "
            f"entities: {normalized_names}"
        )
    return chunks


async def get_entity_co_occurrences(
    user_id: str,
    limit: int = 10,
) -> List[Dict]:
    """Find entities that appear across multiple documents (bridge entities).

    These entities connect different documents and reveal cross-document
    themes and relationships. Useful for identifying what concepts/people/orgs
    span multiple uploaded documents.

    Args:
        user_id: ID of the user (for multi-tenant filtering).
        limit: Maximum number of co-occurring entities to return.

    Returns:
        List of dicts with entity_name, entity_type, doc_ids, doc_count.
    """
    user_ids = [user_id, settings.SHARED_MEMORY_USER_ID]

    with neo4j_driver.session(database=settings.NEO4J_DATABASE) as session:
        result = session.run(
            ENTITY_CO_OCCURRENCE_QUERY,
            user_ids=user_ids,
            limit=limit,
        )
        co_occurrences = []
        for record in result:
            co_occurrences.append({
                "entity_name": record["entity_name"],
                "entity_type": record["entity_type"],
                "normalized_name": record["normalized_name"],
                "doc_ids": record["doc_ids"],
                "doc_count": record["doc_count"],
            })

    if co_occurrences:
        logger.info(
            f"Found {len(co_occurrences)} cross-document entities for user {user_id}"
        )
    return co_occurrences


async def get_co_occurrence_chunks(
    entity_names: List[str],
    user_id: str,
    limit: int = 5,
) -> List[Dict]:
    """Get chunks where cross-document entities appear.

    Given a list of entity normalized names (from get_entity_co_occurrences),
    finds chunks containing those entities to enrich query context with
    cross-document connections.

    Args:
        entity_names: List of normalized entity names to look up.
        user_id: ID of the user (for multi-tenant filtering).
        limit: Maximum chunks to return.

    Returns:
        List of chunk dicts with cross-document entity context.
    """
    user_ids = [user_id, settings.SHARED_MEMORY_USER_ID]

    with neo4j_driver.session(database=settings.NEO4J_DATABASE) as session:
        result = session.run(
            CO_OCCURRENCE_CHUNKS_QUERY,
            entity_names=entity_names,
            user_ids=user_ids,
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
                "matched_entity": record["entity_name"],
                "entity_type": record["entity_type"],
                "score": 0.6,
                "retrieval_method": "co_occurrence",
            })

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
