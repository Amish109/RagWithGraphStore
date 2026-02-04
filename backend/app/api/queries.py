"""Query API endpoints for document Q&A with citations.

Provides the /query endpoint for asking questions about uploaded documents.
Implements QRY-01 (query), QRY-03 (citations), QRY-04 ("I don't know" fallback).
Implements QRY-02 (streaming) via SSE at POST /stream.
Implements QRY-06 (document summaries) via GET /documents/{document_id}/summary.
Implements QRY-07 (text simplification) via POST /simplify.
Supports both authenticated and anonymous users via get_current_user_optional.
"""

import json
import logging
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sse_starlette.sse import EventSourceResponse

from app.core.security import get_current_user_optional
from app.models.schemas import (
    Citation,
    QueryRequest,
    QueryResponse,
    SimplifyRequest,
    SimplifyResponse,
    SummaryResponse,
    UserContext,
)
from app.services.generation_service import (
    generate_answer,
    generate_answer_no_context,
    stream_answer,
)
from app.services.retrieval_service import retrieve_relevant_context
from app.services.simplification_service import (
    SIMPLIFICATION_LEVELS,
    simplify_document_section,
    simplify_text,
)
from app.services.summarization_service import SUMMARY_PROMPTS, summarize_document

logger = logging.getLogger(__name__)

router = APIRouter()

# Module-level cache for summaries (simple in-memory cache)
_summary_cache: Dict[str, dict] = {}


@router.post("/", response_model=QueryResponse)
async def query_documents(
    request: QueryRequest,
    current_user: UserContext = Depends(get_current_user_optional),
):
    """Ask a question about uploaded documents.

    Implements:
    - QRY-01: Natural language query processing
    - QRY-03: Source citations with document references
    - QRY-04: "I don't know" fallback when context insufficient

    Supports both authenticated and anonymous users.

    Args:
        request: QueryRequest with query string and max_results.
        current_user: UserContext (authenticated or anonymous).

    Returns:
        QueryResponse with answer and list of source citations.
    """
    user_id = current_user.id  # Works for both authenticated and anonymous

    # Step 1: Retrieve relevant context (filtered by user_id)
    context = await retrieve_relevant_context(
        query=request.query,
        user_id=user_id,
        max_results=request.max_results,
    )

    # Step 2: Handle no context case (QRY-04)
    if not context["chunks"]:
        return QueryResponse(
            answer=await generate_answer_no_context(),
            citations=[],
        )

    # Step 3: Generate answer from context
    answer = await generate_answer(
        query=request.query,
        context=context["chunks"],
    )

    # Step 4: Format citations (QRY-03)
    citations = [
        Citation(
            document_id=chunk["document_id"],
            filename=chunk["filename"],
            chunk_text=(
                chunk["text"][:200] + "..." if len(chunk["text"]) > 200 else chunk["text"]
            ),
            relevance_score=chunk["score"],
        )
        for chunk in context["chunks"]
    ]

    return QueryResponse(answer=answer, citations=citations)


@router.post("/stream")
async def query_stream(
    request: Request,
    query_request: QueryRequest,
    current_user: UserContext = Depends(get_current_user_optional),
):
    """Stream query response using Server-Sent Events (SSE).

    Implements QRY-02: Streaming responses with visible progress.

    SSE Event Types:
    - status: Processing stage updates ({"stage": "retrieving"|"generating"})
    - citations: Source documents found (list of citation objects)
    - token: Individual response tokens as they are generated
    - done: Stream complete signal
    - error: Error message if something goes wrong

    Args:
        request: FastAPI request (for disconnect detection).
        query_request: QueryRequest with query string and max_results.
        current_user: Authenticated or anonymous user from JWT/session.

    Returns:
        EventSourceResponse streaming tokens and metadata.
    """
    user_id = current_user.id

    async def event_generator():
        try:
            # Step 1: Retrieve context
            yield {
                "event": "status",
                "data": json.dumps({"stage": "retrieving"})
            }

            context = await retrieve_relevant_context(
                query=query_request.query,
                user_id=user_id,
                max_results=query_request.max_results,
            )

            # Step 2: Handle no context case (QRY-04)
            if not context["chunks"]:
                no_context_response = await generate_answer_no_context()
                yield {
                    "event": "token",
                    "data": no_context_response
                }
                yield {"event": "done", "data": ""}
                return

            # Step 3: Send citations
            citations = [
                {
                    "document_id": chunk["document_id"],
                    "filename": chunk["filename"],
                    "chunk_text": chunk["text"][:200] + "..." if len(chunk["text"]) > 200 else chunk["text"],
                    "relevance_score": chunk["score"]
                }
                for chunk in context["chunks"]
            ]
            yield {
                "event": "citations",
                "data": json.dumps(citations)
            }

            # Step 4: Stream LLM response
            yield {
                "event": "status",
                "data": json.dumps({"stage": "generating"})
            }

            async for token in stream_answer(query_request.query, context["chunks"]):
                # Check for client disconnect (Pitfall #5)
                if await request.is_disconnected():
                    break
                yield {"event": "token", "data": token}

            yield {"event": "done", "data": ""}

        except Exception as e:
            # Log error but send user-friendly message
            logger.exception(f"Streaming error: {e}")
            yield {
                "event": "error",
                "data": json.dumps({"message": "An error occurred while generating the response."})
            }

    return EventSourceResponse(
        event_generator(),
        headers={
            "X-Accel-Buffering": "no",  # Disable nginx buffering (Pitfall #1)
            "Cache-Control": "no-cache",
        }
    )


@router.get("/documents/{document_id}/summary", response_model=SummaryResponse)
async def get_document_summary(
    document_id: str,
    summary_type: str = Query(
        default="brief",
        enum=["brief", "detailed", "executive", "bullet"],
        description="Type of summary to generate"
    ),
    current_user: UserContext = Depends(get_current_user_optional),
):
    """Get summary of a document (QRY-06).

    Summary types:
    - brief: 2-3 sentence overview
    - detailed: Comprehensive coverage of all key points
    - executive: Business-focused with recommendations
    - bullet: Key points as bulleted list

    Summaries are cached for performance.
    Supports both authenticated and anonymous users.

    Args:
        document_id: ID of the document to summarize.
        summary_type: Type of summary to generate.
        current_user: UserContext (authenticated or anonymous).

    Returns:
        SummaryResponse with document_id, summary_type, summary, method.

    Raises:
        HTTPException 404: Document not found or user doesn't have access.
    """
    user_id = current_user.id

    result = await summarize_document(
        document_id=document_id,
        user_id=user_id,
        summary_type=summary_type,
        cache_dict=_summary_cache,
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found or you don't have access"
        )

    return SummaryResponse(**result)


@router.post("/simplify", response_model=SimplifyResponse)
async def simplify_content(
    request: SimplifyRequest,
    current_user: UserContext = Depends(get_current_user_optional),
):
    """Simplify complex text to specified reading level (QRY-07).

    Levels:
    - eli5: Child-friendly explanation (elementary reading level)
    - general: General audience (8th grade reading level, default)
    - professional: Professionals from other fields (college reading level)

    Uses two-stage prompting: simplify then verify reading level.
    Supports both authenticated and anonymous users.

    Args:
        request: SimplifyRequest with text, optional document_id, and level.
        current_user: UserContext (authenticated or anonymous).

    Returns:
        SimplifyResponse with original_text, simplified_text, level, level_description.

    Raises:
        HTTPException 400: Invalid simplification level.
    """
    # Validate level
    if request.level not in SIMPLIFICATION_LEVELS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid level '{request.level}'. Must be one of: {list(SIMPLIFICATION_LEVELS.keys())}"
        )

    user_id = current_user.id

    # If document_id provided, use context-aware simplification
    if request.document_id:
        result = await simplify_document_section(
            document_id=request.document_id,
            user_id=user_id,
            section_text=request.text,
            level=request.level,
        )
    else:
        # Direct simplification without document context
        result = await simplify_text(
            text=request.text,
            level=request.level,
        )

    return SimplifyResponse(**result)
