# RAGWithGraphStore

## What This Is

A full-stack intelligent document Q&A system with persistent memory. The FastAPI backend handles document processing, RAG retrieval, and multi-user memory management. The Streamlit frontend provides a test UI to exercise all backend features. The system uses RAG combining graph-based knowledge (Neo4j) and vector search (Qdrant) via Mem0 SDK, with LangChain ChatOpenAI for multi-step reasoning.

## Core Value

Users can upload documents and get intelligent, contextual answers that draw on both semantic similarity (vector search) and relationship understanding (graph search).

## Current Milestone: v1.1 Streamlit Test Frontend

**Goal:** Build a comprehensive Streamlit UI to test and demonstrate all backend features.

**Target features:**
- Authentication flows (register, login, logout, anonymous, admin)
- Document management (upload, list, delete, summaries)
- RAG Q&A with citations, confidence scores, and simplification
- Document comparison
- Memory/chat persistence
- Multi-user isolation verification
- Admin shared knowledge management
- Anonymous-to-authenticated data migration testing

## Requirements

### Validated

*Backend v1.0 — shipped 2026-02-04:*
- ✓ User can upload PDF/DOCX documents to private memory
- ✓ User can ask factual questions about documents with citations
- ✓ User can request document summaries and simplified explanations
- ✓ User can compare multiple documents (GraphRAG)
- ✓ User can add facts to private memory
- ✓ Admin can add facts to shared memory
- ✓ RAG combines graph + vector search
- ✓ JWT authentication with refresh tokens
- ✓ Anonymous sessions with data migration on registration
- ✓ Temporary data expires after configured period
- ✓ Streaming responses (SSE)
- ✓ Confidence scores and highlighted citations

### Active

*Frontend v1.1 — in progress:*
- [ ] User can register, login, and logout via UI
- [ ] Anonymous user can use app without logging in
- [ ] User can upload PDF/DOCX and see processing progress
- [ ] User can list and delete their documents
- [ ] User can ask questions and see streaming answers with citations
- [ ] User can view confidence scores on responses
- [ ] User can request simplified explanations
- [ ] User can compare multiple documents
- [ ] User can see and continue conversation history
- [ ] User can add facts to personal memory
- [ ] Admin can upload to shared knowledge base
- [ ] Admin can view/manage shared memory
- [ ] Multi-user isolation is testable (login as different users)
- [ ] Anonymous data migration is testable (use → register → verify)

### Out of Scope

- OAuth/social login — JWT with email/password is sufficient
- Real-time collaboration — single-user document interactions
- Document editing — read-only analysis and Q&A
- Graph visualization in UI — use Neo4j Browser directly
- Production-grade UI design — this is a test/demo frontend

## Context

**Technical approach:**
- Mem0 SDK handles memory management, configured with Neo4j (graph store) and Qdrant (vector store)
- LangGraph orchestrates multi-step reasoning workflows
- LangChain ChatOpenAI provides the LLM backbone for generation and reasoning
- FastAPI exposes RESTful endpoints for all operations
- Pydantic BaseSettings centralizes configuration from environment variables

**Memory model:**
- Private memory: Per-user isolated space for documents and facts
- Shared memory: Company-wide knowledge accessible to all authenticated users
- Temporary memory: Session-based space for anonymous users, migrates on registration

## Constraints

- **Backend stack**: FastAPI, LangGraph, Mem0 SDK, Neo4j, Qdrant, LangChain ChatOpenAI, Pydantic
- **Frontend stack**: Streamlit (test UI)
- **Document formats**: PDF and DOCX only
- **LLM provider**: OpenAI via LangChain (requires API key)
- **Infrastructure**: Requires running Neo4j, Qdrant, Redis, and PostgreSQL instances

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Mem0 SDK for memory management | Provides unified interface for graph + vector storage | ✓ Good |
| JWT for authentication | Simple, stateless, well-supported in FastAPI | ✓ Good |
| Session-based anonymous access | Allows try-before-signup UX | ✓ Good |
| Private + shared memory model | Balances user privacy with organizational knowledge | ✓ Good |
| Streamlit for test frontend | Rapid prototyping, Python-native, easy backend integration | — Pending |
| Monorepo structure (/backend, /frontend) | Shared planning, unified versioning | — Pending |

---
*Last updated: 2026-02-05 after milestone v1.1 initialization*
