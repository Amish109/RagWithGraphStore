# RAGWithGraphStore

## What This Is

A FastAPI backend service for intelligent document Q&A with persistent memory. Users upload PDFs and DOCX files, then ask questions, request summaries, get explanations, or compare documents. The system uses RAG (Retrieval Augmented Generation) combining graph-based knowledge (Neo4j) and vector search (Qdrant) via Mem0 SDK, with LangChain ChatOpenAI for multi-step reasoning.

## Core Value

Users can upload documents and get intelligent, contextual answers that draw on both semantic similarity (vector search) and relationship understanding (graph search).

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] User can upload PDF documents to their private memory
- [ ] User can upload DOCX documents to their private memory
- [ ] User can ask factual questions about their documents
- [ ] User can request document summaries
- [ ] User can request simplified explanations of document content
- [ ] User can compare multiple documents
- [ ] User can add arbitrary facts to their private memory
- [ ] User can add facts to shared (company-wide) memory
- [ ] User can query and get answers combining graph + vector search (RAG)
- [ ] User can register and login with JWT authentication
- [ ] Anonymous user gets temporary session-based memory space
- [ ] Anonymous user's data migrates to permanent account on registration
- [ ] Temporary anonymous data expires after configured time period
- [ ] All configuration managed via Pydantic BaseSettings / environment variables

### Out of Scope

- Frontend/UI — this is a backend API service only
- OAuth/social login — JWT with email/password is sufficient for v1
- Real-time collaboration — single-user document interactions
- Document editing — read-only analysis and Q&A

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

- **Tech stack**: FastAPI, LangGraph, Mem0 SDK, Neo4j, Qdrant, LangChain ChatOpenAI, Pydantic
- **Document formats**: PDF and DOCX only for v1
- **LLM provider**: OpenAI via LangChain (requires API key)
- **Infrastructure**: Requires running Neo4j and Qdrant instances

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Mem0 SDK for memory management | Provides unified interface for graph + vector storage | — Pending |
| JWT for authentication | Simple, stateless, well-supported in FastAPI | — Pending |
| Session-based anonymous access | Allows try-before-signup UX | — Pending |
| Private + shared memory model | Balances user privacy with organizational knowledge | — Pending |

---
*Last updated: 2026-02-04 after initialization*
