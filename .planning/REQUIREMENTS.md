# Requirements: RAGWithGraphStore

**Defined:** 2026-02-04
**Core Value:** Users can upload documents and get intelligent, contextual answers that draw on both semantic similarity (vector search) and relationship understanding (graph search).

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Document Processing

- [ ] **DOC-01**: User can upload PDF documents to their private memory
- [ ] **DOC-02**: User can upload DOCX documents to their private memory
- [ ] **DOC-03**: User sees progress indicator during document upload/processing
- [ ] **DOC-04**: System generates document summary on upload

### Query & Response

- [ ] **QRY-01**: User can ask natural language questions about their documents
- [ ] **QRY-02**: User receives streaming responses (SSE) for queries
- [ ] **QRY-03**: Responses include source citations with document references
- [ ] **QRY-04**: System responds "I don't know" when context is insufficient
- [ ] **QRY-05**: User can compare multiple documents (GraphRAG multi-hop reasoning)
- [ ] **QRY-06**: User can request document summaries
- [ ] **QRY-07**: User can request simplified explanations of document content

### Memory & Session

- [ ] **MEM-01**: System maintains conversation history within session
- [ ] **MEM-02**: Session persists across browser/client refresh
- [ ] **MEM-03**: System remembers user preferences across sessions (cross-session memory)
- [ ] **MEM-04**: User can add arbitrary facts to their private memory
- [ ] **MEM-05**: Admin can add facts to shared (company-wide) memory (users can only read)
- [ ] **MEM-06**: System summarizes memory to prevent context overflow

### Multi-User & Isolation

- [ ] **USR-01**: Each user has isolated document collection (private space)
- [ ] **USR-02**: Each user has isolated memory space
- [ ] **USR-03**: Shared knowledge space accessible to all authenticated users
- [ ] **USR-04**: User's documents are not visible to other users

### Authentication

- [ ] **AUTH-01**: User can register with email and password
- [ ] **AUTH-02**: User can login and receive JWT access token
- [ ] **AUTH-03**: Anonymous user gets temporary session with unique ID
- [ ] **AUTH-04**: Anonymous user's data migrates to account on registration
- [ ] **AUTH-05**: Temporary anonymous data expires after configured time period
- [ ] **AUTH-06**: System supports refresh token rotation for extended sessions
- [ ] **AUTH-07**: User can logout (invalidate session)
- [ ] **AUTH-08**: Admin role with elevated permissions for shared memory management

### Document Management

- [ ] **MGMT-01**: User can list their uploaded documents
- [ ] **MGMT-02**: User can delete documents (cascades to both Neo4j and Qdrant)
- [ ] **MGMT-03**: User can view document metadata (name, size, upload date)

### Configuration & Infrastructure

- [ ] **CFG-01**: All settings configurable via environment variables (Pydantic BaseSettings)
- [ ] **CFG-02**: System connects to Neo4j for graph storage
- [ ] **CFG-03**: System connects to Qdrant for vector storage
- [ ] **CFG-04**: System uses OpenAI API for LLM and embeddings
- [ ] **CFG-05**: Mem0 SDK configured with Neo4j + Qdrant dual stores

### API Endpoints

- [ ] **API-01**: POST /documents/upload - Upload PDF/DOCX document
- [ ] **API-02**: GET /documents - List user's documents
- [ ] **API-03**: DELETE /documents/{id} - Delete a document
- [ ] **API-04**: POST /query - Ask a question (streaming response)
- [ ] **API-05**: POST /memory - Add fact to private memory (user) or shared memory (admin only)
- [ ] **API-06**: GET /memory - Retrieve user's memory/facts
- [ ] **API-07**: POST /auth/register - Register new user
- [ ] **API-08**: POST /auth/login - Login and get tokens
- [ ] **API-09**: POST /auth/refresh - Refresh access token
- [ ] **API-10**: POST /auth/logout - Logout user

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Advanced Document Processing

- **DOC-V2-01**: Table and chart extraction from documents
- **DOC-V2-02**: Image/diagram analysis within documents
- **DOC-V2-03**: Document versioning and history

### Advanced Query

- **QRY-V2-01**: Follow-up question suggestions after responses (higher priority)
- **QRY-V2-02**: Confidence scores on responses
- **QRY-V2-03**: Highlighted citations showing exact text passages
- **QRY-V2-04**: Voice input for queries
- **QRY-V2-05**: Hybrid search (semantic + keyword BM25)
- **QRY-V2-06**: Re-ranking layer for improved relevance

### Integrations

- **INT-01**: Slack integration for querying
- **INT-02**: Teams integration
- **INT-03**: API webhooks for document events

### Analytics

- **ANL-01**: Query analytics dashboard
- **ANL-02**: Usage metrics per user

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Frontend/UI | Backend API only - frontend is separate project |
| OAuth/social login | JWT with email/password sufficient for v1 |
| Real-time collaboration | Different product category, high complexity |
| Document editing | Read-only analysis and Q&A |
| Custom embedding models | OpenAI embeddings sufficient, custom adds complexity |
| Multi-LLM provider support | Adds complexity for minimal benefit |
| Every document format | PDF + DOCX covers 80% of use cases |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| (To be populated during roadmap creation) | | |

**Coverage:**
- v1 requirements: 38 total
- Mapped to phases: 0
- Unmapped: 38 ⚠️

---
*Requirements defined: 2026-02-04*
*Last updated: 2026-02-04 after initial definition*
