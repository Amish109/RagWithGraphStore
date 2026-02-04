"""Retrieval workflow nodes for document comparison.

Provides nodes for:
- Retrieving chunks from specific documents
- Expanding context via multi-hop graph traversal
"""

import logging
from typing import Dict

from app.services.retrieval_service import retrieve_for_documents
from app.services.graphrag_service import expand_graph_context
from app.workflows.state import DocumentComparisonState

logger = logging.getLogger(__name__)


async def retrieve_documents_node(state: DocumentComparisonState) -> Dict:
    """Retrieve chunks from specified documents.

    For each document ID in the state, retrieves relevant chunks
    based on the query using vector search with document filtering.

    Args:
        state: Current workflow state containing query, user_id, document_ids.

    Returns:
        Dict with retrieved_chunks and updated status.
        retrieved_chunks structure: {doc_id: [chunk_dicts]}
    """
    logger.info(
        f"Retrieving chunks for {len(state['document_ids'])} documents, "
        f"user_id={state['user_id']}"
    )

    retrieved: Dict[str, list] = {}

    for doc_id in state["document_ids"]:
        try:
            result = await retrieve_for_documents(
                query=state["query"],
                user_id=state["user_id"],
                document_ids=[doc_id],
                max_results=5,
                include_graph_context=False,  # Graph expansion in next node
            )
            retrieved[doc_id] = result.get("chunks", [])
            logger.debug(f"Retrieved {len(retrieved[doc_id])} chunks for doc {doc_id}")
        except Exception as e:
            logger.error(f"Failed to retrieve chunks for document {doc_id}: {e}")
            retrieved[doc_id] = []

    total_chunks = sum(len(chunks) for chunks in retrieved.values())
    logger.info(f"Retrieved {total_chunks} total chunks across all documents")

    return {
        "retrieved_chunks": retrieved,
        "status": "chunks_retrieved",
    }


async def expand_graph_context_node(state: DocumentComparisonState) -> Dict:
    """Expand context via multi-hop graph traversal.

    Takes retrieved chunks and expands their context by traversing
    entity relationships in Neo4j. This enables cross-document
    relationship discovery.

    Args:
        state: Current workflow state with retrieved_chunks.

    Returns:
        Dict with graph_context and updated status.
        graph_context structure: {doc_id: {entity_relations, related_chunks}}
    """
    logger.info("Expanding graph context for retrieved chunks")

    graph_context: Dict[str, dict] = {}

    for doc_id, chunks in state["retrieved_chunks"].items():
        if not chunks:
            graph_context[doc_id] = {
                "entity_relations": [],
                "related_chunks": [],
            }
            continue

        # Extract chunk IDs for graph expansion
        chunk_ids = [c["id"] for c in chunks if "id" in c]

        if not chunk_ids:
            graph_context[doc_id] = {
                "entity_relations": [],
                "related_chunks": [],
            }
            continue

        try:
            # Expand context via entity graph traversal
            expanded = await expand_graph_context(chunk_ids)

            # Aggregate entity relations and related chunks
            all_entity_relations = []
            all_related_chunks = set()

            for chunk_id, ctx in expanded.items():
                entity_rels = ctx.get("entity_relations", [])
                all_entity_relations.extend(entity_rels)

                related = ctx.get("related_chunks", [])
                all_related_chunks.update(related)

            graph_context[doc_id] = {
                "entity_relations": all_entity_relations,
                "related_chunks": list(all_related_chunks),
                "filename": expanded.get(chunk_ids[0], {}).get("filename"),
            }

            logger.debug(
                f"Doc {doc_id}: {len(all_entity_relations)} entity relations, "
                f"{len(all_related_chunks)} related chunks"
            )

        except Exception as e:
            logger.error(f"Failed to expand graph context for doc {doc_id}: {e}")
            graph_context[doc_id] = {
                "entity_relations": [],
                "related_chunks": [],
            }

    logger.info(f"Graph expansion complete for {len(graph_context)} documents")

    return {
        "graph_context": graph_context,
        "status": "graph_expanded",
    }
