# Requirements: RAGWithGraphStore

**Defined:** 2026-02-05
**Core Value:** Users can upload documents and get intelligent, contextual answers that draw on both semantic similarity (vector search) and relationship understanding (graph search).

## Milestone v1.1 Requirements

Requirements for Streamlit Test Frontend. Each maps to roadmap phases.

### Authentication

- [ ] **AUTH-F01**: User can login with email and password via form
- [ ] **AUTH-F02**: User can register new account via form
- [ ] **AUTH-F03**: User can logout via button
- [ ] **AUTH-F04**: Anonymous user gets automatic session without logging in
- [ ] **AUTH-F05**: Current user info displayed in sidebar (name, role, session type)
- [ ] **AUTH-F06**: Debug panel shows token expiry time and user ID

### Document Management

- [ ] **DOC-F01**: User can upload PDF files via drag-drop or file picker
- [ ] **DOC-F02**: User can upload DOCX files via drag-drop or file picker
- [ ] **DOC-F03**: User sees progress indicator during document processing
- [ ] **DOC-F04**: User can view list of uploaded documents with name, size, date
- [ ] **DOC-F05**: User can delete documents from list
- [ ] **DOC-F06**: User can view auto-generated summary for each document

### RAG Query & Chat

- [ ] **QRY-F01**: User can enter natural language questions in text input
- [ ] **QRY-F02**: User sees streaming response with typewriter effect
- [ ] **QRY-F03**: Response includes source citations with document names
- [ ] **QRY-F04**: Response shows confidence score (high/medium/low badge)
- [ ] **QRY-F05**: User can see chat history (previous Q&A in session)
- [ ] **QRY-F06**: User can click "Explain Simpler" to get simplified explanation

### Document Comparison

- [ ] **CMP-F01**: User can select 2+ documents to compare
- [ ] **CMP-F02**: User sees comparison results (similarities, differences, insights)
- [ ] **CMP-F03**: Comparison includes citations from multiple source documents

### Memory

- [ ] **MEM-F01**: User can add facts to personal memory via form
- [ ] **MEM-F02**: User can view stored memory entries
- [ ] **MEM-F03**: Responses show when memory context is used (labeled)

### Admin Features

- [ ] **ADM-F01**: Admin-only pages visible only to admin users
- [ ] **ADM-F02**: Admin can add facts to shared company-wide knowledge base
- [ ] **ADM-F03**: Admin can view shared memory entries

### Testing & Debug

- [ ] **TST-F01**: User can login as different users to verify isolation
- [ ] **TST-F02**: User can test anonymous-to-registered data migration flow
- [ ] **TST-F03**: User can view raw API requests and responses (inspector)
- [ ] **TST-F04**: User can test raw backend endpoints directly

## Future Requirements

Deferred to future milestones. Tracked but not in current roadmap.

### Enhanced UX

- **UX-F01**: Dark/light theme toggle
- **UX-F02**: Mobile-responsive layout
- **UX-F03**: Keyboard shortcuts for common actions
- **UX-F04**: Export chat history to PDF/Markdown

### Advanced Testing

- **TST-V2-01**: Automated test runner for backend endpoints
- **TST-V2-02**: Performance metrics dashboard
- **TST-V2-03**: Load testing simulation

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Graph visualization | Use Neo4j Browser directly |
| Production-grade styling | This is a test UI, not production |
| OAuth/social login | Backend only supports JWT email/password |
| Real-time collaboration | Backend doesn't support this |
| Document editing | Backend is read-only analysis |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| AUTH-F01 | TBD | Pending |
| AUTH-F02 | TBD | Pending |
| AUTH-F03 | TBD | Pending |
| AUTH-F04 | TBD | Pending |
| AUTH-F05 | TBD | Pending |
| AUTH-F06 | TBD | Pending |
| DOC-F01 | TBD | Pending |
| DOC-F02 | TBD | Pending |
| DOC-F03 | TBD | Pending |
| DOC-F04 | TBD | Pending |
| DOC-F05 | TBD | Pending |
| DOC-F06 | TBD | Pending |
| QRY-F01 | TBD | Pending |
| QRY-F02 | TBD | Pending |
| QRY-F03 | TBD | Pending |
| QRY-F04 | TBD | Pending |
| QRY-F05 | TBD | Pending |
| QRY-F06 | TBD | Pending |
| CMP-F01 | TBD | Pending |
| CMP-F02 | TBD | Pending |
| CMP-F03 | TBD | Pending |
| MEM-F01 | TBD | Pending |
| MEM-F02 | TBD | Pending |
| MEM-F03 | TBD | Pending |
| ADM-F01 | TBD | Pending |
| ADM-F02 | TBD | Pending |
| ADM-F03 | TBD | Pending |
| TST-F01 | TBD | Pending |
| TST-F02 | TBD | Pending |
| TST-F03 | TBD | Pending |
| TST-F04 | TBD | Pending |

**Coverage:**
- v1.1 requirements: 28 total
- Mapped to phases: 0 (pending roadmap)
- Unmapped: 28

---
*Requirements defined: 2026-02-05*
*Last updated: 2026-02-05 after milestone v1.1 scoping*
