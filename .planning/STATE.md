# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-04)

**Core value:** Users can upload documents and get intelligent, contextual answers that draw on both semantic similarity (vector search) and relationship understanding (graph search).
**Current focus:** Phase 2 Complete - Ready for Phase 3: UX & Streaming

## Current Position

Phase: 2 of 6 (Multi-User Core & Memory Integration) - COMPLETE
Plan: 7 of 7 complete
Status: Phase 2 Complete
Last activity: 2026-02-04 - Completed 02-07-PLAN.md (Wave 4 - Security Tests)

Progress: [██████████] 100% (Phase 2)
Overall: [████░░░░░░] 40% (12/30 plans across all phases)

## Performance Metrics

**Velocity:**
- Total plans completed: 12
- Average duration: 5.0 min
- Total execution time: 1.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-foundation-core-rag | 5 | 18 min | 3.6 min |
| 02-multi-user-memory | 7 | 43 min | 6.1 min |

**Recent Trend:**
- Last 5 plans: 02-03 (3 min), 02-04 (4 min), 02-05 (5 min), 02-06 (5 min), 02-07 (19 min)
- Trend: 02-07 longer due to comprehensive test suite (561 lines)

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

### Pending Todos

None yet.

### Blockers/Concerns

**Phase 2 (Multi-User Core):** COMPLETE. All 7 plans executed successfully. Multi-tenant isolation verified through comprehensive security tests.

**Phase 4 (LangGraph Integration):** Research flagged LangGraph workflow patterns for document comparison using GraphRAG as complex. Need deeper research during planning for checkpoint configuration, state management with dual stores, and workflow design patterns.

## Session Continuity

Last session: 2026-02-04 - Phase 2 Wave 4 execution (02-07)
Stopped at: Completed Phase 2, ready for Phase 3: UX & Streaming
Resume file: None
