"""Query API endpoints for document Q&A with citations.

Provides the /query endpoint for asking questions about uploaded documents.
Implements QRY-01 (query), QRY-03 (citations), QRY-04 ("I don't know" fallback).
Implements QRY-02 (streaming) via SSE at POST /stream.
Implements QRY-06 (document summaries) via GET /documents/{document_id}/summary.
Implements QRY-07 (text simplification) via POST /simplify.
Supports both authenticated and anonymous users via get_current_user_optional.
"""

import asyncio
import json
import logging
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sse_starlette.sse import EventSourceResponse

from app.core.security import get_current_user_optional
from app.models.schemas import (
    Citation,
    ConfidenceScore,
    HighlightedCitation,
    QueryRequest,
    QueryResponse,
    QueryResponseWithCitations,
    SimplifyRequest,
    SimplifyResponse,
    SummaryResponse,
    UserContext,
)
from app.services.confidence_service import generate_answer_with_confidence
from app.services.generation_service import (
    generate_answer,
    generate_answer_no_context,
    stream_answer,
)
from app.services.retrieval_service import (
    extract_highlighted_citations,
    retrieve_for_documents,
    retrieve_relevant_context,
)
from app.services.simplification_service import (
    SIMPLIFICATION_LEVELS,
    simplify_document_section,
    simplify_text,
)
from app.services.summarization_service import SUMMARY_PROMPTS, summarize_document
from app.models.document import get_document_by_id
from app.services.summary_storage import (
    get_stream_content_from,
    get_stream_length,
    get_summary,
    get_summary_status,
    get_type_status,
    store_summary,
)

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
        include_graph_context=request.include_graph_context,
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

    Uses an LLM agent with tool-calling for providers that support it
    (OpenAI, Anthropic, OpenRouter). Falls back to direct retrieval pipeline
    for providers without tool support (Ollama).

    SSE Event Types:
    - status: Processing stage updates ({"stage": "thinking"|"retrieving"|"generating"})
    - tool_call: Agent is calling a tool ({"name": "...", "args": {...}})
    - citations: Source documents found (list of citation objects)
    - token: Individual response tokens as they are generated
    - done: Stream complete signal
    - error: Error message if something goes wrong

    Args:
        request: FastAPI request (for disconnect detection).
        query_request: QueryRequest with query string, max_results, and optional chat_history.
        current_user: Authenticated or anonymous user from JWT/session.

    Returns:
        EventSourceResponse streaming tokens and metadata.
    """
    user_id = current_user.id

    async def agent_event_generator():
        """Agent-based flow for tool-capable LLM providers."""
        from app.services.chat_agent import (
            DoneEvent,
            StatusEvent,
            TokenEvent,
            ToolCallEvent,
            run_agent,
        )

        try:
            yield {
                "event": "status",
                "data": json.dumps({"stage": "thinking"}),
            }

            full_response_tokens = []

            async for event in run_agent(
                query=query_request.query,
                user_id=user_id,
                document_ids=query_request.document_ids,
                chat_history=query_request.chat_history,
                include_shared_memory=not current_user.is_anonymous,
            ):
                if await request.is_disconnected():
                    break

                if isinstance(event, ToolCallEvent):
                    yield {
                        "event": "tool_call",
                        "data": json.dumps({
                            "name": event.name,
                            "args": event.args,
                        }),
                    }
                elif isinstance(event, StatusEvent):
                    yield {
                        "event": "status",
                        "data": json.dumps({"stage": event.stage}),
                    }
                elif isinstance(event, TokenEvent):
                    full_response_tokens.append(event.token)
                    yield {"event": "token", "data": event.token}
                elif isinstance(event, DoneEvent):
                    yield {"event": "done", "data": ""}

            # Save conversation to memory after completion
            if full_response_tokens:
                try:
                    from app.db.mem0_client import get_mem0
                    mem0 = get_mem0()
                    response_text = "".join(full_response_tokens)
                    mem0.add(
                        messages=[
                            {"role": "user", "content": query_request.query},
                            {"role": "assistant", "content": response_text},
                        ],
                        user_id=user_id,
                    )
                except Exception as e:
                    logger.warning(f"Memory save failed: {e}")

        except Exception as e:
            logger.exception(f"Agent streaming error: {e}")
            yield {
                "event": "error",
                "data": json.dumps({"message": "An error occurred while generating the response."}),
            }

    async def fallback_event_generator():
        """Direct retrieval pipeline for providers without tool support (Ollama)."""
        try:
            # Step 1: Retrieve context
            yield {
                "event": "status",
                "data": json.dumps({"stage": "retrieving"})
            }

            # Use document-scoped retrieval if document_ids provided
            if query_request.document_ids:
                context = await retrieve_for_documents(
                    query=query_request.query,
                    user_id=user_id,
                    document_ids=query_request.document_ids,
                    max_results=query_request.max_results,
                    include_graph_context=query_request.include_graph_context,
                )
            else:
                context = await retrieve_relevant_context(
                    query=query_request.query,
                    user_id=user_id,
                    max_results=query_request.max_results,
                    include_graph_context=query_request.include_graph_context,
                )

            # Step 1a: Inject document metadata + summary for document-specific chat
            if query_request.document_ids:
                doc_preambles = []
                for doc_id in query_request.document_ids:
                    doc_meta = get_document_by_id(doc_id, user_id)
                    brief_summary = get_summary(doc_id, "brief")

                    if doc_meta or brief_summary:
                        parts = []
                        if doc_meta:
                            fname = doc_meta.get("filename", "Unknown")
                            ftype = (doc_meta.get("file_type") or "unknown").upper()
                            chunks = doc_meta.get("chunk_count", "unknown")
                            parts.append(f"Document: {fname} (Type: {ftype}, Chunks: {chunks})")
                        if brief_summary:
                            parts.append(f"Document Summary: {brief_summary}")

                        if parts:
                            doc_preambles.append({
                                "text": "\n".join(parts),
                                "document_id": doc_id,
                                "filename": doc_meta.get("filename", "Document Overview") if doc_meta else "Document Overview",
                                "score": 1.0,
                                "id": f"preamble-{doc_id}",
                                "position": -1,
                            })

                context["chunks"] = doc_preambles + context["chunks"]

            # Step 1b: Include memory context
            memory_chunks = []
            try:
                from app.services.memory_service import search_with_shared
                memories = await search_with_shared(
                    user_id=user_id,
                    query=query_request.query,
                    limit=5,
                    include_shared=not current_user.is_anonymous,
                )
                memory_chunks = [
                    {
                        "text": m.get("memory", ""),
                        "document_id": "memory",
                        "filename": "Shared Memory" if m.get("is_shared") else "User Memory",
                        "score": m.get("score", 0.5),
                        "id": m.get("id", ""),
                        "position": 0,
                    }
                    for m in memories
                    if m.get("memory")
                ]
            except Exception as e:
                logger.warning(f"Memory retrieval failed: {e}")

            # Merge document chunks with memory chunks
            all_chunks = context["chunks"] + memory_chunks

            # Step 2: Handle no context case (QRY-04)
            if not all_chunks:
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
                for chunk in all_chunks
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

            full_response = []
            async for token in stream_answer(query_request.query, all_chunks):
                if await request.is_disconnected():
                    break
                full_response.append(token)
                yield {"event": "token", "data": token}

            yield {"event": "done", "data": ""}

            # Step 5: Save conversation to memory
            if full_response:
                try:
                    from app.db.mem0_client import get_mem0
                    mem0 = get_mem0()
                    response_text = "".join(full_response)
                    mem0.add(
                        messages=[
                            {"role": "user", "content": query_request.query},
                            {"role": "assistant", "content": response_text},
                        ],
                        user_id=user_id,
                    )
                except Exception as e:
                    logger.warning(f"Memory save failed: {e}")

        except Exception as e:
            logger.exception(f"Streaming error: {e}")
            yield {
                "event": "error",
                "data": json.dumps({"message": "An error occurred while generating the response."})
            }

    # Choose event generator based on provider capability
    from app.services.llm_provider import supports_tool_calling

    if supports_tool_calling():
        generator = agent_event_generator()
    else:
        generator = fallback_event_generator()

    return EventSourceResponse(
        generator,
        headers={
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-cache",
        }
    )


@router.get("/documents/{document_id}/summary", response_model=SummaryResponse)
async def get_document_summary(
    document_id: str,
    summary_type: str = Query(
        default="brief",
        alias="format",
        enum=["brief", "detailed", "executive", "bullet"],
        description="Type of summary to generate"
    ),
    current_user: UserContext = Depends(get_current_user_optional),
):
    """Get summary of a document.

    Returns pre-generated summary instantly from Redis if available.
    Falls back to on-demand generation for older documents.
    """
    user_id = current_user.id

    # 1. Check Redis for pre-generated summary
    cached = get_summary(document_id, summary_type)
    if cached:
        return SummaryResponse(
            document_id=document_id,
            summary_type=summary_type,
            summary=cached,
            method="cached",
        )

    # 2. Fall back to on-demand generation (for pre-existing documents)
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

    # Store in Redis for future requests
    store_summary(document_id, summary_type, result["summary"])

    return SummaryResponse(**result)


@router.get("/documents/{document_id}/summary/stream")
async def stream_document_summary(
    request: Request,
    document_id: str,
    summary_type: str = Query(
        default="brief",
        alias="format",
        enum=["brief", "detailed", "executive", "bullet"],
        description="Type of summary to generate"
    ),
    current_user: UserContext = Depends(get_current_user_optional),
):
    """Stream summary via SSE by polling Redis.

    The endpoint never calls Ollama directly. Instead:
    1. If completed summary exists in Redis → send it instantly
    2. If Celery is already generating → poll Redis for new chunks
    3. If nothing is happening → dispatch Celery task, then poll Redis

    This decouples the frontend from the LLM call. Celery owns generation,
    the endpoint just reads from Redis. User can refresh/switch tabs without
    losing progress — Celery keeps running independently.

    SSE Events:
    - status: {"stage": "generating"} — Celery is generating
    - token: partial summary text (new content since last poll)
    - done: generation complete
    - error: something went wrong
    """
    user_id = current_user.id

    async def event_generator():
        try:
            logger.info(f"Summary stream: doc={document_id}, user={user_id}, type={summary_type}")

            # 1. Check completed cache — send instantly
            cached = get_summary(document_id, summary_type)
            if cached:
                logger.info(f"Summary cache hit: doc={document_id}, type={summary_type}")
                yield {"event": "token", "data": cached}
                yield {"event": "done", "data": ""}
                return

            # 2. Check if Celery is already generating, if not dispatch
            status = get_type_status(document_id, summary_type)
            if status != "generating":
                from app.tasks import generate_single_summary_task
                generate_single_summary_task.apply_async(
                    kwargs={
                        "document_id": document_id,
                        "user_id": user_id,
                        "summary_type": summary_type,
                    },
                    queue="summaries",
                )
                logger.info(f"Dispatched Celery task: doc={document_id}, type={summary_type}")

            yield {"event": "status", "data": json.dumps({"stage": "generating"})}

            # 3. Poll Redis for new content from the Celery worker
            offset = 0
            idle_count = 0
            max_idle = 600  # 600 * 0.5s = 5 minutes max wait

            while idle_count < max_idle:
                if await request.is_disconnected():
                    logger.info(f"Client disconnected: doc={document_id}, type={summary_type}")
                    return

                # Check if completed while we were polling
                completed = get_summary(document_id, summary_type)
                if completed:
                    # Send any remaining content the client hasn't seen
                    remaining = completed[offset:]
                    if remaining:
                        yield {"event": "token", "data": remaining}
                    yield {"event": "done", "data": ""}
                    return

                # Check for generation failure
                current_status = get_type_status(document_id, summary_type)
                if current_status == "failed":
                    yield {
                        "event": "error",
                        "data": json.dumps({"message": "Summary generation failed."}),
                    }
                    return

                # Read new content from stream
                new_content = get_stream_content_from(document_id, summary_type, offset)
                if new_content:
                    offset += len(new_content)
                    idle_count = 0
                    yield {"event": "token", "data": new_content}
                else:
                    idle_count += 1

                await asyncio.sleep(0.5)

            # Timed out
            yield {
                "event": "error",
                "data": json.dumps({"message": "Summary generation timed out."}),
            }

        except Exception as e:
            logger.exception(f"Summary streaming error: {e}")
            yield {
                "event": "error",
                "data": json.dumps({"message": "Failed to generate summary."}),
            }

    return EventSourceResponse(
        event_generator(),
        headers={
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-cache",
        },
    )


@router.post("/documents/{document_id}/summary/regenerate")
async def regenerate_summary(
    document_id: str,
    summary_type: str = Query(
        default="brief",
        alias="format",
        enum=["brief", "detailed", "executive", "bullet"],
    ),
    current_user: UserContext = Depends(get_current_user_optional),
):
    """Delete cached summary and trigger regeneration.

    Clears the existing summary from Redis. The frontend then calls
    the stream endpoint which auto-dispatches a new Celery task.
    """
    import redis as redis_lib
    from app.config import settings as app_settings
    from app.services.summary_storage import clear_stream, set_type_status

    r = redis_lib.from_url(app_settings.REDIS_URL, decode_responses=True)
    r.delete(f"summary:{document_id}:{summary_type}")

    set_type_status(document_id, summary_type, "pending")
    clear_stream(document_id, summary_type)

    return {"message": f"Summary '{summary_type}' cleared. Re-request via stream endpoint."}


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


@router.post("/enhanced", response_model=QueryResponseWithCitations)
async def query_documents_enhanced(
    request: QueryRequest,
    current_user: UserContext = Depends(get_current_user_optional),
):
    """Enhanced query with confidence scores, highlighted citations, and memory context.

    Phase 5 enhanced query endpoint providing:
    - Confidence score indicating model certainty (Success Criteria #6)
    - Highlighted citations with exact text passages (Success Criteria #4)
    - User memory facts integrated into context (Success Criteria #3, #5)

    Supports both authenticated and anonymous users.
    The original /query endpoint remains for backward compatibility.

    Args:
        request: QueryRequest with query string and max_results.
        current_user: UserContext (authenticated or anonymous).

    Returns:
        QueryResponseWithCitations with answer, confidence, and highlighted citations.
    """
    user_id = current_user.id

    # Step 1: Retrieve relevant document context (filtered by user_id)
    context = await retrieve_relevant_context(
        query=request.query,
        user_id=user_id,
        max_results=request.max_results,
        include_graph_context=request.include_graph_context,
    )

    # Step 2: Retrieve user memories (if authenticated and not anonymous)
    # User memories influence query responses through personalization
    memory_context = []
    if not current_user.is_anonymous:
        from app.services.memory_service import search_with_shared

        memories = await search_with_shared(
            user_id=user_id,
            query=request.query,
            limit=3,
            include_shared=True,  # Include shared company knowledge
        )
        memory_context = [
            {
                "text": m.get("memory", ""),
                "filename": "Shared Memory" if m.get("is_shared") else "User Memory",
                "score": m.get("score", 0.5),
            }
            for m in memories
            if m.get("memory")  # Only include non-empty memories
        ]

    # Step 3: Combine document + memory context
    all_context = context["chunks"] + memory_context

    # Step 4: Handle no context case
    if not all_context:
        return QueryResponseWithCitations(
            answer="I don't know. I couldn't find any relevant information in your documents.",
            confidence=ConfidenceScore(
                score=0.95,
                level="high",
                interpretation="The model is confident there is no relevant information.",
            ),
            citations=[],
        )

    # Step 5: Generate answer with confidence using logprobs
    result = await generate_answer_with_confidence(
        query=request.query,
        context=all_context,
    )

    # Step 6: Extract highlighted citations with exact passages
    # Only extract citations from document chunks (not memory context)
    citations = await extract_highlighted_citations(
        answer=result["answer"],
        context_chunks=context["chunks"],
        query=request.query,
    )

    # Build confidence score from result
    confidence_data = result["confidence"]
    confidence = ConfidenceScore(
        score=confidence_data["score"],
        level=confidence_data["level"],
        interpretation=confidence_data["interpretation"],
    )

    return QueryResponseWithCitations(
        answer=result["answer"],
        confidence=confidence,
        citations=citations,
    )


@router.get("/graph/entities")
async def get_cross_document_entities(
    current_user: UserContext = Depends(get_current_user_optional),
):
    """Get entities that appear across multiple documents.

    Returns "bridge entities" — concepts, people, organizations, etc.
    that connect different documents in the user's collection.
    Useful for discovering cross-document themes and relationships.

    Returns:
        List of entities with their type, document count, and document IDs.
    """
    from app.services.graphrag_service import get_entity_co_occurrences

    user_id = current_user.id
    co_occurrences = await get_entity_co_occurrences(user_id=user_id, limit=20)

    return {
        "entities": co_occurrences,
        "count": len(co_occurrences),
    }
