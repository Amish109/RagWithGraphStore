# Phase 5: Differentiation Features - Research

**Researched:** 2026-02-04
**Domain:** Document summarization, text simplification, confidence scoring, highlighted citations, memory augmentation
**Confidence:** HIGH

## Summary

Phase 5 delivers competitive differentiation through on-demand document summaries, simplified explanations, highlighted citations, and confidence scores. This phase builds on top of the memory infrastructure from Phase 2 and the document processing pipeline from Phase 1. The research identified that LangChain provides mature summarization patterns (stuff, map-reduce, refine chains), OpenAI's logprobs API enables confidence scoring, and citation highlighting requires preserving chunk-to-source mappings at index time.

The key insight is that most Phase 5 features are LLM prompt engineering problems rather than infrastructure challenges. Document summaries use the same retrieval pipeline but with summarization-focused prompts. Simplified explanations use a two-stage prompt: first explain simply, then verify reading level. Confidence scores leverage OpenAI logprobs to compute joint token probabilities. Highlighted citations require enhancing the existing Citation model with exact text passages and position data.

**Primary recommendation:** Implement features incrementally: (1) On-demand summarization with caching, (2) Text simplification with progressive prompting, (3) Confidence scores via logprobs, (4) Enhanced citations with highlighted passages. For memory endpoints, extend Phase 2 memory service with admin-only shared memory write operations and integrate memory context into query responses.

## Standard Stack

The established libraries/tools for Phase 5:

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| langchain | >=0.2.0 | Summarization chains, prompt templates | Mature summarization patterns (stuff, map-reduce, refine). Already in codebase from Phase 1. |
| langchain-openai | >=0.2.0 | OpenAI with logprobs support | Native logprobs parameter for confidence scoring. |
| redis | >=5.0.0 | Summary caching | LRU cache for expensive summarization results. Already planned in Phase 2. |
| async_lru | >=2.0.0 | In-memory async LRU | Lightweight cache for frequently accessed summaries before Redis fallback. |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| numpy | latest | Logprob math | Converting logprobs to confidence scores (np.exp). |
| pydantic | >=2.0 | Response models | Enhanced Citation schema with position/highlight data. |
| hashlib | stdlib | Cache key generation | SHA-256 hash of document_id + summary_type for cache keys. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| OpenAI logprobs | Self-consistency voting | Multiple LLM calls vs. single call with logprobs. Logprobs cheaper. |
| LangChain summarization | Custom chain | LangChain has tested patterns, handles edge cases. |
| Redis summary cache | In-memory only | Redis persists across restarts, supports distributed deployments. |
| Two-stage simplification | Single prompt | Two-stage more reliable for reading level control. |

**Installation:**
```bash
# Most already installed from Phase 1/2
pip install "async_lru>=2.0.0"
pip install numpy  # If not already present

# Verify existing
pip show langchain langchain-openai redis
```

## Architecture Patterns

### Recommended Additional Structure (Phase 5)
```
backend/app/
├── services/
│   ├── summarization_service.py  # NEW: Document summarization with caching
│   ├── simplification_service.py # NEW: Text simplification service
│   ├── confidence_service.py     # NEW: Confidence score calculation
│   ├── generation_service.py     # EXTEND: Add logprobs support
│   ├── retrieval_service.py      # EXTEND: Enhanced citations
│   └── memory_service.py         # EXTEND: Shared memory operations (from Phase 2)
├── api/
│   ├── queries.py                # EXTEND: Summarize, simplify endpoints
│   └── memory.py                 # EXTEND: Admin shared memory endpoints (from Phase 2)
├── models/
│   └── schemas.py                # EXTEND: Enhanced Citation, SummaryResponse, ConfidenceScore
└── core/
    └── cache.py                  # NEW: Summary caching utilities
```

### Pattern 1: On-Demand Document Summarization

**What:** Generate summaries for documents already stored in the system without re-uploading.

**When to use:** QRY-06 (User can request document summaries).

**Example:**
```python
# app/services/summarization_service.py
from typing import Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from app.config import settings
from app.db.neo4j_client import neo4j_driver
from app.db.qdrant_client import get_document_chunks
from functools import lru_cache
import hashlib

# Summary types with different prompts
SUMMARY_PROMPTS = {
    "brief": "Summarize this document in 2-3 sentences. Focus on the main point.",
    "detailed": "Provide a comprehensive summary covering all key points, organized by topic.",
    "executive": "Create an executive summary suitable for busy stakeholders. Include key findings, recommendations, and action items.",
    "bullet": "Summarize the document as a bulleted list of key points."
}

def _cache_key(document_id: str, summary_type: str) -> str:
    """Generate cache key for summary."""
    return hashlib.sha256(f"{document_id}:{summary_type}".encode()).hexdigest()

async def get_document_text(document_id: str, user_id: str) -> Optional[str]:
    """Retrieve full document text from chunks.

    CRITICAL: Filter by user_id for multi-tenant isolation.
    """
    with neo4j_driver.session(database=settings.NEO4J_DATABASE) as session:
        result = session.run("""
            MATCH (d:Document {id: $doc_id, user_id: $user_id})-[:CONTAINS]->(c:Chunk)
            RETURN c.text AS text, c.position AS position
            ORDER BY c.position
        """, doc_id=document_id, user_id=user_id)

        chunks = list(result)
        if not chunks:
            return None

        return "\n\n".join(record["text"] for record in chunks)

async def summarize_document(
    document_id: str,
    user_id: str,
    summary_type: str = "brief",
    max_chunks: int = 50,
    use_cache: bool = True,
    redis_client = None
) -> Optional[dict]:
    """Generate summary for a document.

    Uses map-reduce pattern for long documents:
    1. Summarize each chunk individually (map)
    2. Combine chunk summaries into final summary (reduce)

    Caches results in Redis for performance.
    """
    cache_key = _cache_key(document_id, summary_type)

    # Check cache first
    if use_cache and redis_client:
        cached = await redis_client.get(f"summary:{cache_key}")
        if cached:
            import json
            return json.loads(cached)

    # Get document text
    document_text = await get_document_text(document_id, user_id)
    if not document_text:
        return None

    # Get summary prompt
    summary_prompt = SUMMARY_PROMPTS.get(summary_type, SUMMARY_PROMPTS["brief"])

    llm = ChatOpenAI(
        model=settings.OPENAI_MODEL,
        temperature=0.3,  # Slight creativity for summaries
        openai_api_key=settings.OPENAI_API_KEY,
    )

    # For short documents, use "stuff" method
    if len(document_text) < 10000:
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a document summarization expert. Create clear, accurate summaries."),
            ("user", "{instruction}\n\nDocument:\n{document}")
        ])

        messages = prompt.format_messages(
            instruction=summary_prompt,
            document=document_text
        )
        response = await llm.ainvoke(messages)

        result = {
            "document_id": document_id,
            "summary_type": summary_type,
            "summary": response.content,
            "method": "stuff"
        }
    else:
        # For long documents, use map-reduce
        # Split into chunks and summarize each
        chunk_size = 4000
        chunks = [document_text[i:i+chunk_size] for i in range(0, len(document_text), chunk_size)]

        # Map: Summarize each chunk
        map_prompt = ChatPromptTemplate.from_messages([
            ("system", "Summarize this text section concisely, preserving key information."),
            ("user", "{text}")
        ])

        chunk_summaries = []
        for chunk in chunks[:max_chunks]:
            messages = map_prompt.format_messages(text=chunk)
            response = await llm.ainvoke(messages)
            chunk_summaries.append(response.content)

        # Reduce: Combine chunk summaries
        combined = "\n\n".join(chunk_summaries)
        reduce_prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a document summarization expert. Create clear, accurate summaries."),
            ("user", "{instruction}\n\nSection summaries:\n{summaries}")
        ])

        messages = reduce_prompt.format_messages(
            instruction=summary_prompt,
            summaries=combined
        )
        response = await llm.ainvoke(messages)

        result = {
            "document_id": document_id,
            "summary_type": summary_type,
            "summary": response.content,
            "method": "map_reduce",
            "chunks_processed": len(chunks[:max_chunks])
        }

    # Cache result (1 hour TTL)
    if use_cache and redis_client:
        import json
        await redis_client.setex(
            f"summary:{cache_key}",
            3600,  # 1 hour
            json.dumps(result)
        )

    return result
```

**Critical:**
1. Always filter by user_id when retrieving document chunks.
2. Use map-reduce for long documents to avoid token limits.
3. Cache summaries - they're expensive to generate.
4. Different summary types serve different user needs.

### Pattern 2: Text Simplification with Progressive Prompting

**What:** Generate simplified explanations of complex document content.

**When to use:** QRY-07 (User can request simplified explanations).

**Example:**
```python
# app/services/simplification_service.py
from typing import Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from app.config import settings

# Simplification levels with target audiences
SIMPLIFICATION_LEVELS = {
    "eli5": {
        "description": "Explain like I'm 5 years old",
        "prompt": "Explain this in very simple terms that a child could understand. Use everyday analogies and avoid technical words.",
        "reading_level": "elementary"
    },
    "general": {
        "description": "General audience explanation",
        "prompt": "Explain this for someone with no background in this field. Use simple language and define any technical terms.",
        "reading_level": "8th grade"
    },
    "professional": {
        "description": "Professional but accessible",
        "prompt": "Explain this for a professional in a different field. Be clear but don't oversimplify technical concepts.",
        "reading_level": "college"
    }
}

async def simplify_text(
    text: str,
    level: str = "general",
    context: Optional[str] = None
) -> dict:
    """Simplify complex text to specified reading level.

    Uses two-stage prompting:
    1. Generate simplified explanation
    2. Verify/adjust reading level
    """
    level_config = SIMPLIFICATION_LEVELS.get(level, SIMPLIFICATION_LEVELS["general"])

    llm = ChatOpenAI(
        model=settings.OPENAI_MODEL,
        temperature=0.4,  # Slight creativity for explanations
        openai_api_key=settings.OPENAI_API_KEY,
    )

    # Stage 1: Initial simplification
    if context:
        prompt = ChatPromptTemplate.from_messages([
            ("system", f"""You are an expert at explaining complex topics simply.
Target audience: {level_config['description']}.
Reading level: {level_config['reading_level']}.

{level_config['prompt']}"""),
            ("user", """Context from the document:
{context}

Complex text to simplify:
{text}

Simplified explanation:""")
        ])
        messages = prompt.format_messages(context=context, text=text)
    else:
        prompt = ChatPromptTemplate.from_messages([
            ("system", f"""You are an expert at explaining complex topics simply.
Target audience: {level_config['description']}.
Reading level: {level_config['reading_level']}.

{level_config['prompt']}"""),
            ("user", """Complex text to simplify:
{text}

Simplified explanation:""")
        ])
        messages = prompt.format_messages(text=text)

    response = await llm.ainvoke(messages)
    simplified = response.content

    # Stage 2: Verify and adjust reading level
    verify_prompt = ChatPromptTemplate.from_messages([
        ("system", f"""You are a reading level expert. Review this explanation and ensure it matches the target reading level: {level_config['reading_level']}.

If it's too complex, simplify further. If it's good, return it unchanged.
Only output the final explanation, no commentary."""),
        ("user", "{explanation}")
    ])

    messages = verify_prompt.format_messages(explanation=simplified)
    response = await llm.ainvoke(messages)

    return {
        "original_text": text[:500] + "..." if len(text) > 500 else text,
        "simplified_text": response.content,
        "level": level,
        "level_description": level_config["description"]
    }

async def simplify_document_section(
    document_id: str,
    user_id: str,
    section_text: str,
    level: str = "general"
) -> dict:
    """Simplify a specific section of a document with surrounding context.

    Retrieves nearby chunks for context to improve simplification accuracy.
    """
    from app.services.retrieval_service import retrieve_relevant_context

    # Get context from document
    context_result = await retrieve_relevant_context(
        query=section_text[:500],  # Use first 500 chars as query
        user_id=user_id,
        max_results=2
    )

    context = "\n".join([
        chunk["text"] for chunk in context_result.get("chunks", [])
    ]) if context_result.get("chunks") else None

    return await simplify_text(
        text=section_text,
        level=level,
        context=context
    )
```

**Critical:**
1. Two-stage prompting ensures consistent reading level.
2. Context improves simplification accuracy.
3. Different levels serve different user needs (eli5 for beginners, professional for experts in other fields).

### Pattern 3: Confidence Scores via OpenAI Logprobs

**What:** Calculate confidence scores for LLM responses to help users know when to verify answers.

**When to use:** Success criteria #6 (System provides confidence scores).

**Example:**
```python
# app/services/confidence_service.py
from typing import List, Dict, Optional
import numpy as np
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from app.config import settings

def calculate_confidence_from_logprobs(logprobs: List[Dict]) -> dict:
    """Calculate confidence score from OpenAI logprobs.

    Methods:
    1. Average token probability
    2. Joint probability (product of all token probs)
    3. Weighted score (emphasizes important tokens)

    Returns confidence metrics and interpretation.
    """
    if not logprobs:
        return {"score": 0.5, "level": "unknown", "interpretation": "No logprob data available"}

    # Extract log probabilities
    log_probs = [lp["logprob"] for lp in logprobs if lp.get("logprob") is not None]

    if not log_probs:
        return {"score": 0.5, "level": "unknown", "interpretation": "No logprob data available"}

    # Convert to linear probabilities
    probabilities = np.exp(log_probs)

    # Method 1: Average probability
    avg_prob = float(np.mean(probabilities))

    # Method 2: Joint probability (can get very small)
    joint_prob = float(np.prod(probabilities))

    # Method 3: Geometric mean (better for comparing sequences)
    geometric_mean = float(np.exp(np.mean(log_probs)))

    # Perplexity (lower = more confident)
    perplexity = float(np.exp(-np.mean(log_probs)))

    # Final confidence score (0-1, using geometric mean)
    confidence_score = min(geometric_mean, 1.0)

    # Interpretation thresholds
    if confidence_score >= 0.85:
        level = "high"
        interpretation = "The model is highly confident in this response."
    elif confidence_score >= 0.60:
        level = "medium"
        interpretation = "The model is moderately confident. Consider verifying key claims."
    else:
        level = "low"
        interpretation = "The model has low confidence. Please verify this response with authoritative sources."

    return {
        "score": round(confidence_score, 3),
        "level": level,
        "interpretation": interpretation,
        "metrics": {
            "average_probability": round(avg_prob, 3),
            "geometric_mean": round(geometric_mean, 3),
            "perplexity": round(perplexity, 2),
            "tokens_analyzed": len(log_probs)
        }
    }

async def generate_answer_with_confidence(
    query: str,
    context: List[Dict]
) -> dict:
    """Generate answer with confidence score using logprobs.

    CRITICAL: Must use ChatOpenAI with logprobs=True.
    """
    # Assemble context
    context_text = "\n\n".join([
        f"[Document: {chunk.get('filename', 'Unknown')}]\n{chunk['text']}"
        for chunk in context
    ])

    # Create LLM with logprobs enabled
    llm = ChatOpenAI(
        model=settings.OPENAI_MODEL,
        temperature=0,
        openai_api_key=settings.OPENAI_API_KEY,
        logprobs=True,  # Enable log probabilities
        # top_logprobs=5,  # Get alternatives (optional, for analysis)
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a helpful document Q&A assistant. Answer questions ONLY based on the provided context.

CRITICAL INSTRUCTIONS:
- If the context does not contain information to answer the question, respond EXACTLY with: "I don't know. I couldn't find information about this in the provided documents."
- Do not use any knowledge outside the provided context
- Cite the document name when referencing information
- Be concise and direct"""),
        ("user", """Context:
{context}

Question: {query}

Answer:""")
    ])

    messages = prompt.format_messages(context=context_text, query=query)
    response = await llm.ainvoke(messages)

    # Extract logprobs from response
    logprobs_data = []
    if hasattr(response, 'response_metadata') and response.response_metadata:
        logprobs_content = response.response_metadata.get('logprobs', {}).get('content', [])
        logprobs_data = [
            {"token": item.get("token"), "logprob": item.get("logprob")}
            for item in logprobs_content
            if item.get("logprob") is not None
        ]

    # Calculate confidence
    confidence = calculate_confidence_from_logprobs(logprobs_data)

    return {
        "answer": response.content,
        "confidence": confidence
    }
```

**Critical:**
1. Enable `logprobs=True` in ChatOpenAI initialization.
2. Access logprobs via `response.response_metadata['logprobs']['content']`.
3. Use geometric mean for sequence-level confidence (more stable than joint probability).
4. Provide clear interpretation thresholds for user guidance.

### Pattern 4: Highlighted Citations with Exact Text Passages

**What:** Enhance citations to show exact text passages that support the answer.

**When to use:** Success criteria #4 (Responses include highlighted citations).

**Example:**
```python
# app/services/retrieval_service.py (extend)
# app/models/schemas.py (extend)

# Enhanced Citation schema
from pydantic import BaseModel
from typing import List, Optional

class HighlightedCitation(BaseModel):
    """Enhanced citation with exact text passage highlighting."""
    document_id: str
    filename: str
    page_number: Optional[int] = None  # If available from PDF parsing

    # Full chunk text for context
    chunk_text: str

    # Highlighted passage (the specific part that supports the claim)
    highlighted_passage: str
    highlight_start: int  # Character offset in chunk_text
    highlight_end: int    # Character offset in chunk_text

    relevance_score: float

    # For UI rendering
    chunk_position: int  # Position in document

class QueryResponseWithCitations(BaseModel):
    """Query response with highlighted citations and confidence."""
    answer: str
    confidence: dict
    citations: List[HighlightedCitation]

# Citation extraction service
async def extract_highlighted_citations(
    answer: str,
    context_chunks: List[Dict],
    query: str
) -> List[HighlightedCitation]:
    """Extract highlighted citations by identifying which parts of chunks support the answer.

    Uses LLM to identify the most relevant passages within each chunk.
    """
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import ChatPromptTemplate
    import json

    llm = ChatOpenAI(
        model=settings.OPENAI_MODEL,
        temperature=0,
        openai_api_key=settings.OPENAI_API_KEY,
    )

    citations = []

    for chunk in context_chunks:
        # Ask LLM to identify the most relevant passage
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a citation extraction expert. Given an answer and a source chunk,
identify the exact passage in the chunk that best supports the answer.

Return JSON with:
- highlighted_passage: The exact text from the chunk that supports the answer (copy verbatim)
- relevance_explanation: Brief explanation of why this passage is relevant

Only return the JSON, no other text."""),
            ("user", """Answer being cited: {answer}

Source chunk:
{chunk_text}

Identify the most relevant passage:""")
        ])

        messages = prompt.format_messages(
            answer=answer,
            chunk_text=chunk["text"]
        )

        try:
            response = await llm.ainvoke(messages)
            # Parse JSON response
            result = json.loads(response.content)
            highlighted = result.get("highlighted_passage", "")

            # Find position in original text
            start = chunk["text"].find(highlighted)
            end = start + len(highlighted) if start >= 0 else len(chunk["text"])

            if start < 0:
                # Fallback: use first 200 chars
                highlighted = chunk["text"][:200]
                start = 0
                end = min(200, len(chunk["text"]))

            citations.append(HighlightedCitation(
                document_id=chunk.get("document_id", ""),
                filename=chunk.get("filename", "Unknown"),
                page_number=chunk.get("page_number"),
                chunk_text=chunk["text"],
                highlighted_passage=highlighted,
                highlight_start=start,
                highlight_end=end,
                relevance_score=chunk.get("score", 0.0),
                chunk_position=chunk.get("position", 0)
            ))
        except Exception:
            # Fallback: use chunk text as-is
            citations.append(HighlightedCitation(
                document_id=chunk.get("document_id", ""),
                filename=chunk.get("filename", "Unknown"),
                page_number=chunk.get("page_number"),
                chunk_text=chunk["text"],
                highlighted_passage=chunk["text"][:200] + "..." if len(chunk["text"]) > 200 else chunk["text"],
                highlight_start=0,
                highlight_end=min(200, len(chunk["text"])),
                relevance_score=chunk.get("score", 0.0),
                chunk_position=chunk.get("position", 0)
            ))

    return citations
```

**Critical:**
1. Highlighted passages must be verbatim from source text.
2. Character offsets enable UI highlighting.
3. Fallback to chunk truncation if exact match fails.
4. Include chunk context for user to see surrounding text.

### Pattern 5: Memory API Endpoints (Extend from Phase 2)

**What:** Extend memory endpoints for shared memory management and integration with query responses.

**When to use:** API-05 (POST /memory), API-06 (GET /memory), Success criteria #3, #5.

**Example:**
```python
# app/api/memory.py (extend from Phase 2 plan)
from fastapi import APIRouter, Depends, HTTPException, status
from app.core.security import get_current_user
from app.core.rbac import require_admin, Role
from app.services.memory_service import (
    add_user_memory, search_user_memories, get_user_memories,
    add_shared_memory, search_shared_memories
)
from app.models.schemas import MemoryAddRequest, MemoryListResponse
from app.config import settings

router = APIRouter(prefix="/memory", tags=["memory"])

@router.post("/", response_model=dict)
async def add_memory(
    request: MemoryAddRequest,
    current_user: dict = Depends(get_current_user)
):
    """Add fact to user's private memory (API-05, MEM-04).

    Facts influence future query responses by providing user context.
    """
    if current_user.get("is_anonymous"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Anonymous users cannot add memories. Please register."
        )

    result = await add_user_memory(
        user_id=current_user["id"],
        content=request.content,
        metadata={
            **(request.metadata or {}),
            "type": "fact"  # Mark as user-provided fact
        }
    )

    return {
        "status": "added",
        "memory_id": result.get("id"),
        "scope": "private"
    }

@router.post("/shared", response_model=dict)
async def add_shared_memory_endpoint(
    request: MemoryAddRequest,
    current_user: dict = Depends(require_admin)  # Admin only
):
    """Add fact to shared company memory (API-05, MEM-05).

    ADMIN ONLY. All authenticated users can query against shared memory.
    """
    result = await add_shared_memory(
        content=request.content,
        admin_id=current_user["id"],
        metadata=request.metadata
    )

    return {
        "status": "added",
        "memory_id": result.get("id"),
        "scope": "shared",
        "added_by": current_user["email"]
    }

@router.get("/", response_model=MemoryListResponse)
async def list_memories(
    include_shared: bool = True,
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
):
    """List user's memories and optionally shared memories (API-06)."""
    if current_user.get("is_anonymous"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Anonymous users cannot list memories. Please register."
        )

    # Get user's private memories
    private_memories = await get_user_memories(
        user_id=current_user["id"],
        limit=limit
    )

    # Optionally get shared memories
    shared_memories = []
    if include_shared:
        shared_memories = await get_user_memories(
            user_id=settings.SHARED_MEMORY_USER_ID,
            limit=20
        )
        for mem in shared_memories:
            mem["is_shared"] = True

    all_memories = private_memories + shared_memories

    return MemoryListResponse(
        memories=[
            {
                "id": m.get("id", ""),
                "memory": m.get("memory", ""),
                "metadata": m.get("metadata"),
                "is_shared": m.get("is_shared", False)
            }
            for m in all_memories
        ],
        count=len(all_memories)
    )
```

**Critical:**
1. Admin role required for writing to shared memory.
2. All authenticated users can read shared memory.
3. Mark shared vs. private memories clearly in responses.
4. Anonymous users cannot use memory endpoints.

### Anti-Patterns to Avoid

- **Regenerating summaries on every request:** Summaries are expensive. Always cache with TTL.
- **Single simplification pass:** Two-stage (simplify + verify level) produces more consistent results.
- **Trusting raw logprob scores:** Convert and normalize. Raw logprobs are log-scale.
- **Fabricating highlighted passages:** Always extract verbatim text from source. Never paraphrase.
- **Allowing non-admins to write shared memory:** Shared memory corrupts easily without access control.
- **Ignoring confidence on "I don't know" responses:** Confidence should be high for "I don't know" (model is confident it doesn't know).

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Long document summarization | Single prompt | LangChain map-reduce | Handles token limits, tested patterns |
| Confidence calculation | Simple average | Geometric mean + perplexity | Mathematically sound, handles edge cases |
| Reading level assessment | Flesch-Kincaid formula | LLM verification prompt | LLM understands context better than formulas |
| Summary caching | File-based cache | Redis with TTL | Persistent, shared across instances, auto-expiry |
| Citation highlighting | Regex matching | LLM extraction | Handles paraphrasing, semantic matching |
| Admin role checking | If/else in routes | FastAPI Depends + RoleChecker | Reusable, testable, declarative |

**Key insight:** Phase 5 features are primarily prompt engineering challenges. The infrastructure (vector store, graph store, auth, memory) exists from Phases 1-2. Focus on well-designed prompts and proper caching.

## Common Pitfalls

### Pitfall 1: Summary Regeneration Storm (HIGH)

**What goes wrong:** Every summary request triggers LLM calls, causing high latency and cost. User retries compound the problem.

**Why it happens:** No caching strategy for expensive summarization.

**How to avoid:**
- Redis cache with 1-hour TTL for summaries
- Cache key: hash(document_id + summary_type)
- Background job for popular document pre-summarization
- Rate limit summarization requests per user

**Warning signs:**
- High OpenAI API costs
- Slow /summarize endpoint (>5s)
- Repeated identical requests in logs

### Pitfall 2: Confidence Score Misinterpretation (MEDIUM)

**What goes wrong:** Users see "0.85 confidence" and assume it's 85% accurate. Confidence measures model certainty, not factual accuracy.

**Why it happens:** Confidence score presentation lacks context.

**How to avoid:**
- Always show interpretation text with score
- Use level names (high/medium/low) not just numbers
- Clarify: "Confidence reflects model certainty, not accuracy"
- For "I don't know" responses, explain high confidence is good

**Warning signs:**
- Users reporting "high confidence but wrong answers"
- Confusion in user feedback about confidence meaning

### Pitfall 3: Citation Hallucination (HIGH)

**What goes wrong:** LLM generates "highlighted passage" that doesn't exist in source text.

**Why it happens:** LLM paraphrases instead of quoting verbatim.

**How to avoid:**
- Verify highlighted_passage exists in chunk_text (string search)
- Fallback to truncated chunk if exact match fails
- Explicit prompt: "Copy the exact text verbatim"
- Log and monitor citation match failures

**Warning signs:**
- highlight_start = -1 in responses
- User reports citation doesn't match source
- Long highlighted passages (>500 chars) often fabricated

### Pitfall 4: Simplification Level Drift (LOW)

**What goes wrong:** "ELI5" explanation uses graduate-level vocabulary. Reading levels inconsistent.

**Why it happens:** Single-pass simplification without verification.

**How to avoid:**
- Two-stage prompting: simplify then verify level
- Include reading level in system prompt
- Test with readability metrics (optional validation)
- User feedback on simplification quality

**Warning signs:**
- User complaints about "still too complex"
- Inconsistent vocabulary levels in responses

### Pitfall 5: Shared Memory Pollution (MEDIUM)

**What goes wrong:** Incorrect facts added to shared memory affect all users' query responses.

**Why it happens:** No verification, audit, or approval workflow for shared memory.

**How to avoid:**
- Admin-only write access (RBAC)
- Audit log for all shared memory changes
- Optional: approval workflow for shared facts
- Easy delete/edit for admins

**Warning signs:**
- Wrong answers traced to shared memory facts
- No way to know who added what
- Facts conflict with each other

## Code Examples

Verified patterns from official sources:

### API Endpoint for Document Summary

```python
# app/api/queries.py (extend)
from fastapi import APIRouter, Depends, HTTPException, Query
from app.core.security import get_current_user
from app.services.summarization_service import summarize_document
from app.db.redis_client import get_redis
import redis.asyncio as redis

router = APIRouter()

@router.get("/documents/{document_id}/summary")
async def get_document_summary(
    document_id: str,
    summary_type: str = Query(default="brief", enum=["brief", "detailed", "executive", "bullet"]),
    current_user: dict = Depends(get_current_user),
    redis_client: redis.Redis = Depends(get_redis)
):
    """Get summary of a document (QRY-06).

    Summary types:
    - brief: 2-3 sentence overview
    - detailed: Comprehensive coverage of all key points
    - executive: Business-focused with recommendations
    - bullet: Key points as bulleted list

    Summaries are cached for 1 hour.
    """
    result = await summarize_document(
        document_id=document_id,
        user_id=current_user["id"],
        summary_type=summary_type,
        redis_client=redis_client
    )

    if not result:
        raise HTTPException(
            status_code=404,
            detail="Document not found or you don't have access"
        )

    return result
```

### API Endpoint for Text Simplification

```python
# app/api/queries.py (extend)
from app.services.simplification_service import simplify_document_section

@router.post("/simplify")
async def simplify_content(
    request: SimplifyRequest,
    current_user: dict = Depends(get_current_user)
):
    """Simplify complex text (QRY-07).

    Levels:
    - eli5: Child-friendly explanation
    - general: General audience (default)
    - professional: Professionals from other fields
    """
    result = await simplify_document_section(
        document_id=request.document_id,
        user_id=current_user["id"],
        section_text=request.text,
        level=request.level
    )

    return result
```

### Enhanced Query Endpoint with All Phase 5 Features

```python
# app/api/queries.py (extend)
from app.services.confidence_service import generate_answer_with_confidence
from app.services.retrieval_service import extract_highlighted_citations
from app.services.memory_service import search_user_memories

@router.post("/query", response_model=QueryResponseWithCitations)
async def query_documents_enhanced(
    request: QueryRequest,
    current_user: dict = Depends(get_current_user)
):
    """Enhanced query with confidence scores, highlighted citations, and memory context.

    Phase 5 enhancements:
    - Confidence score on response
    - Highlighted citations showing exact passages
    - User memory facts integrated into context
    """
    user_id = current_user["id"]

    # Step 1: Retrieve relevant document context
    context = await retrieve_relevant_context(
        query=request.query,
        user_id=user_id,
        max_results=request.max_results
    )

    # Step 2: Retrieve relevant user memories (if authenticated)
    memory_context = []
    if not current_user.get("is_anonymous"):
        memories = await search_user_memories(
            user_id=user_id,
            query=request.query,
            limit=3,
            include_shared=True  # Include shared company knowledge
        )
        memory_context = [
            {"text": m.get("memory", ""), "filename": "User Memory", "score": m.get("score", 0.5)}
            for m in memories
        ]

    # Step 3: Combine document context with memory context
    all_context = context["chunks"] + memory_context

    # Step 4: Generate answer with confidence
    if not all_context:
        return QueryResponseWithCitations(
            answer="I don't know. I couldn't find any relevant information in your documents.",
            confidence={"score": 0.95, "level": "high", "interpretation": "The model is confident there is no relevant information."},
            citations=[]
        )

    result = await generate_answer_with_confidence(
        query=request.query,
        context=all_context
    )

    # Step 5: Extract highlighted citations
    citations = await extract_highlighted_citations(
        answer=result["answer"],
        context_chunks=context["chunks"],  # Only document chunks, not memories
        query=request.query
    )

    return QueryResponseWithCitations(
        answer=result["answer"],
        confidence=result["confidence"],
        citations=citations
    )
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single-pass summarization | Map-reduce for long docs | 2024 | Handles documents of any length |
| No confidence scores | OpenAI logprobs | 2024 | Native support, no fine-tuning needed |
| Simple citation (doc name) | Highlighted passages | 2025 | Auditable, verifiable responses |
| Manual memory facts | Mem0 with graph relationships | 2025 | Semantic search + relationship awareness |
| Flesch-Kincaid readability | LLM verification prompts | 2025 | Context-aware, more accurate |

**Deprecated/outdated:**
- `temperature=0` for all tasks: Use 0.3-0.4 for creative tasks like summarization/simplification
- Single-prompt summarization for long documents: Use map-reduce or refine chains
- Confidence from self-consistency: Logprobs faster and cheaper

## Open Questions

Things that couldn't be fully resolved:

1. **Optimal summary cache TTL**
   - What we know: 1 hour reasonable, documents don't change
   - What's unclear: Should it be longer? Per-document TTL based on update frequency?
   - Recommendation: Start with 1 hour, monitor cache hit rate, adjust

2. **Confidence threshold calibration**
   - What we know: 0.85 high, 0.60 medium are reasonable starting points
   - What's unclear: Optimal thresholds for this specific use case
   - Recommendation: Collect user feedback, adjust thresholds based on "wrong answer" reports

3. **Citation extraction cost**
   - What we know: Extra LLM call per chunk for highlighting
   - What's unclear: Is the UX benefit worth the latency/cost?
   - Recommendation: Make highlighting optional (query param), cache results

4. **Memory influence on query accuracy**
   - What we know: User facts can improve personalization
   - What's unclear: Can bad facts degrade answer quality?
   - Recommendation: Weight document context higher than memory context

5. **Shared memory governance**
   - What we know: Admin-only write access
   - What's unclear: Should there be an approval workflow? Version history?
   - Recommendation: Start simple (admin-only), add governance if needed

## Sources

### Primary (HIGH confidence)

**Official Documentation:**
- [OpenAI Cookbook - Using Logprobs](https://cookbook.openai.com/examples/using_logprobs) - Confidence score implementation patterns
- [LangChain RAG Documentation](https://docs.langchain.com/oss/python/langchain/rag) - Summarization and retrieval patterns
- [Mem0 Graph Memory Documentation](https://docs.mem0.ai/open-source/features/graph-memory) - Memory integration patterns
- [Tensorlake - Citation-Aware RAG](https://www.tensorlake.ai/blog/rag-citations) - Highlighted citation implementation

**LangChain Tutorials:**
- [5 Levels of Summarization](https://github.com/gkamradt/langchain-tutorials/blob/main/data_generation/5%20Levels%20Of%20Summarization%20-%20Novice%20To%20Expert.ipynb) - Stuff, map-reduce, refine patterns
- [LangChain Summarization Techniques](https://www.baeldung.com/cs/langchain-text-summarize) - Pattern comparison

### Secondary (MEDIUM confidence)

**Implementation Guides (2026):**
- [RAG Evaluation & Confidence Score](https://medium.com/@naresh.kancharla/rag-evaluation-confidence-score-dfd1bdd01b82) - RAGAS and logprobs approaches
- [Adding Confidence Score for LLM Results](https://medium.com/@johnpaulthermadomthomas/adding-confidence-score-for-lll-results-in-rag-chain-scenarios-7ccbaf6b74b6) - Weighted confidence calculation
- [FastAPI Smart Caching](https://medium.com/@bhagyarana80/3x-faster-responses-in-fastapi-smart-caching-with-async-lru-and-redis-for-high-concurrency-apis-6b8428772f22) - async_lru + Redis patterns

**Text Simplification Research:**
- [LLM-based Text Simplification](https://arxiv.org/abs/2505.01980) - Progressive simplification methods
- [LLM-Guided Planning for Text Simplification](https://arxiv.org/html/2508.11816) - Two-stage approach

### Tertiary (LOW confidence)

**Community Patterns:**
- GitHub discussions on citation highlighting
- LangChain GitHub issues on logprobs access
- Mem0 + RAG integration patterns (needs validation)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Using existing codebase libraries, official documentation verified
- Architecture: HIGH - Patterns from LangChain docs, OpenAI cookbook, production examples
- Summarization: HIGH - Well-documented LangChain patterns
- Confidence scores: HIGH - OpenAI official cookbook, clear implementation
- Citations: MEDIUM - Some LLM extraction reliability concerns
- Simplification: MEDIUM - Two-stage approach documented but less battle-tested
- Memory integration: MEDIUM - Depends on Phase 2 implementation

**Research date:** 2026-02-04
**Valid until:** 30 days (stable patterns, check for LangChain/OpenAI API changes)

**Critical Phase 5 Success Criteria:**
- [ ] Document summaries generated on-demand without re-upload
- [ ] Summary caching with Redis (1-hour TTL minimum)
- [ ] Simplified explanations with configurable reading levels
- [ ] Confidence scores on all query responses using logprobs
- [ ] Highlighted citations with exact text passages
- [ ] Admin-only shared memory write access
- [ ] User memory facts integrated into query context
- [ ] All features maintain user isolation (multi-tenant safe)
