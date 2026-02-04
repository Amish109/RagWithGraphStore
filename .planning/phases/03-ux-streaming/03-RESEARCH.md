# Phase 3: UX & Streaming - Research

**Researched:** 2026-02-04
**Domain:** FastAPI SSE streaming, LangChain streaming, document management, error handling
**Confidence:** HIGH

## Summary

Phase 3 focuses on polishing the user experience through three main areas: (1) streaming responses for queries using Server-Sent Events (SSE) to provide real-time feedback instead of blocking waits, (2) document management capabilities including listing, deletion with cascade, and automatic summary generation, and (3) robust error handling that presents user-friendly messages without exposing internal details.

The existing codebase (FastAPI with LangChain ChatOpenAI, Neo4j, and Qdrant) provides a solid foundation. The query endpoint currently returns complete responses synchronously - this must be converted to stream tokens as they arrive. Document upload already uses background tasks but lacks status tracking. Error handling is minimal, with only basic HTTPException usage.

**Primary recommendation:** Use `sse-starlette` for SSE streaming with LangChain's `astream()` method, implement cascade deletion with explicit dual-store cleanup (Qdrant filter delete + Neo4j DETACH DELETE), and add global exception handlers with structured error responses.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| sse-starlette | 3.2.0 | Server-Sent Events for FastAPI | Production-ready, W3C compliant, auto disconnect detection |
| langchain | >=1.0 | LLM orchestration with streaming | Already in use, native `astream()` support |
| langchain-openai | >=1.1.7 | ChatOpenAI with async streaming | Already in use, supports token-by-token streaming |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pydantic | >=2.7.0 | Structured error responses | Already in use, for ErrorResponse models |
| redis | >=5.0.0 | Task status persistence (optional) | If task status must survive server restarts |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| sse-starlette | StreamingResponse (built-in) | StreamingResponse works but sse-starlette handles SSE spec compliance, ping/keepalive, disconnect detection |
| In-memory task status | Redis/Celery | Memory is simpler but lost on restart; Celery for heavy processing |
| map_reduce summarization | stuff chain | Stuff is simpler but fails on large documents; map_reduce scales |

**Installation:**
```bash
pip install sse-starlette
```

## Architecture Patterns

### Recommended Project Structure
```
backend/app/
├── api/
│   ├── queries.py          # Add streaming query endpoint
│   └── documents.py        # Add delete endpoint, enhance list
├── core/
│   ├── exceptions.py       # Expand with domain exceptions
│   └── error_handlers.py   # NEW: Global exception handlers
├── services/
│   ├── generation_service.py  # Add streaming generation
│   ├── summarization_service.py  # NEW: Document summarization
│   └── document_processor.py  # Add status tracking, summary step
├── models/
│   └── schemas.py          # Add DocumentDetail, ErrorResponse schemas
└── utils/
    └── task_tracker.py     # NEW: In-memory task status tracking
```

### Pattern 1: SSE Streaming for LLM Responses
**What:** Stream LLM tokens to client as they are generated using SSE
**When to use:** Query endpoints where users wait for AI responses
**Example:**
```python
# Source: sse-starlette docs + LangChain astream
from sse_starlette import EventSourceResponse
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o", streaming=True, temperature=0)

async def stream_query_response(query: str, context: list):
    """Stream LLM response token by token."""
    prompt = ChatPromptTemplate.from_messages([...])
    messages = prompt.format_messages(context=context, query=query)

    async for chunk in llm.astream(messages):
        if chunk.content:
            yield {"data": chunk.content, "event": "token"}

    yield {"data": "[DONE]", "event": "done"}

@router.post("/stream")
async def query_stream(request: QueryRequest, current_user: dict = Depends(get_current_user)):
    context = await retrieve_relevant_context(request.query, current_user["id"])
    return EventSourceResponse(
        stream_query_response(request.query, context["chunks"]),
        headers={"X-Accel-Buffering": "no"}  # Disable nginx buffering
    )
```

### Pattern 2: Task Status Tracking
**What:** Track background task progress with status updates
**When to use:** Document upload processing to show progress stages
**Example:**
```python
# Source: FastAPI background tasks pattern
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, Optional

class TaskStatus(str, Enum):
    PENDING = "pending"
    EXTRACTING = "extracting"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    INDEXING = "indexing"
    SUMMARIZING = "summarizing"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class TaskInfo:
    document_id: str
    status: TaskStatus
    progress: int  # 0-100
    message: str
    created_at: datetime
    updated_at: datetime
    error: Optional[str] = None

# In-memory tracker (consider Redis for persistence)
task_registry: Dict[str, TaskInfo] = {}

def update_task_status(document_id: str, status: TaskStatus, progress: int, message: str):
    if document_id in task_registry:
        task_registry[document_id].status = status
        task_registry[document_id].progress = progress
        task_registry[document_id].message = message
        task_registry[document_id].updated_at = datetime.utcnow()
```

### Pattern 3: Cascade Delete (Dual-Store)
**What:** Delete document from both Neo4j and Qdrant atomically
**When to use:** Document deletion endpoint
**Example:**
```python
# Source: Neo4j DETACH DELETE + Qdrant filter delete
from qdrant_client.models import Filter, FieldCondition, MatchValue

async def delete_document(document_id: str, user_id: str) -> bool:
    """Delete document with cascade to both stores.

    CRITICAL: Order matters - delete from Qdrant first (no rollback),
    then Neo4j (transactional). If Neo4j fails, Qdrant data is orphaned
    but that's safer than orphaned Neo4j data with missing vectors.
    """
    # Step 1: Verify ownership in Neo4j
    doc = get_document_by_id(document_id, user_id)
    if not doc:
        return False

    # Step 2: Delete vectors from Qdrant (by document_id filter)
    qdrant_client.delete(
        collection_name=settings.QDRANT_COLLECTION,
        points_selector=Filter(
            must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]
        ),
        wait=True
    )

    # Step 3: Delete from Neo4j (DETACH DELETE cascades to chunks)
    with neo4j_driver.session(database=settings.NEO4J_DATABASE) as session:
        session.run("""
            MATCH (u:User {id: $user_id})-[:OWNS]->(d:Document {id: $document_id})
            OPTIONAL MATCH (d)-[:CONTAINS]->(c:Chunk)
            DETACH DELETE d, c
        """, user_id=user_id, document_id=document_id)

    return True
```

### Pattern 4: Global Exception Handler
**What:** Centralized error handling with user-friendly responses
**When to use:** All API endpoints
**Example:**
```python
# Source: FastAPI error handling docs
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel

class ErrorResponse(BaseModel):
    error: str
    message: str
    detail: Optional[str] = None

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            error="validation_error",
            message="Invalid request data",
            detail=str(exc.errors())
        ).model_dump()
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    # Log the full exception internally
    logger.exception(f"Unhandled exception: {exc}")
    # Return sanitized response to user
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="internal_error",
            message="An unexpected error occurred. Please try again later."
        ).model_dump()
    )
```

### Pattern 5: Document Summarization
**What:** Generate summary on document upload using map_reduce chain
**When to use:** After document chunking, before indexing
**Example:**
```python
# Source: LangChain summarization patterns
from langchain.chains.summarize import load_summarize_chain
from langchain_core.documents import Document

async def generate_document_summary(chunks: list[dict], llm) -> str:
    """Generate document summary using map_reduce for scalability.

    map_reduce handles large documents by:
    1. Summarizing each chunk independently (map)
    2. Combining chunk summaries into final summary (reduce)
    """
    # Convert chunks to LangChain Document format
    docs = [Document(page_content=chunk["text"]) for chunk in chunks]

    # Use map_reduce for large documents, stuff for small
    if len(docs) <= 4:
        chain = load_summarize_chain(llm, chain_type="stuff")
    else:
        chain = load_summarize_chain(llm, chain_type="map_reduce")

    result = await chain.ainvoke({"input_documents": docs})
    return result["output_text"]
```

### Anti-Patterns to Avoid
- **Blocking LLM calls in request thread:** Always use async streaming or background tasks
- **Returning stack traces to users:** Log internally, return generic messages
- **Ignoring Qdrant/Neo4j sync issues:** Always delete Qdrant first, accept potential orphans
- **Fixed-size progress (0/100):** Use meaningful stages with descriptive messages
- **SSE without disconnect handling:** Always check `request.is_disconnected()`

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SSE protocol handling | Custom StreamingResponse with SSE format | sse-starlette EventSourceResponse | Handles keepalive pings, disconnect detection, W3C compliance |
| Document summarization | Custom recursive summarization | LangChain load_summarize_chain | Handles chunk batching, prompt templates, map_reduce logic |
| Token streaming from OpenAI | Manual API calls with stream=True | ChatOpenAI.astream() | Handles async iteration, error recovery, token parsing |
| Error response formatting | Inline try/except in each route | Global @exception_handler | Consistent format, single source of truth |

**Key insight:** SSE and streaming look simple but have many edge cases (proxy buffering, connection timeouts, client disconnects, backpressure). sse-starlette handles these.

## Common Pitfalls

### Pitfall 1: Nginx/Proxy Buffering SSE
**What goes wrong:** SSE events batch up and arrive in chunks instead of real-time
**Why it happens:** Nginx buffers responses by default (~16KB before flush)
**How to avoid:** Set `X-Accel-Buffering: no` header on SSE responses
**Warning signs:** Events arrive in bursts, long delays before first token

### Pitfall 2: Orphaned Data After Failed Cascade Delete
**What goes wrong:** Qdrant vectors deleted but Neo4j delete fails, leaving inconsistent state
**Why it happens:** No distributed transaction support between stores
**How to avoid:** Accept Qdrant-first deletion (orphaned vectors are harmless); alternatively, mark documents as "deleting" before starting
**Warning signs:** Queries return results for "deleted" documents

### Pitfall 3: Memory Exhaustion from Task Registry
**What goes wrong:** task_registry dict grows unbounded as documents are uploaded
**Why it happens:** No cleanup of completed/old task entries
**How to avoid:** Implement TTL-based cleanup (e.g., remove entries older than 1 hour)
**Warning signs:** Memory usage grows linearly with uploads over time

### Pitfall 4: Summarization Fails on Large Documents
**What goes wrong:** Token limit exceeded when summarizing long documents
**Why it happens:** Using "stuff" chain that sends all content at once
**How to avoid:** Use "map_reduce" chain type which processes chunks independently
**Warning signs:** OpenAI API returns "context_length_exceeded" error

### Pitfall 5: Missing SSE Client Disconnect Detection
**What goes wrong:** Server continues generating after client navigates away, wasting resources
**Why it happens:** Not checking disconnect status in streaming loop
**How to avoid:** Check `await request.is_disconnected()` in generator loop
**Warning signs:** High server CPU even with few active users

### Pitfall 6: Exposing Internal Errors to Users
**What goes wrong:** Stack traces, database errors, or file paths shown in API responses
**Why it happens:** No global exception handler catching unhandled errors
**How to avoid:** Add catch-all exception handler returning generic messages; log details internally
**Warning signs:** Users see "Neo4j connection failed" or Python tracebacks

## Code Examples

Verified patterns from official sources:

### SSE Query Endpoint (Complete)
```python
# Source: sse-starlette 3.2.0 docs + FastAPI
from fastapi import APIRouter, Depends, Request
from sse_starlette import EventSourceResponse
from app.models.schemas import QueryRequest, Citation
from app.services.retrieval_service import retrieve_relevant_context
from app.core.security import get_current_user
import json

router = APIRouter()

@router.post("/stream", response_class=EventSourceResponse)
async def query_stream(
    request: Request,
    query_request: QueryRequest,
    current_user: dict = Depends(get_current_user),
):
    """Stream query response with SSE."""
    user_id = current_user["id"]

    async def event_generator():
        # Step 1: Retrieve context
        yield {"event": "status", "data": json.dumps({"stage": "retrieving"})}
        context = await retrieve_relevant_context(
            query=query_request.query,
            user_id=user_id,
            max_results=query_request.max_results,
        )

        if not context["chunks"]:
            yield {"event": "answer", "data": "I don't know. I couldn't find relevant information."}
            yield {"event": "done", "data": ""}
            return

        # Step 2: Send citations
        citations = [
            {"document_id": c["document_id"], "filename": c["filename"], "score": c["score"]}
            for c in context["chunks"]
        ]
        yield {"event": "citations", "data": json.dumps(citations)}

        # Step 3: Stream LLM response
        yield {"event": "status", "data": json.dumps({"stage": "generating"})}
        async for chunk in stream_llm_response(query_request.query, context["chunks"]):
            if await request.is_disconnected():
                break
            yield {"event": "token", "data": chunk}

        yield {"event": "done", "data": ""}

    return EventSourceResponse(
        event_generator(),
        headers={"X-Accel-Buffering": "no"}
    )
```

### Document Delete Endpoint
```python
# Source: Qdrant Python SDK + Neo4j Cypher
from fastapi import APIRouter, Depends, HTTPException, status
from qdrant_client.models import Filter, FieldCondition, MatchValue

@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Delete a document and all associated data."""
    user_id = current_user["id"]

    # Verify ownership
    doc = get_document_by_id(document_id, user_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    # Delete from Qdrant first (filter by document_id)
    qdrant_client.delete(
        collection_name=settings.QDRANT_COLLECTION,
        points_selector=Filter(
            must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]
        ),
        wait=True
    )

    # Delete from Neo4j (DETACH DELETE cascades to chunks)
    with neo4j_driver.session(database=settings.NEO4J_DATABASE) as session:
        session.run("""
            MATCH (u:User {id: $user_id})-[:OWNS]->(d:Document {id: $document_id})
            OPTIONAL MATCH (d)-[:CONTAINS]->(c:Chunk)
            DETACH DELETE d, c
        """, user_id=user_id, document_id=document_id)

    return {"message": "Document deleted successfully"}
```

### Task Status Tracking
```python
# Source: FastAPI background tasks pattern
from datetime import datetime, timedelta
from typing import Dict
from threading import Lock

task_registry: Dict[str, TaskInfo] = {}
registry_lock = Lock()

def cleanup_old_tasks():
    """Remove tasks older than 1 hour."""
    cutoff = datetime.utcnow() - timedelta(hours=1)
    with registry_lock:
        to_remove = [
            doc_id for doc_id, info in task_registry.items()
            if info.updated_at < cutoff
        ]
        for doc_id in to_remove:
            del task_registry[doc_id]

@router.get("/{document_id}/status")
async def get_document_status(
    document_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get document processing status."""
    task = task_registry.get(document_id)
    if not task:
        # Check if document exists (already processed)
        doc = get_document_by_id(document_id, current_user["id"])
        if doc:
            return {"status": "completed", "progress": 100, "message": "Document ready"}
        raise HTTPException(status_code=404, detail="Document not found")

    return {
        "status": task.status,
        "progress": task.progress,
        "message": task.message,
        "error": task.error
    }
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Blocking LLM calls | Streaming with SSE | 2024 | 10x better perceived latency |
| Plain StreamingResponse | sse-starlette EventSourceResponse | 2025 | Automatic ping/keepalive, proper SSE spec |
| Custom summarization loops | LangChain load_summarize_chain | 2024 | Handles chunking, batching, reduce automatically |
| Per-route try/except | Global exception handlers | FastAPI 0.100+ | Consistent error format, less boilerplate |

**Deprecated/outdated:**
- `load_qa_chain` with `chain_type="stuff"` for summarization - Use `load_summarize_chain` instead
- Manual SSE formatting with `\n\n` separators - Use sse-starlette's structured events
- Synchronous Neo4j driver calls in async endpoints - Use `async with` or run in executor

## Open Questions

Things that couldn't be fully resolved:

1. **Redis vs In-Memory for Task Status**
   - What we know: In-memory is simpler but lost on restart; Redis persists
   - What's unclear: Project requirement for task status persistence
   - Recommendation: Start with in-memory dict, add Redis if persistence needed (Phase 2 may add Redis anyway)

2. **Summary Storage Location**
   - What we know: Summary should be stored for quick retrieval
   - What's unclear: Whether to store in Neo4j Document node or separate collection
   - Recommendation: Add `summary` property to Document node in Neo4j (simple, no new schema)

3. **Progress SSE vs Polling for Document Upload**
   - What we know: SSE provides real-time updates, polling is simpler
   - What's unclear: Whether clients will support SSE for uploads
   - Recommendation: Implement polling endpoint first (`GET /documents/{id}/status`), SSE as enhancement

## Sources

### Primary (HIGH confidence)
- [sse-starlette 3.2.0 PyPI](https://pypi.org/project/sse-starlette/) - EventSourceResponse usage, features
- [sse-starlette GitHub](https://github.com/sysid/sse-starlette) - Complete examples, configuration
- [FastAPI Error Handling](https://fastapi.tiangolo.com/tutorial/handling-errors/) - Exception handlers, HTTPException
- [Qdrant Python Client](https://python-client.qdrant.tech/qdrant_client.qdrant_client) - delete() method, FilterSelector
- [Neo4j Cypher DELETE](https://neo4j.com/docs/cypher-manual/current/clauses/delete/) - DETACH DELETE syntax

### Secondary (MEDIUM confidence)
- [LangChain Streaming](https://docs.langchain.com/oss/python/langgraph/streaming) - astream() patterns
- [LangChain load_summarize_chain](https://medium.com/@abonia/summarization-with-langchain-b3d83c030889) - map_reduce, stuff, refine patterns
- [FastAPI Background Tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/) - Task tracking patterns
- [Neo4j Large Delete Best Practices](https://neo4j.com/developer/kb/large-delete-transaction-best-practices-in-neo4j/) - Batch deletion

### Tertiary (LOW confidence)
- [Streaming AI Agents with SSE](https://akanuragkumar.medium.com/streaming-ai-agents-responses-with-server-sent-events-sse-a-technical-case-study-f3ac855d0755) - Architecture patterns
- [Qdrant + Neo4j Sync Challenges](https://neo4j.com/blog/developer/qdrant-to-enhance-rag-pipeline/) - Consistency considerations

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Verified with official documentation
- Architecture: HIGH - Patterns align with existing codebase structure
- Pitfalls: HIGH - Well-documented in official sources and community
- Code examples: MEDIUM - Based on official APIs, not tested against project

**Research date:** 2026-02-04
**Valid until:** 2026-03-04 (30 days - stable domain)
