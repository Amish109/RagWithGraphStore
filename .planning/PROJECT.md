# RAGWithGraphStore

## What This Is

A full-stack intelligent document Q&A system with persistent memory. The FastAPI backend handles document processing, RAG retrieval, and multi-user memory management. The Next.js production frontend provides a polished, responsive web app with SSE streaming, dark/light theme, and all backend features exposed through a modern UI. The system uses RAG combining graph-based knowledge (Neo4j) and vector search (Qdrant) via Mem0 SDK, with LangChain ChatOpenAI for multi-step reasoning.

## Core Value

Users can upload documents and get intelligent, contextual answers that draw on both semantic similarity (vector search) and relationship understanding (graph search).

## Current Milestone: v2.0 Next.js Production Frontend

**Goal:** Replace the Streamlit test frontend with a full production Next.js frontend featuring SSE streaming, dark/light theme, responsive layout, and all backend features.

**Target features:**
- Authentication flows (register, login, logout, anonymous, admin) with JWT httpOnly cookies
- Document management (upload with drag-drop, list, delete, summaries)
- RAG Q&A with SSE streaming, citations, confidence scores, and simplification
- Document comparison with follow-up questions
- Memory management (personal + shared)
- Admin shared knowledge management
- Multi-user isolation
- Anonymous-to-authenticated data migration
- Dark/light theme, responsive mobile layout, loading skeletons, animations

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

*Frontend v1.1 Streamlit — shipped 2026-02-05 (Phase 7):*
- ✓ User can register, login, and logout via UI
- ✓ Anonymous user can use app without logging in
- ✓ Dynamic navigation with role-based access

### Active

*Frontend v2.0 — in progress:*
- [ ] Complete auth with JWT httpOnly cookies and auto-refresh
- [ ] Anonymous-to-authenticated data migration
- [ ] Document upload with drag-drop and processing progress
- [ ] Document list, delete, summaries
- [ ] Chat Q&A with SSE streaming and markdown rendering
- [ ] Citations, confidence scores, simplification levels
- [ ] Document comparison with follow-up questions
- [ ] Personal memory management
- [ ] Admin shared knowledge management
- [ ] Dark/light theme, responsive layout, loading skeletons

### Out of Scope

- OAuth/social login — JWT with email/password is sufficient
- Real-time collaboration — single-user document interactions
- Document editing — read-only analysis and Q&A
- Graph visualization in UI — use Neo4j Browser directly
- WebSocket — backend uses SSE, not WebSocket
- Offline mode — requires server connection
- Multi-language UI — English only
- Custom theme builder — dark/light toggle is sufficient

## Context

**Technical approach:**
- Mem0 SDK handles memory management, configured with Neo4j (graph store) and Qdrant (vector store)
- LangGraph orchestrates multi-step reasoning workflows
- LangChain ChatOpenAI provides the LLM backbone for generation and reasoning
- FastAPI exposes RESTful endpoints for all operations
- Next.js 15 with App Router provides production frontend
- shadcn/ui + Tailwind CSS v4 for component library and styling
- zustand for client-side state management
- httpOnly cookies via Next.js API route proxy for secure auth

**Memory model:**
- Private memory: Per-user isolated space for documents and facts
- Shared memory: Company-wide knowledge accessible to all authenticated users
- Temporary memory: Session-based space for anonymous users, migrates on registration

## Constraints

- **Backend stack**: FastAPI, LangGraph, Mem0 SDK, Neo4j, Qdrant, LangChain ChatOpenAI, Pydantic
- **Frontend stack**: Next.js 15 + React 19 + Tailwind CSS v4 + shadcn/ui + zustand + motion
- **Document formats**: PDF and DOCX only
- **LLM provider**: OpenAI via LangChain (requires API key)
- **Infrastructure**: Requires running Neo4j, Qdrant, Redis, and PostgreSQL instances
- **Auth**: JWT with httpOnly cookies via Next.js API route proxy (not localStorage)
- **SSE**: POST-based SSE via fetch + eventsource-parser (not EventSource API)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Mem0 SDK for memory management | Provides unified interface for graph + vector storage | ✓ Good |
| JWT for authentication | Simple, stateless, well-supported in FastAPI | ✓ Good |
| Session-based anonymous access | Allows try-before-signup UX | ✓ Good |
| Private + shared memory model | Balances user privacy with organizational knowledge | ✓ Good |
| Streamlit for test frontend | Rapid prototyping, Python-native, easy backend integration | ✓ Good (served its purpose) |
| Replace Streamlit with Next.js | Production-grade UI, SSR, streaming, responsive | — Pending |
| httpOnly cookies via API proxy | Prevents XSS token theft, secure auth | — Pending |
| Tailwind CSS v4 + shadcn/ui | Modern CSS-first config, accessible components | — Pending |
| zustand for state management | Lightweight, no provider needed, persistent storage | — Pending |
| fetch + eventsource-parser for SSE | EventSource can't POST, backend SSE is POST-based | — Pending |
| Pin zod@3 | v4 incompatible with @hookform/resolvers | — Pending |

---
*Last updated: 2026-02-08 after milestone v2.0 initialization*
