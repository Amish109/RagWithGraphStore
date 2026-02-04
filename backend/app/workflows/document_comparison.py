"""Document comparison LangGraph workflow.

Provides:
- create_comparison_workflow(): Build the LangGraph workflow with checkpointing
- compare_documents(): Execute document comparison with state persistence

This workflow enables multi-step reasoning for comparing documents:
1. Retrieve relevant chunks from each document
2. Expand context via graph traversal
3. Analyze similarities and differences using LLM
4. Generate final response with citations
"""

import logging
from typing import List, Optional

from langgraph.graph import StateGraph, END

from app.db.checkpoint_store import get_checkpointer
from app.workflows.state import DocumentComparisonState
from app.workflows.nodes.retrieval import (
    retrieve_documents_node,
    expand_graph_context_node,
)
from app.workflows.nodes.comparison import analyze_comparison_node
from app.workflows.nodes.generation import generate_response_node

logger = logging.getLogger(__name__)

# Module-level workflow cache
_workflow = None


async def create_comparison_workflow():
    """Create the document comparison LangGraph workflow.

    Builds a linear workflow with the following nodes:
    1. retrieve: Get relevant chunks from each document
    2. expand_graph: Expand context via entity relationships
    3. compare: Analyze similarities and differences
    4. generate: Produce final response with citations

    Uses PostgreSQL checkpointing for durable state persistence.

    Returns:
        Compiled LangGraph workflow with checkpointer attached.
    """
    global _workflow

    if _workflow is not None:
        return _workflow

    logger.info("Creating document comparison workflow")

    # Define the workflow graph
    workflow = StateGraph(DocumentComparisonState)

    # Add nodes
    workflow.add_node("retrieve", retrieve_documents_node)
    workflow.add_node("expand_graph", expand_graph_context_node)
    workflow.add_node("compare", analyze_comparison_node)
    workflow.add_node("generate", generate_response_node)

    # Define linear flow
    workflow.set_entry_point("retrieve")
    workflow.add_edge("retrieve", "expand_graph")
    workflow.add_edge("expand_graph", "compare")
    workflow.add_edge("compare", "generate")
    workflow.add_edge("generate", END)

    # Compile with checkpointer for state persistence
    checkpointer = await get_checkpointer()
    _workflow = workflow.compile(checkpointer=checkpointer)

    logger.info("Document comparison workflow created successfully")
    return _workflow


async def compare_documents(
    user_id: str,
    query: str,
    document_ids: List[str],
    session_id: Optional[str] = None,
) -> DocumentComparisonState:
    """Execute document comparison workflow.

    Compares specified documents using multi-step LangGraph workflow:
    1. Retrieves relevant chunks from each document
    2. Expands context via graph traversal
    3. Analyzes similarities and differences
    4. Generates response with citations

    Uses checkpointing for state persistence across requests.

    Args:
        user_id: ID of the user making the comparison request.
        query: User's comparison query (e.g., "Compare the main themes").
        document_ids: List of document IDs to compare.
        session_id: Optional session ID for thread management.
            If not provided, uses a hash of document_ids.

    Returns:
        DocumentComparisonState with complete results including:
        - response: Formatted comparison analysis
        - citations: List of source citations
        - similarities, differences, cross_document_insights: Analysis details

    Raises:
        ValueError: If fewer than 2 documents specified.
        Exception: If workflow execution fails.
    """
    if len(document_ids) < 2:
        raise ValueError("At least 2 documents required for comparison")

    # Generate session_id if not provided
    if session_id is None:
        # Create deterministic session ID from document IDs
        session_id = "_".join(sorted(document_ids)[:3])[:50]

    # CRITICAL: Thread ID includes user_id to prevent cross-user state mixing (Pitfall #5)
    thread_id = f"{user_id}:doc_compare:{session_id}"

    logger.info(
        f"Starting document comparison: {len(document_ids)} docs, "
        f"thread_id={thread_id}"
    )

    # Build config with thread_id for checkpointing
    config = {
        "configurable": {
            "thread_id": thread_id,
        }
    }

    # Build initial state
    initial_state: DocumentComparisonState = {
        "query": query,
        "user_id": user_id,
        "document_ids": document_ids,
        "retrieved_chunks": {},
        "graph_context": {},
        "similarities": [],
        "differences": [],
        "cross_document_insights": [],
        "response": "",
        "citations": [],
        "status": "started",
        "error": None,
    }

    # Get or create workflow
    workflow = await create_comparison_workflow()

    # Execute workflow (resumes from checkpoint if exists)
    try:
        result = await workflow.ainvoke(initial_state, config)
        logger.info(
            f"Comparison complete: status={result.get('status')}, "
            f"citations={len(result.get('citations', []))}"
        )
        return result
    except Exception as e:
        logger.error(f"Workflow execution failed: {e}")
        raise


async def get_comparison_state(
    user_id: str,
    session_id: str,
) -> Optional[DocumentComparisonState]:
    """Get the current state of a comparison workflow.

    Retrieves the persisted state for a given thread without
    executing any new workflow steps.

    Args:
        user_id: ID of the user.
        session_id: Session ID used in the comparison.

    Returns:
        Current workflow state if exists, None otherwise.
    """
    thread_id = f"{user_id}:doc_compare:{session_id}"

    config = {
        "configurable": {
            "thread_id": thread_id,
        }
    }

    workflow = await create_comparison_workflow()

    try:
        state = await workflow.aget_state(config)
        if state and state.values:
            return state.values
        return None
    except Exception as e:
        logger.error(f"Failed to get comparison state: {e}")
        return None
