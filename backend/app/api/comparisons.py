"""Document comparison API endpoints.

Provides:
- POST /compare: Compare multiple documents using LangGraph workflow
- GET /compare/{session_id}/state: Get workflow state for multi-turn queries

Implements Phase 4 Success Criteria #1 (document comparison) and #5 (citations).
Integrates with LangGraph workflow and memory summarization service.
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException

from app.core.security import get_current_user
from app.models.schemas import (
    ComparisonCitation,
    ComparisonRequest,
    ComparisonResponse,
)
from app.services.memory_summarizer import get_memory_summarizer
from app.workflows.document_comparison import (
    compare_documents,
    get_comparison_state,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=ComparisonResponse)
async def compare_documents_endpoint(
    request: ComparisonRequest,
    current_user: dict = Depends(get_current_user),
) -> ComparisonResponse:
    """Compare multiple documents and return analysis with citations.

    Executes LangGraph document comparison workflow:
    1. Retrieves relevant chunks from each document
    2. Expands context via graph traversal (GraphRAG)
    3. Analyzes similarities and differences using LLM
    4. Generates response with cross-document insights and citations

    Workflow state persists for multi-turn conversations using the session_id.
    Memory is updated and summarized after each interaction.

    Args:
        request: ComparisonRequest with document_ids (2-5), query, optional session_id.
        current_user: Authenticated user from JWT token.

    Returns:
        ComparisonResponse with similarities, differences, insights, and citations.

    Raises:
        HTTPException 400: If fewer than 2 documents provided.
        HTTPException 500: If comparison workflow fails.
    """
    user_id = current_user["sub"]

    # Generate session_id if not provided (new conversation)
    session_id = request.session_id or str(uuid.uuid4())

    logger.info(
        f"Document comparison requested: user={user_id}, "
        f"docs={len(request.document_ids)}, session={session_id}"
    )

    try:
        # Execute comparison workflow
        result = await compare_documents(
            user_id=user_id,
            query=request.query,
            document_ids=request.document_ids,
            session_id=session_id,
        )

        # Check for workflow errors
        if result.get("error"):
            logger.error(f"Comparison workflow error: {result['error']}")
            raise HTTPException(
                status_code=500,
                detail=f"Comparison failed: {result['error']}",
            )

        # Update memory with this interaction
        summarizer = get_memory_summarizer()
        await summarizer.add_interaction(
            user_id=user_id,
            query=request.query,
            response=result["response"],
            session_id=session_id,
        )

        # Build citations from workflow result
        citations = [
            ComparisonCitation(
                document_id=c.get("document_id", ""),
                chunk_id=c.get("chunk_id", ""),
                filename=c.get("filename", ""),
                text=c.get("text", "")[:500],  # Enforce max length
            )
            for c in result.get("citations", [])
        ]

        logger.info(
            f"Comparison complete: session={session_id}, "
            f"citations={len(citations)}"
        )

        return ComparisonResponse(
            similarities=result.get("similarities", []),
            differences=result.get("differences", []),
            cross_document_insights=result.get("cross_document_insights", []),
            response=result.get("response", ""),
            citations=citations,
            session_id=session_id,
            status=result.get("status", "completed"),
        )

    except HTTPException:
        raise
    except ValueError as e:
        # Handle validation errors (e.g., fewer than 2 documents)
        logger.warning(f"Comparison validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Comparison failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Comparison error: {str(e)}",
        )


@router.get("/{session_id}/state")
async def get_comparison_state_endpoint(
    session_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get current workflow state for a comparison session.

    Allows clients to check workflow state between turns in multi-turn
    document comparison conversations.

    Args:
        session_id: Session ID from previous comparison request.
        current_user: Authenticated user from JWT token.

    Returns:
        Current workflow state if exists, or 404 if session not found.
    """
    user_id = current_user["sub"]

    state = await get_comparison_state(
        user_id=user_id,
        session_id=session_id,
    )

    if state is None:
        raise HTTPException(
            status_code=404,
            detail=f"No comparison state found for session {session_id}",
        )

    return {
        "session_id": session_id,
        "status": state.get("status", "unknown"),
        "similarities_count": len(state.get("similarities", [])),
        "differences_count": len(state.get("differences", [])),
        "citations_count": len(state.get("citations", [])),
        "has_response": bool(state.get("response")),
    }
