"""Query API endpoints for document Q&A with citations.

Provides the /query endpoint for asking questions about uploaded documents.
Implements QRY-01 (query), QRY-03 (citations), QRY-04 ("I don't know" fallback).
"""

from fastapi import APIRouter, Depends

from app.core.security import get_current_user
from app.models.schemas import Citation, QueryRequest, QueryResponse
from app.services.generation_service import generate_answer, generate_answer_no_context
from app.services.retrieval_service import retrieve_relevant_context

router = APIRouter()


@router.post("/", response_model=QueryResponse)
async def query_documents(
    request: QueryRequest,
    current_user: dict = Depends(get_current_user),
):
    """Ask a question about uploaded documents.

    Implements:
    - QRY-01: Natural language query processing
    - QRY-03: Source citations with document references
    - QRY-04: "I don't know" fallback when context insufficient

    Args:
        request: QueryRequest with query string and max_results.
        current_user: Authenticated user from JWT token.

    Returns:
        QueryResponse with answer and list of source citations.
    """
    user_id = current_user["id"]

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
