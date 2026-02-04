"""Query API endpoints for document Q&A with citations.

Provides the /query endpoint for asking questions about uploaded documents.
Implements QRY-01 (query), QRY-03 (citations), QRY-04 ("I don't know" fallback).
Implements QRY-02 (streaming) via SSE at POST /stream.
Supports both authenticated and anonymous users via get_current_user_optional.
"""

import json
import logging

from fastapi import APIRouter, Depends, Request
from sse_starlette.sse import EventSourceResponse

from app.core.security import get_current_user_optional
from app.models.schemas import Citation, QueryRequest, QueryResponse, UserContext
from app.services.generation_service import (
    generate_answer,
    generate_answer_no_context,
    stream_answer,
)
from app.services.retrieval_service import retrieve_relevant_context

logger = logging.getLogger(__name__)

router = APIRouter()


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
