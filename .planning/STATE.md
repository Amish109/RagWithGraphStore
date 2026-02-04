# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-04)

**Core value:** Users can upload documents and get intelligent, contextual answers that draw on both semantic similarity (vector search) and relationship understanding (graph search).
**Current focus:** Phase 5: Differentiation Features - READY

## Current Position

Phase: 5 of 6 (Differentiation Features) - READY TO START
Plan: 0 of 4 complete
Status: Ready
Last activity: 2026-02-04 - Completed 04-05-PLAN.md (Phase 4 COMPLETE)

Progress: [██████████] 100% (Phase 4)
Overall: [██████████] 70% (21/30 plans across all phases)

## Performance Metrics

**Velocity:**
- Total plans completed: 21
- Average duration: 4.6 min
- Total execution time: 1.7 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-foundation-core-rag | 5 | 18 min | 3.6 min |
| 02-multi-user-memory | 7 | 43 min | 6.1 min |
| 03-ux-streaming | 4 | 20 min | 5.0 min |
| 04-langgraph-workflows | 5 | 19 min | 3.8 min |

**Recent Trend:**
- Last 5 plans: 04-01 (4 min), 04-02 (5 min), 04-03 (5 min), 04-04 (3 min), 04-05 (2 min)
- Trend: Phase 4 completed efficiently - API endpoint integration straightforward with existing services

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Roadmap created: 6-phase structure following research recommendations (Foundation -> Multi-User -> UX -> LangGraph -> Differentiation -> Production)
- All 38 v1 requirements mapped to phases with 100% coverage
- Research identified critical pitfalls for Phase 1: semantic chunking, JWT security, Neo4j schema design, embedding dimension locking
- Research identified Phase 2 and Phase 4 as needing deeper investigation during planning
- **01-01:** Singleton database clients (neo4j_driver, qdrant_client) at module level for simplicity
- **01-01:** COSINE distance for Qdrant per OpenAI embedding recommendations
- **01-01:** Multi-tenant payload indexes created from start (user_id, document_id)
- **01-02:** PyJWT over python-jose for JWT encoding (simpler, no extra deps)
- **01-02:** Argon2 over bcrypt for password hashing (GPU-resistant, OWASP 2024+)
- **01-02:** OAuth2PasswordRequestForm for login (FastAPI docs compatibility)
- **01-02:** Stateless logout - server-side blocklist deferred to Phase 2+
- **01-03:** AsyncOpenAI client for non-blocking embedding operations
- **01-03:** Temperature=0 for deterministic LLM responses
- **01-03:** langchain_core.prompts import path (not deprecated langchain.prompts)
- **01-04:** pymupdf4llm for PDF extraction (Markdown output preserves structure)
- **01-04:** RecursiveCharacterTextSplitter with semantic separators (prevents poor chunking)
- **01-04:** Shared UUIDs between Neo4j chunks and Qdrant vectors for cross-referencing
- **01-04:** Background task processing to avoid blocking API
- **01-05:** User_id filtering on all Qdrant searches for multi-tenant isolation (Pitfall #6)
- **01-05:** Neo4j enrichment to add filename metadata to search results
- **01-05:** Separate 'memory' collection from 'documents' for Mem0 (Pitfall #1)
- **01-05:** Lazy Mem0 initialization defers connection until first use
- **02-01:** redis.asyncio over deprecated aioredis (merged into redis-py 5.0+)
- **02-01:** SHA-256 hashing for refresh tokens (fast enough for tokens)
- **02-01:** TTL on blocklist entries matching token lifetime (prevents unbounded growth)
- **02-01:** JTI in both access and refresh tokens for unified revocation
- **02-02:** HTTP-only cookies over URL parameters (prevents XSS, session hijacking)
- **02-02:** anon_ prefix distinguishes anonymous from authenticated user IDs
- **02-02:** UserContext schema provides unified interface for all endpoints
- **02-02:** COOKIE_SECURE=False for local dev, True for production
- **02-03:** Role stored in JWT for fast authorization (avoids DB lookup per request)
- **02-03:** Default role is 'user', admin assigned manually
- **02-03:** RoleChecker uses get_current_user (requires auth), not optional variant
- **02-04:** SHARED_MEMORY_USER_ID = '__shared__' sentinel for company memory
- **02-04:** Anonymous users can use memory API (tied to session ID)
- **02-04:** search_with_shared includes shared only for authenticated users
- **02-05:** Migration order: Neo4j first, then Qdrant, then Mem0 (by importance)
- **02-05:** Qdrant migration uses scroll + set_payload (no bulk update API)
- **02-05:** Mem0 migration uses copy-delete pattern (no user_id update support)
- **02-06:** APScheduler for daily TTL cleanup at configurable hour (default 3 AM)
- **02-06:** ANONYMOUS_DATA_TTL_DAYS = 7 (configurable)
- **02-06:** Admin API at /admin/memory/shared for shared memory management
- **02-07:** Unique UUIDs in test emails to avoid conflicts between test runs
- **02-07:** ASGITransport for direct app testing without real server
- **02-07:** Tests designed to run in CI with real environment (not mocked)
- **03-01:** Status code to error type mapping for consistent error strings
- **03-01:** Skip 'body' prefix in validation error field paths for cleaner messages
- **03-01:** Generic exception handler logs full details but returns sanitized message
- **03-02:** In-memory task tracking (not Redis) for simplicity - upgrade path available
- **03-02:** 1 hour TTL for task cleanup to prevent memory exhaustion
- **03-02:** Progress percentages: EXTRACTING=10%, CHUNKING=25%, EMBEDDING=40%, INDEXING=70%, SUMMARIZING=85%, COMPLETED=100%
- **03-03:** sse-starlette over built-in StreamingResponse for W3C SSE compliance
- **03-03:** X-Accel-Buffering: no header to disable nginx buffering
- **03-03:** Separate streaming LLM instance with streaming=True per request
- **03-04:** Cascade delete: Qdrant first, then Neo4j (orphaned vectors harmless)
- **03-04:** map_reduce summarization for >4 chunks to prevent token overflow
- **03-04:** Summary generated BEFORE indexing for storage with document
- **04-01:** psycopg_pool.AsyncConnectionPool for async PostgreSQL management
- **04-01:** Lazy initialization for PostgreSQL pool (consistent with other clients)
- **04-01:** Graceful fallback if PostgreSQL unavailable (warning, not crash)
- **04-01:** MEMORY_MAX_TOKENS=4000, MEMORY_SUMMARIZATION_THRESHOLD=0.75
- **04-02:** LIMIT 50 on all graph queries to prevent explosion (Pitfall #3)
- **04-02:** Fallback DOCUMENT_CONTEXT_QUERY when Entity nodes don't exist
- **04-02:** include_graph_context=False default for backward compatibility
- **04-02:** MatchAny for document filtering in retrieve_for_documents
- **04-03:** Thread ID format: {user_id}:doc_compare:{session_id} for cross-user isolation
- **04-03:** Linear workflow flow: retrieve -> expand_graph -> compare -> generate
- **04-03:** Module-level workflow caching for efficiency
- **04-03:** JSON response parsing with text fallback for robust analysis
- **04-04:** Token estimation: 4 chars = 1 token (standard approximation)
- **04-04:** Recent 5 interactions always preserved verbatim (Pitfall #4)
- **04-04:** LLM temperature=0.3 for summaries (slightly creative for quality)
- **04-04:** Delete-then-add pattern for memory consolidation
- **04-05:** ComparisonCitation separate from existing Citation (different fields)
- **04-05:** Require authentication for comparison endpoint (resource-intensive)
- **04-05:** Memory updated after each comparison interaction

### Pending Todos

None yet.

### Blockers/Concerns

**Phase 2 (Multi-User Core):** COMPLETE. All 7 plans executed successfully. Multi-tenant isolation verified through comprehensive security tests.

**Phase 3 (UX & Streaming):** COMPLETE. All 4 plans executed successfully. SSE streaming, document management, error handling, and task tracking all in place.

**Phase 4 (LangGraph Integration):** COMPLETE. All 5 plans executed successfully. Document comparison via LangGraph workflow with GraphRAG multi-hop reasoning, memory summarization, and API endpoint.

**Phase 5 (Differentiation Features):** Ready to start. On-demand summarization, text simplification, confidence scores, and shared knowledge integration.

## Session Continuity

Last session: 2026-02-04 - Phase 4 Wave 3 execution (04-05) - Phase 4 COMPLETE
Stopped at: Completed 04-05-PLAN.md, ready for Phase 5
Resume file: None
