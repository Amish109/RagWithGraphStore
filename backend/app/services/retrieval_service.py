"""Retrieval service for document context retrieval using hybrid vector+graph search.

Phase 1: Vector-only retrieval from Qdrant with Neo4j metadata enrichment.
Phase 4+: Graph-based retrieval for relationship-aware context via GraphRAG.
Phase 5: Highlighted citation extraction with exact text passages.
Phase 6: Hybrid retrieval — vector search + graph entity lookup merged & re-ranked.
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional

from langchain_core.prompts import ChatPromptTemplate

from app.config import settings
from app.services.llm_provider import get_llm
from app.db.neo4j_client import neo4j_driver
from app.db.qdrant_client import search_similar_chunks, qdrant_client
from app.models.schemas import HighlightedCitation
from app.services.embedding_service import generate_query_embedding
from qdrant_client.models import Filter, FieldCondition, MatchValue, MatchAny

logger = logging.getLogger(__name__)


def _enrich_chunks_with_neo4j(chunks: List[Dict]) -> List[Dict]:
    """Enrich chunks with document metadata from Neo4j.

    Args:
        chunks: List of chunk dicts with 'id' key.

    Returns:
        List of enriched chunk dicts with 'filename' and 'document_id' added.
    """
    enriched = []
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
                enriched.append({
                    **chunk,
                    "filename": record["filename"],
                    "document_id": record["document_id"],
                })
            else:
                enriched.append({
                    **chunk,
                    "filename": "Unknown",
                })
    return enriched


def _merge_and_rerank(
    vector_chunks: List[Dict],
    graph_chunks: List[Dict],
    max_results: int,
) -> List[Dict]:
    """Merge vector search and graph entity lookup results, deduplicate, and re-rank.

    Scoring strategy:
    - Vector-only chunks keep their cosine similarity score
    - Graph-only chunks get a base score of 0.7
    - Chunks found by BOTH methods get a boosted score (vector_score * 1.2)

    This rewards chunks that are both semantically similar AND entity-matched,
    which strongly signals relevance.

    Args:
        vector_chunks: Chunks from vector search (have 'score' from cosine similarity).
        graph_chunks: Chunks from graph entity lookup.
        max_results: Maximum number of chunks to return.

    Returns:
        Merged, deduplicated, and re-ranked list of chunks.
    """
    # Build lookup by chunk ID
    merged: Dict[str, Dict] = {}

    # Add vector chunks first (they have real similarity scores)
    for chunk in vector_chunks:
        chunk_id = chunk["id"]
        merged[chunk_id] = {
            **chunk,
            "retrieval_method": "vector",
        }

    # Merge graph chunks — boost if already found by vector search
    for chunk in graph_chunks:
        chunk_id = chunk["id"]
        if chunk_id in merged:
            # Found by both — boost the score
            existing = merged[chunk_id]
            existing["score"] = min(existing["score"] * 1.2, 1.0)
            existing["retrieval_method"] = "hybrid"
            # Carry over entity match info
            existing["matched_entity"] = chunk.get("matched_entity")
            existing["entity_type"] = chunk.get("entity_type")
        else:
            # Graph-only: add with graph score
            merged[chunk_id] = {**chunk}

    # Sort by score descending and return top N
    result = sorted(merged.values(), key=lambda c: c.get("score", 0), reverse=True)
    return result[:max_results]


async def retrieve_relevant_context(
    query: str,
    user_id: str,
    max_results: int = 3,
    include_graph_context: bool = True,
) -> Dict:
    """Retrieve relevant context using hybrid vector + graph search.

    Combines two retrieval paths:
    1. Vector search (Qdrant) — semantic similarity
    2. Graph entity lookup (Neo4j) — entity name matching from query

    Results are merged, deduplicated, and re-ranked. Chunks found by
    both methods get a boosted score. Then optionally expanded with
    multi-hop entity relationships.

    CRITICAL: Always filter by user_id for multi-tenant isolation.

    Args:
        query: User's question or search query.
        user_id: ID of the user (for multi-tenant filtering).
        max_results: Maximum number of context chunks to return.
        include_graph_context: If True, expand context via entity graph traversal.

    Returns:
        Dict with 'chunks' key containing list of enriched context chunks.
    """
    # Step 1: Generate query embedding
    query_embedding = await generate_query_embedding(query)

    # Step 2: Run vector search and graph entity lookup in parallel
    vector_task = asyncio.get_event_loop().run_in_executor(
        None,
        lambda: search_similar_chunks(
            query_vector=query_embedding,
            user_id=user_id,
            limit=max_results,
        ),
    )

    # Graph entity lookup (extracts entities from query, looks them up in Neo4j)
    graph_task = _safe_graph_entity_lookup(query, user_id, limit=max_results)

    vector_chunks, graph_chunks = await asyncio.gather(vector_task, graph_task)

    # Step 3: Enrich vector chunks with Neo4j metadata
    enriched_vector = _enrich_chunks_with_neo4j(vector_chunks)

    # Graph chunks already have filename/document_id from the Cypher query
    # but may need Neo4j enrichment for chunks that don't have it
    enriched_graph = [c for c in graph_chunks if c.get("filename")]

    # Step 4: Merge and re-rank
    merged_chunks = _merge_and_rerank(enriched_vector, enriched_graph, max_results)

    if graph_chunks:
        logger.info(
            f"Hybrid retrieval: {len(vector_chunks)} vector + "
            f"{len(graph_chunks)} graph → {len(merged_chunks)} merged"
        )

    # Step 5: Optionally expand with multi-hop graph context
    if include_graph_context and merged_chunks:
        from app.services.graphrag_service import expand_graph_context

        chunk_ids = [c["id"] for c in merged_chunks]
        graph_context = await expand_graph_context(chunk_ids)

        for chunk in merged_chunks:
            ctx = graph_context.get(chunk["id"], {})
            chunk["entity_relations"] = ctx.get("entity_relations", [])
            chunk["related_chunks"] = ctx.get("related_chunks", [])

    return {"chunks": merged_chunks}


async def retrieve_for_documents(
    query: str,
    user_id: str,
    document_ids: List[str],
    max_results: int = 5,
    include_graph_context: bool = True,
) -> Dict:
    """Retrieve relevant context filtered by specific documents using hybrid search.

    Combines vector search (scoped to document_ids) with graph entity lookup
    (also scoped to document_ids) for document-specific chat.

    Args:
        query: User's question or search query.
        user_id: ID of the user (for multi-tenant filtering).
        document_ids: List of document IDs to filter results to.
        max_results: Maximum number of context chunks to return.
        include_graph_context: If True, expand context via entity graph traversal.

    Returns:
        Dict with 'chunks' key containing list of enriched context chunks.
    """
    # Step 1: Generate query embedding
    query_embedding = await generate_query_embedding(query)

    # Step 2: Vector search in Qdrant with document filtering
    search_filter = Filter(
        must=[
            FieldCondition(key="user_id", match=MatchValue(value=user_id)),
            FieldCondition(key="document_id", match=MatchAny(any=document_ids)),
        ]
    )

    # Run vector search and graph entity lookup in parallel
    async def _vector_search():
        response = qdrant_client.query_points(
            collection_name=settings.QDRANT_COLLECTION,
            query=query_embedding,
            query_filter=search_filter,
            limit=max_results,
            with_payload=True,
        )
        return [
            {
                "id": result.payload.get("chunk_id", str(result.id)),
                "score": result.score,
                "text": result.payload.get("text", ""),
                "position": result.payload.get("position", 0),
                "document_id": result.payload.get("document_id"),
            }
            for result in response.points
        ]

    graph_task = _safe_graph_entity_lookup(
        query, user_id, document_ids=document_ids, limit=max_results
    )

    vector_chunks, graph_chunks = await asyncio.gather(
        _vector_search(), graph_task
    )

    # Step 3: Enrich vector chunks with Neo4j metadata
    enriched_vector = _enrich_chunks_with_neo4j(vector_chunks)
    enriched_graph = [c for c in graph_chunks if c.get("filename")]

    # Step 4: Merge and re-rank
    merged_chunks = _merge_and_rerank(enriched_vector, enriched_graph, max_results)

    if graph_chunks:
        logger.info(
            f"Hybrid doc retrieval: {len(vector_chunks)} vector + "
            f"{len(graph_chunks)} graph → {len(merged_chunks)} merged"
        )

    # Step 5: Optionally expand with graph context
    if include_graph_context and merged_chunks:
        from app.services.graphrag_service import expand_graph_context

        chunk_ids = [c["id"] for c in merged_chunks]
        graph_context = await expand_graph_context(chunk_ids)

        for chunk in merged_chunks:
            ctx = graph_context.get(chunk["id"], {})
            chunk["entity_relations"] = ctx.get("entity_relations", [])
            chunk["related_chunks"] = ctx.get("related_chunks", [])

    return {
        "chunks": merged_chunks,
        "document_ids": document_ids,
        "graph_expanded": include_graph_context,
    }


async def _safe_graph_entity_lookup(
    query: str,
    user_id: str,
    document_ids: Optional[List[str]] = None,
    limit: int = 5,
) -> List[Dict]:
    """Safely run graph entity lookup — returns empty list on failure.

    This wraps get_entity_chunks_for_query with error handling so that
    graph lookup failures don't break the entire retrieval pipeline.
    The entity extraction from the query uses the LLM, which may be slow
    or fail — vector search should still work independently.
    """
    if not settings.GRAPHRAG_ENABLED:
        return []

    try:
        from app.services.graphrag_service import get_entity_chunks_for_query
        return await get_entity_chunks_for_query(
            query=query,
            user_id=user_id,
            document_ids=document_ids,
            limit=limit,
        )
    except Exception as e:
        logger.warning(f"Graph entity lookup failed (non-fatal): {e}")
        return []


async def extract_highlighted_citations(
    answer: str,
    context_chunks: List[Dict],
    query: str,
) -> List[HighlightedCitation]:
    """Extract highlighted citations by identifying exact passages supporting the answer.

    Uses LLM to identify the most relevant passage within each chunk that
    supports the generated answer. CRITICAL: Verifies highlighted_passage
    exists verbatim in chunk_text to prevent hallucination (Pitfall #3).

    Phase 5 - Success Criteria #4: Highlighted citations with exact text passages.

    Args:
        answer: The generated answer to find supporting text for.
        context_chunks: List of context chunks used to generate the answer.
            Each chunk should have: text, document_id, filename, score, position.
        query: Original user query for context.

    Returns:
        List of HighlightedCitation objects with exact text passages and offsets.
    """
    llm = get_llm(temperature=0)

    citations = []

    for chunk in context_chunks:
        chunk_text = chunk.get("text", "")
        if not chunk_text:
            continue

        # Ask LLM to identify the most relevant passage
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are a citation extraction expert. Given an answer and a source chunk,
identify the exact passage in the chunk that best supports the answer.

CRITICAL: You must copy the text EXACTLY as it appears in the chunk. Do not paraphrase.

Return JSON with:
- highlighted_passage: The exact text from the chunk that supports the answer (copy verbatim, max 300 characters)

Only return the JSON object, no other text.""",
                ),
                (
                    "user",
                    """Answer being cited: {answer}

Source chunk:
{chunk_text}

Identify the most relevant passage (copy exact text):""",
                ),
            ]
        )

        messages = prompt.format_messages(answer=answer, chunk_text=chunk_text)

        try:
            response = await llm.ainvoke(messages)

            # Parse JSON response
            response_text = response.content.strip()

            # Handle potential markdown code blocks
            if response_text.startswith("```"):
                lines = response_text.split("\n")
                # Remove first and last lines (```json and ```)
                response_text = "\n".join(lines[1:-1])

            result = json.loads(response_text)
            highlighted = result.get("highlighted_passage", "")

            # CRITICAL: Verify highlighted passage exists in chunk (Pitfall #3)
            start = chunk_text.find(highlighted)
            end = start + len(highlighted) if start >= 0 else -1

            if start < 0 or not highlighted:
                # Fallback: use first 200 chars if exact match fails
                highlighted = (
                    chunk_text[:200] + "..."
                    if len(chunk_text) > 200
                    else chunk_text
                )
                start = 0
                end = min(200, len(chunk_text))

            citations.append(
                HighlightedCitation(
                    document_id=chunk.get("document_id", ""),
                    filename=chunk.get("filename", "Unknown"),
                    page_number=chunk.get("page_number"),
                    chunk_text=chunk_text,
                    highlighted_passage=highlighted,
                    highlight_start=start,
                    highlight_end=end,
                    relevance_score=chunk.get("score", 0.0),
                    chunk_position=chunk.get("position", 0),
                )
            )

        except (json.JSONDecodeError, KeyError, TypeError):
            # Fallback: use chunk text truncation if LLM fails
            highlighted = (
                chunk_text[:200] + "..."
                if len(chunk_text) > 200
                else chunk_text
            )
            citations.append(
                HighlightedCitation(
                    document_id=chunk.get("document_id", ""),
                    filename=chunk.get("filename", "Unknown"),
                    page_number=chunk.get("page_number"),
                    chunk_text=chunk_text,
                    highlighted_passage=highlighted,
                    highlight_start=0,
                    highlight_end=min(200, len(chunk_text)),
                    relevance_score=chunk.get("score", 0.0),
                    chunk_position=chunk.get("position", 0),
                )
            )

    return citations
