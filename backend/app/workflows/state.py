"""LangGraph workflow state schemas using TypedDict.

Provides strongly-typed state schemas for workflow state management.
All workflows should define their state schema here for consistency.
"""

from typing import List, Optional, TypedDict


class DocumentComparisonState(TypedDict):
    """State schema for document comparison workflow.

    Tracks the complete lifecycle of a document comparison request:
    1. Input: query, user_id, document_ids
    2. Retrieved data: chunks and graph context per document
    3. Analysis results: similarities, differences, insights
    4. Output: response with citations
    5. Workflow tracking: status and error handling
    """

    # Input
    query: str
    user_id: str
    document_ids: List[str]

    # Retrieved data
    # Structure: {doc_id: [{"id": chunk_id, "text": text, "score": score, ...}]}
    retrieved_chunks: dict
    # Structure: {doc_id: {"entity_relations": [...], "related_chunks": [...]}}
    graph_context: dict

    # Analysis results
    similarities: List[str]
    differences: List[str]
    cross_document_insights: List[str]

    # Output
    response: str
    # Structure: [{"doc_id": str, "chunk_id": str, "text": str, "filename": str}]
    citations: List[dict]

    # Workflow tracking
    status: str
    error: Optional[str]
