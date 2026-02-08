# Requirements: RAGWithGraphStore

**Defined:** 2026-02-08
**Core Value:** Users can upload documents and get intelligent, contextual answers that draw on both semantic similarity (vector search) and relationship understanding (graph search).

## Milestone v1.1 Requirements (Superseded)

*Phase 7 completed. Phases 8-12 superseded by v2.0 Next.js frontend.*

### Authentication (v1.1)
- [x] **AUTH-F01**: User can login with email and password via form
- [x] **AUTH-F02**: User can register new account via form
- [x] **AUTH-F03**: User can logout via button
- [x] **AUTH-F04**: Anonymous user gets automatic session without logging in
- [x] **AUTH-F05**: Current user info displayed in sidebar (name, role, session type)
- [x] **AUTH-F06**: Debug panel shows token expiry time and user ID

## Milestone v2.0 Requirements

Requirements for Next.js production frontend. Each maps to roadmap phases 13-17.

### Authentication

- [ ] **AUTH-01**: User can register with email and password via form
- [ ] **AUTH-02**: User can login with email and password via form
- [ ] **AUTH-03**: User can logout and be redirected to login page
- [ ] **AUTH-04**: User's JWT tokens refresh automatically before expiry
- [ ] **AUTH-05**: User can use the app anonymously without logging in
- [ ] **AUTH-06**: Auth state persists across page refresh (httpOnly cookies)
- [ ] **AUTH-07**: When anonymous user registers, documents and chat migrate to new account
- [ ] **AUTH-08**: User sees migration success notification showing what was transferred

### Layout & Navigation

- [ ] **LAYOUT-01**: User sees sidebar navigation with collapsible sections
- [ ] **LAYOUT-02**: User can toggle between dark and light theme
- [ ] **LAYOUT-03**: User can use the app on mobile devices (responsive layout)
- [ ] **LAYOUT-04**: User sees loading skeletons while data loads
- [ ] **LAYOUT-05**: User sees toast notifications for actions

### Document Management

- [ ] **DOC-01**: User can upload PDF/DOCX via drag-and-drop zone
- [ ] **DOC-02**: User sees real-time processing progress after upload
- [ ] **DOC-03**: User can view list of uploaded documents with metadata
- [ ] **DOC-04**: User can delete documents with confirmation dialog
- [ ] **DOC-05**: User can view document summaries (brief/detailed/executive/bullet)
- [ ] **DOC-06**: Each user sees only their own documents (multi-user isolation)

### Chat & Q&A

- [ ] **CHAT-01**: User can ask questions and see streaming responses (SSE)
- [ ] **CHAT-02**: User sees markdown-rendered responses with formatting
- [ ] **CHAT-03**: User sees citations with source references below answers
- [ ] **CHAT-04**: User sees confidence score badge on each response
- [ ] **CHAT-05**: User can request simplified explanations (eli5/general/professional)
- [ ] **CHAT-06**: User can see and continue conversation history within session
- [ ] **CHAT-07**: Each user sees only their own chat history (multi-user isolation)

### Document Comparison

- [ ] **COMP-01**: User can select 2-5 documents for comparison
- [ ] **COMP-02**: User sees structured comparison results (similarities, differences, insights)
- [ ] **COMP-03**: User can ask follow-up questions about a comparison

### Memory Management

- [ ] **MEM-01**: User can view, search, and delete auto-saved personal memories
- [ ] **MEM-02**: Admin can manage shared company knowledge (add/list/delete)

### Admin

- [ ] **ADMIN-01**: Admin sees admin-only navigation and can manage shared knowledge

## Future Requirements

Deferred to future release. Tracked but not in current roadmap.

### Notifications
- **NOTIF-01**: User receives in-app notifications for processing completion
- **NOTIF-02**: User receives notification when document processing fails

### Advanced Search
- **SEARCH-01**: User can search across all documents with filters
- **SEARCH-02**: User can save and re-run common queries

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| OAuth/social login | JWT with email/password is sufficient for v2.0 |
| WebSocket streaming | Backend uses SSE, not WebSocket |
| Offline mode | Requires server connection for RAG |
| Multi-language UI | English only for v2.0 |
| Custom theme builder | Dark/light toggle is sufficient |
| Graph visualization | Use Neo4j Browser directly |
| Real-time collaboration | Single-user document interactions |
| Document editing | Read-only analysis and Q&A |
| Mobile native app | Web responsive is sufficient |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| AUTH-01 | Phase 13 | Pending |
| AUTH-02 | Phase 13 | Pending |
| AUTH-03 | Phase 13 | Pending |
| AUTH-04 | Phase 13 | Pending |
| AUTH-05 | Phase 13 | Pending |
| AUTH-06 | Phase 13 | Pending |
| AUTH-07 | Phase 13 | Pending |
| AUTH-08 | Phase 13 | Pending |
| LAYOUT-01 | Phase 13 | Pending |
| LAYOUT-02 | Phase 13 | Pending |
| LAYOUT-05 | Phase 13 | Pending |
| DOC-01 | Phase 14 | Pending |
| DOC-02 | Phase 14 | Pending |
| DOC-03 | Phase 14 | Pending |
| DOC-04 | Phase 14 | Pending |
| DOC-05 | Phase 14 | Pending |
| DOC-06 | Phase 14 | Pending |
| LAYOUT-04 | Phase 14 | Pending |
| CHAT-01 | Phase 15 | Pending |
| CHAT-02 | Phase 15 | Pending |
| CHAT-03 | Phase 15 | Pending |
| CHAT-04 | Phase 15 | Pending |
| CHAT-05 | Phase 15 | Pending |
| CHAT-06 | Phase 15 | Pending |
| CHAT-07 | Phase 15 | Pending |
| COMP-01 | Phase 16 | Pending |
| COMP-02 | Phase 16 | Pending |
| COMP-03 | Phase 16 | Pending |
| MEM-01 | Phase 16 | Pending |
| MEM-02 | Phase 16 | Pending |
| ADMIN-01 | Phase 16 | Pending |
| LAYOUT-03 | Phase 17 | Pending |

**Coverage:**
- v2.0 requirements: 32 total
- Mapped to phases: 32
- Unmapped: 0 ✓

---
*Requirements defined: 2026-02-08*
*Last updated: 2026-02-08 after v2.0 milestone definition*
