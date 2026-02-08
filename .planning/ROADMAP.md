# Roadmap: RAGWithGraphStore

## Overview

This roadmap delivers a production-ready FastAPI backend for intelligent document Q&A with persistent memory, followed by a comprehensive Next.js production frontend. The backend (v1.0) established core RAG, multi-user isolation, streaming, and advanced features. The frontend (v2.0) replaces the Streamlit test UI with a polished Next.js application featuring SSE streaming, dark/light theme, responsive layout, and all backend features exposed through a modern component library.

## Milestones

- **v1.0: FastAPI Backend** (Phases 1-6) - Production-ready intelligent document Q&A backend
- **v1.1: Streamlit Test Frontend** (Phases 7-12) - Test UI (Phase 7 complete, Phases 8-12 superseded by v2.0)
- **v2.0: Next.js Production Frontend** (Phases 13-17) - Full production frontend replacing Streamlit

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

### Milestone v1.0: FastAPI Backend

- [x] **Phase 1: Foundation & Core RAG** - Database setup, authentication, document processing, basic retrieval
- [x] **Phase 2: Multi-User Core & Memory Integration** - Multi-tenant isolation, Mem0 memory management, session persistence
- [x] **Phase 3: UX & Streaming** - Streaming responses, document management, query history, graceful error handling
- [x] **Phase 4: LangGraph & Advanced Workflows** - Document comparison, GraphRAG multi-hop reasoning, memory summarization
- [x] **Phase 5: Differentiation Features** - Shared knowledge spaces, document summaries, highlighted citations, confidence scores
- [ ] **Phase 6: Production Hardening** - Observability, performance optimization, error handling, load testing (deferred)

### Milestone v1.1: Streamlit Test Frontend

- [x] **Phase 7: Foundation & Authentication** - Streamlit setup, API client, session state, auth flows (complete)
- [~] **Phases 8-12** — Superseded by v2.0 Next.js frontend

### Milestone v2.0: Next.js Production Frontend

- [ ] **Phase 13: Project Scaffold & Authentication** - Next.js setup, shadcn/ui, auth flows, dark/light theme
- [ ] **Phase 14: Document Management** - Upload, progress, list, delete, summaries
- [ ] **Phase 15: Chat & SSE Streaming** - Q&A interface, SSE streaming, citations, confidence
- [ ] **Phase 16: Comparison, Memory & Admin** - Document comparison, memory management, admin panel
- [ ] **Phase 17: Polish, Responsive & Final Integration** - Mobile layout, animations, error handling

## Phase Details

### Phase 1: Foundation & Core RAG
**Goal**: Establish infrastructure and deliver working document upload, processing, and question-answering with citations
**Depends on**: Nothing (first phase)
**Requirements**: CFG-01, CFG-02, CFG-03, CFG-04, CFG-05, AUTH-01, AUTH-02, AUTH-07, DOC-01, DOC-02, QRY-01, QRY-03, QRY-04, API-01, API-07, API-08, API-10
**Success Criteria** (what must be TRUE):
  1. User can register and login with email/password, receiving JWT tokens
  2. User can upload PDF and DOCX documents that are parsed, chunked, and stored in both Neo4j and Qdrant
  3. User can ask natural language questions and receive answers with source citations showing which documents were referenced
  4. System responds "I don't know" when context is insufficient rather than hallucinating
  5. All configuration (database connections, API keys, settings) is managed via environment variables
**Plans**: 5 plans in 4 waves

Plans:
- [x] 01-01-PLAN.md — Project scaffolding, configuration, database connections (Wave 1)
- [x] 01-02-PLAN.md — JWT authentication system (Wave 2)
- [x] 01-03-PLAN.md — Embedding and LLM generation services (Wave 2)
- [x] 01-04-PLAN.md — Document processing pipeline with dual-store indexing (Wave 3)
- [x] 01-05-PLAN.md — Query endpoint with citations and Mem0 config (Wave 4)

### Phase 2: Multi-User Core & Memory Integration
**Goal**: Ensure secure multi-tenant isolation and integrate Mem0 for persistent conversation memory
**Depends on**: Phase 1
**Requirements**: USR-01, USR-02, USR-03, USR-04, AUTH-03, AUTH-04, AUTH-05, AUTH-06, AUTH-08, MEM-01, MEM-02, MEM-03, MEM-04, MEM-05
**Success Criteria** (what must be TRUE):
  1. Each user has completely isolated document collections and cannot access other users' documents
  2. Each user has isolated memory space where conversations and preferences persist across sessions
  3. Anonymous users receive temporary sessions with unique IDs that work identically to authenticated sessions
  4. Anonymous users can register and all their documents/memories migrate to their permanent account seamlessly
  5. Temporary anonymous data automatically expires after configured period and is cleaned up from both Neo4j and Qdrant
  6. Admin users can add facts to shared company-wide memory that all authenticated users can query
  7. System remembers conversation history within sessions and user preferences across sessions
**Plans**: 7 plans in 4 waves

Plans:
- [x] 02-01-PLAN.md — Redis + refresh token rotation with single-use enforcement (Wave 1)
- [x] 02-02-PLAN.md — Anonymous session management with HTTP-only cookies (Wave 1)
- [x] 02-03-PLAN.md — RBAC with user/admin roles (Wave 2)
- [x] 02-04-PLAN.md — Memory service and API endpoints (Wave 2)
- [x] 02-05-PLAN.md — Anonymous-to-authenticated data migration (Wave 3)
- [x] 02-06-PLAN.md — TTL cleanup scheduler + shared memory management (Wave 3)
- [x] 02-07-PLAN.md — Multi-tenant isolation security tests (Wave 4)

### Phase 3: UX & Streaming
**Goal**: Polish user experience with streaming responses, document management UI, and robust error handling
**Depends on**: Phase 2
**Requirements**: QRY-02, DOC-03, DOC-04, MGMT-01, MGMT-02, MGMT-03, API-02, API-03
**Success Criteria** (what must be TRUE):
  1. User receives streaming responses (SSE) for queries with visible progress instead of waiting for complete answers
  2. User sees progress indicators during document upload and processing showing what stage is active
  3. User can list all their uploaded documents with metadata (name, size, upload date)
  4. User can delete documents and the system cascades deletion to both Neo4j and Qdrant stores
  5. System automatically generates document summaries on upload for quick reference
  6. Errors display helpful messages to users rather than crashing or showing stack traces
**Plans**: 4 plans in 2 waves

Plans:
- [x] 03-01-PLAN.md — Global exception handlers and ErrorResponse schema (Wave 1)
- [x] 03-02-PLAN.md — Task tracking for document processing progress (Wave 1)
- [x] 03-03-PLAN.md — SSE streaming for query responses (Wave 2)
- [x] 03-04-PLAN.md — Document management: delete, summaries, enhanced listing (Wave 2)

### Phase 4: LangGraph & Advanced Workflows
**Goal**: Enable complex multi-step reasoning for document comparison and advanced query workflows
**Depends on**: Phase 3
**Requirements**: QRY-05, MEM-06
**Success Criteria** (what must be TRUE):
  1. User can compare multiple documents and receive analysis showing similarities, differences, and cross-document insights
  2. System uses GraphRAG multi-hop reasoning through Neo4j to traverse entity relationships across documents
  3. System automatically summarizes conversation memory when context grows too large to prevent overflow
  4. LangGraph workflow state persists across requests allowing multi-turn complex queries
  5. Document comparison responses cite specific sections from multiple source documents
**Plans**: 5 plans in 3 waves

Plans:
- [x] 04-01-PLAN.md — PostgreSQL checkpointing + LangGraph infrastructure (Wave 1)
- [x] 04-02-PLAN.md — GraphRAG multi-hop retrieval service (Wave 1)
- [x] 04-03-PLAN.md — Document comparison LangGraph workflow (Wave 2)
- [x] 04-04-PLAN.md — Memory summarization service (Wave 2)
- [x] 04-05-PLAN.md — Document comparison API endpoint with citations (Wave 3)

### Phase 5: Differentiation Features
**Goal**: Deliver competitive advantages through shared knowledge, advanced summaries, and trust-building features
**Depends on**: Phase 4
**Requirements**: QRY-06, QRY-07, API-05, API-06
**Success Criteria** (what must be TRUE):
  1. User can request document summaries at any time without re-uploading files
  2. User can request simplified explanations of complex document content for easier understanding
  3. User can add arbitrary facts to their private memory that influence future query responses
  4. Responses include highlighted citations showing exact text passages from source documents
  5. Admin can add facts to shared memory and all authenticated users can query against this shared knowledge base
  6. System provides confidence scores on responses so users know when to verify answers
**Plans**: 4 plans in 3 waves

Plans:
- [x] 05-01-PLAN.md — On-demand document summarization service (Wave 1)
- [x] 05-02-PLAN.md — Text simplification service with reading level control (Wave 1)
- [x] 05-03-PLAN.md — Confidence scores and highlighted citations (Wave 2)
- [x] 05-04-PLAN.md — Memory API and shared knowledge integration (Wave 3)

### Phase 6: Production Hardening (Deferred)
**Goal**: Production-ready system with observability, performance optimization, and operational excellence
**Status**: Deferred

### Phase 7: Foundation & Authentication (v1.1 - Complete)
**Goal**: Establish Streamlit application structure with working authentication flows and persistent session state
**Status**: Complete (5/5 plans)

Plans:
- [x] 07-01-PLAN.md — Project scaffolding, API client, session state utilities (Wave 1)
- [x] 07-02-PLAN.md — Login page with callback-based auth flow (Wave 2)
- [x] 07-03-PLAN.md — Registration page with callback-based auth flow (Wave 2)
- [x] 07-04-PLAN.md — App entry, dynamic navigation, sidebar user info, logout (Wave 3)
- [x] 07-05-PLAN.md — Debug panel with token info, human verification (Wave 4)

### Phase 13: Project Scaffold & Authentication
**Goal**: Set up Next.js project with shadcn/ui, dark/light theme, and complete auth flows including anonymous access and migration
**Depends on**: Backend Phase 5 (completed)
**Requirements**: AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-05, AUTH-06, AUTH-07, AUTH-08, LAYOUT-01, LAYOUT-02, LAYOUT-05
**Success Criteria** (what must be TRUE):
  1. User can register, login, logout through polished forms
  2. JWT tokens stored in httpOnly cookies, auto-refresh before expiry
  3. Dark/light theme toggle works without flash (next-themes)
  4. Sidebar navigation renders with auth-aware sections
  5. Anonymous users can browse; registration migrates their data
  6. Toast notifications appear for auth actions

### Phase 14: Document Management
**Goal**: Full document lifecycle — upload, track progress, list, delete, summaries
**Depends on**: Phase 13
**Requirements**: DOC-01, DOC-02, DOC-03, DOC-04, DOC-05, DOC-06, LAYOUT-04
**Success Criteria** (what must be TRUE):
  1. User can drag-and-drop PDF/DOCX files with type/size validation
  2. Upload shows real-time processing progress (polling /documents/{id}/status)
  3. Document list shows filename, date, chunk count, status badge
  4. Delete shows confirmation dialog with optimistic UI update
  5. Document summaries available in 4 formats via tabs
  6. Loading skeletons shown during data fetch
  7. Each user sees only their own documents

### Phase 15: Chat & SSE Streaming
**Goal**: Core Q&A experience with streaming, citations, confidence, simplification
**Depends on**: Phase 14
**Requirements**: CHAT-01, CHAT-02, CHAT-03, CHAT-04, CHAT-05, CHAT-06, CHAT-07
**Success Criteria** (what must be TRUE):
  1. User types question and sees token-by-token streaming response
  2. Responses render as markdown (headers, lists, code blocks, tables)
  3. Citations appear below each response with source document links
  4. Confidence badge shows high/medium/low with tooltip
  5. "Simplify" button offers eli5/general/professional levels
  6. Chat history persists within session (zustand)
  7. Each user sees only their own chat (isolation via auth)
  8. Stream properly closes on navigation away (AbortController)

### Phase 16: Comparison, Memory & Admin
**Goal**: Document comparison, personal memory, admin panel
**Depends on**: Phase 15
**Requirements**: COMP-01, COMP-02, COMP-03, MEM-01, MEM-02, ADMIN-01
**Success Criteria** (what must be TRUE):
  1. User can select 2-5 documents and trigger comparison
  2. Comparison results show similarities, differences, cross-document insights
  3. User can ask follow-up questions in comparison context
  4. User can add/view/delete personal memory facts
  5. Admin sees admin-only nav items and shared knowledge management page
  6. Admin can add/list/delete shared company knowledge

### Phase 17: Polish, Responsive & Final Integration
**Goal**: Mobile layout, animations, loading states, error handling, final testing
**Depends on**: Phase 16
**Requirements**: LAYOUT-03
**Success Criteria** (what must be TRUE):
  1. App works on mobile devices with collapsible sidebar
  2. Page transitions use subtle animations (motion)
  3. Error boundaries catch and display errors gracefully
  4. All 22 backend endpoints have corresponding frontend features
  5. Anonymous → registered migration works end-to-end
  6. Multi-user isolation verified (login as different users)

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → (6 deferred) → 7 → (8-12 superseded) → 13 → 14 → 15 → 16 → 17

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation & Core RAG | 5/5 | Complete | 2026-02-04 |
| 2. Multi-User Core & Memory Integration | 7/7 | Complete | 2026-02-04 |
| 3. UX & Streaming | 4/4 | Complete | 2026-02-04 |
| 4. LangGraph & Advanced Workflows | 5/5 | Complete | 2026-02-04 |
| 5. Differentiation Features | 4/4 | Complete | 2026-02-04 |
| 6. Production Hardening | 0/5 | Deferred | - |
| 7. Foundation & Authentication | 5/5 | Complete | 2026-02-05 |
| 8-12. Streamlit Phases | - | Superseded | - |
| 13. Project Scaffold & Auth | 0/0 | Not started | - |
| 14. Document Management | 0/0 | Not started | - |
| 15. Chat & SSE Streaming | 0/0 | Not started | - |
| 16. Comparison, Memory & Admin | 0/0 | Not started | - |
| 17. Polish & Final Integration | 0/0 | Not started | - |
