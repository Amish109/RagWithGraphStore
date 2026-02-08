# Feature Landscape: Production Next.js Frontend for RAG Application

**Domain:** Production document Q&A / RAG chat frontend
**Researched:** 2026-02-08
**Confidence:** HIGH (based on analysis of production RAG UIs like Perplexity, ChatGPT, Open WebUI; current 2026 UI patterns; backend API audit)

## Executive Summary

Production RAG frontends in 2026 have converged on a set of patterns: chat-centric Q&A with inline numbered citations, progressive document upload with status tracking, confidence indicators that communicate uncertainty honestly, and streaming responses that feel conversational. The key differentiator between "demo" and "production" RAG UIs is how they handle the space between asking a question and trusting the answer -- citation display, confidence communication, and source traceability.

This project's backend already supports a rich feature set (SSE streaming, confidence scores with logprobs, highlighted citations with character offsets, document comparison, memory-augmented responses, text simplification). The frontend's job is to expose these capabilities through patterns users already understand from Perplexity, ChatGPT, and similar tools, while adding production-grade polish (dark/light theme, responsive layout, loading states, error recovery).

Key insight: **The backend is feature-complete. The frontend challenge is not "what to build" but "how to present it."** Every feature below maps directly to an existing backend endpoint. The complexity is in the UI interaction patterns, not in inventing new capabilities.

---

## Table Stakes

Features users expect in any production RAG/document Q&A application. Missing these makes the product feel broken or incomplete.

### Authentication and Session Management

| Feature | Why Expected | Complexity | Backend Endpoint | Notes |
|---------|--------------|------------|-----------------|-------|
| **Login form** | Users must authenticate to access their documents | Low | `POST /auth/login` (OAuth2PasswordRequestForm) | Email + password. Store JWT pair in httpOnly cookie via API route proxy. Show validation errors inline. |
| **Registration form** | New user onboarding | Low | `POST /auth/register` | Email + password + confirm. Anonymous session migration happens server-side automatically. Show migration stats banner on success. |
| **Logout** | Session termination | Low | `POST /auth/logout` | Clear cookies, redirect to login. Invalidates server-side via blocklist. |
| **Anonymous session** | Try-before-signup experience | Medium | Backend auto-creates via session cookie | Users land on chat immediately without auth wall. Soft prompt to register after meaningful interaction (e.g., after 3 queries or first upload). |
| **Token refresh** | Seamless session continuity | Medium | `POST /auth/refresh` | Silent refresh before token expiry. Automatic retry on 401. Single-use rotation means failed refresh = force re-login. |
| **Auth state indicator** | Users need to know their identity context | Low | Derived from JWT claims | Sidebar or header showing: user email, role badge (user/admin), or "Guest" for anonymous. |

### Chat / Q&A Interface

| Feature | Why Expected | Complexity | Backend Endpoint | Notes |
|---------|--------------|------------|-----------------|-------|
| **Chat input with submit** | Core interaction pattern | Low | `POST /query/stream` (primary) or `POST /query/enhanced` | Text input at bottom of chat area. Submit on Enter, Shift+Enter for newline. Disable during streaming. |
| **Streaming response display** | Users expect real-time token generation like ChatGPT | High | `POST /query/stream` (SSE) | Token-by-token display with smooth typewriter effect. Must handle SSE events: `status`, `citations`, `token`, `done`, `error`. Show "Searching documents..." and "Generating response..." status phases. |
| **Chat history (session)** | Users expect to scroll up and see previous exchanges | Medium | Client-side state (no backend history endpoint) | Persist in React state during session. Each message pair: user query + assistant response with citations. Consider localStorage for cross-refresh persistence. |
| **Empty state** | New users need guidance | Low | None | Show suggested questions based on uploaded documents, or generic prompts like "Upload a document and ask me anything." |
| **Error handling in chat** | Graceful failure | Low | SSE `error` event + HTTP errors | Show inline error message in chat flow (not a modal). Offer "Try again" button. Never show raw stack traces. |
| **Loading/thinking state** | User needs feedback during retrieval phase | Low | SSE `status` event (stage: "retrieving"/"generating") | Animated dots or skeleton in chat bubble. Show distinct phases: "Searching your documents..." then "Generating answer..." |
| **Copy response** | Users want to use answers elsewhere | Low | None (client-side) | Copy button on each assistant message. Copy as markdown or plain text. |

### Citation Display

| Feature | Why Expected | Complexity | Backend Endpoint | Notes |
|---------|--------------|------------|-----------------|-------|
| **Inline numbered citations** | Perplexity pattern is now table stakes | High | `POST /query/enhanced` returns `HighlightedCitation` with `highlighted_passage`, `highlight_start`, `highlight_end` | Parse answer text to insert `[1]`, `[2]` markers. Map to citation objects. |
| **Citation list below answer** | Users need to see sources at a glance | Medium | `citations` array in response | Show after each answer: filename, relevance score, short excerpt. Collapsible for space. |
| **Citation hover/click detail** | Users want to verify sources | Medium | `HighlightedCitation.chunk_text` + `highlighted_passage` | On hover: tooltip with highlighted passage in context. On click: expand to show full chunk with yellow-highlighted relevant passage. |
| **Document source links** | Navigate from citation to document | Low | `citation.document_id` + `citation.filename` | Link citation to document detail/summary page. Show page number if available. |

### Confidence Score Display

| Feature | Why Expected | Complexity | Backend Endpoint | Notes |
|---------|--------------|------------|-----------------|-------|
| **Confidence badge on response** | Users need to calibrate trust in AI answers | Low | `POST /query/enhanced` returns `ConfidenceScore` with `score`, `level`, `interpretation` | Color-coded badge: green (high, >=0.7), yellow (medium, 0.4-0.7), red (low, <0.4). Display level label. |
| **Confidence tooltip** | Power users want the "why" | Low | `ConfidenceScore.interpretation` field | On hover/click: show interpretation text. Show numeric score for transparency. |

### Document Management

| Feature | Why Expected | Complexity | Backend Endpoint | Notes |
|---------|--------------|------------|-----------------|-------|
| **Drag-and-drop upload zone** | Modern file upload expectation | Medium | `POST /documents/upload` (multipart) | Accept PDF and DOCX. Drag overlay with file type icons. Also support click-to-browse. Validate file type and size client-side before upload. Max 50MB (backend config). |
| **Upload progress tracking** | Users need feedback for long operations | High | `GET /documents/{id}/status` (polling) | Multi-stage progress: pending -> extracting -> chunking -> embedding -> indexing -> summarizing -> completed. Poll every 2-3 seconds. Handle "failed" status. |
| **Document list** | Users need to see and manage their documents | Low | `GET /documents/` | Table or card grid: filename, upload date, chunk count. Sort by date (newest first). Show processing status badge for in-progress documents. |
| **Document deletion** | Users need to remove documents | Low | `DELETE /documents/{id}` | Confirmation dialog before delete. Optimistic UI update with rollback on error. Show toast notification on success. |

### Layout and Navigation

| Feature | Why Expected | Complexity | Backend Endpoint | Notes |
|---------|--------------|------------|-----------------|-------|
| **Sidebar navigation** | Standard app layout pattern | Low | None | Sections: Chat (primary), Documents, Memory, Settings. Admin section conditionally visible. Collapsible on mobile. |
| **Dark/light theme toggle** | User preference, reduces eye strain | Low | None (client-side) | Use Tailwind dark mode with class strategy via next-themes. Persist preference in localStorage. Default to system preference. |
| **Responsive mobile layout** | Users access from phones/tablets | Medium | None | Chat-first on mobile. Sidebar becomes bottom nav or hamburger menu. Touch-friendly tap targets (min 44px). |
| **Loading skeletons** | Perceived performance | Low | None | Skeleton placeholders for document list, chat messages during load. Use shadcn/ui Skeleton component. |
| **Toast notifications** | Feedback for actions | Low | None | Success/error/info toasts. Auto-dismiss after 5s. Stack multiple. Use sonner via shadcn/ui. |

---

## Differentiators

Features that elevate the product beyond baseline expectations. Not required but create significant value.

### Enhanced Chat Experience

| Feature | Value Proposition | Complexity | Backend Endpoint | Notes |
|---------|-------------------|------------|-----------------|-------|
| **"Explain Simpler" button** | Instantly simplify complex answers at different reading levels | Low | `POST /query/simplify` with level: eli5/general/professional | Button below each response. Dropdown for level selection. |
| **Document summary on demand** | Quick document overview without reading | Low | `GET /query/documents/{id}/summary?summary_type=brief\|detailed\|executive\|bullet` | Button on document card. Tab interface for summary types. |
| **Suggested follow-up questions** | Guide users to ask better questions | Medium | Client-side generation (or add backend endpoint later) | After each response, suggest 2-3 related questions. |
| **Keyboard shortcuts** | Power user efficiency | Low | None | Cmd+K for search/new query, Escape to cancel streaming. Use shadcn/ui Command component. |
| **Markdown rendering in responses** | Rich formatting for structured answers | Low | None (client-side) | react-markdown with remark-gfm for tables, lists, code blocks. |
| **Message actions menu** | Quick actions per message | Low | None | Three-dot menu: Copy, Simplify, Share. |

### Document Comparison

| Feature | Value Proposition | Complexity | Backend Endpoint | Notes |
|---------|-------------------|------------|-----------------|-------|
| **Multi-document selection for comparison** | Enable cross-document analysis | Medium | `POST /compare/` (ComparisonRequest) | Checkbox selection on document list (2-5 docs). "Compare Selected" button. |
| **Structured comparison results** | Clear presentation of similarities vs differences | Medium | `ComparisonResponse` with similarities, differences, cross_document_insights, citations | Three-section layout: Similarities, Differences, Cross-Document Insights. |
| **Comparison chat continuation** | Multi-turn analysis of the same document set | High | `session_id` in ComparisonRequest + `GET /compare/{session_id}/state` | Follow-up questions in same session. |

### Memory and Personalization

| Feature | Value Proposition | Complexity | Backend Endpoint | Notes |
|---------|-------------------|------------|-----------------|-------|
| **Personal memory panel** | Users can add facts that influence future answers | Low | `POST /memory/` + `GET /memory/` + `DELETE /memory/{id}` | Settings-style page or sidebar panel. |
| **Memory-influenced response indicator** | Transparency about what influenced the answer | Low | Check if memory chunks in citations | Badge on responses that used memory context. |
| **Admin shared knowledge management** | Admins curate company-wide knowledge base | Medium | `POST /admin/memory/shared` + `GET /admin/memory/shared` + `DELETE /admin/memory/shared/{id}` | Admin-only page with CRUD interface. |

---

## Anti-Features

Features to explicitly NOT build. These add complexity without proportional value.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Real-time collaboration** | Backend doesn't support it; single-user analysis tool | Keep sessions single-user |
| **Document editing/annotation** | Backend is read-only analysis | Link to external editors |
| **Graph visualization** | Neo4j Browser exists for developers. No user value. | Show graph-derived insights as text |
| **Voice input/output** | Significant complexity for niche use case | Standard text input |
| **Multi-language UI** | Premature i18n | English only |
| **OAuth/social login** | Backend only supports JWT email/password | Email/password auth only |
| **Document preview/viewer** | Significant complexity (PDF rendering) | Show metadata + summary |
| **Conversation branching** | Complex state management | Linear chat history |
| **Client-side document processing** | Backend handles chunking/embedding | Upload to backend only |
| **WebSocket connection** | Backend uses SSE, not WebSocket | fetch + eventsource-parser |
| **Offline mode / PWA** | RAG requires backend LLM inference | Show clear "offline" state |

---

## Feature Dependencies

```
Authentication (FOUNDATIONAL - must be first)
  |
  +-> Token Management (refresh, storage, 401 handling)
  |     |
  |     +-> All Authenticated Features
  |           |
  |           +-> Document Upload
  |           |     +-> Processing Status Polling
  |           |           +-> Document List (shows completed docs)
  |           |                 +-> Document Summary
  |           |                 +-> Document Selection for Comparison
  |           |                       +-> Document Comparison
  |           |
  |           +-> Chat / Q&A (can work in parallel with documents)
  |           |     +-> SSE Streaming Connection
  |           |     +-> Citation Display (depends on streaming data)
  |           |     +-> Confidence Badge (depends on enhanced query)
  |           |     +-> Text Simplification (depends on having a response)
  |           |     +-> Chat History (accumulates from queries)
  |           |
  |           +-> Memory Management
  |                 +-> Personal Memory CRUD
  |                 +-> Admin Shared Memory (depends on role check)
  |                 +-> Memory Indicator on Responses
  |
  +-> Anonymous Session (PARALLEL to auth)
        +-> Same features as authenticated, minus memory/admin
        +-> Registration Upgrade Prompt
              +-> Data Migration Notification
```

---

## MVP Recommendation

### Priority 1: Core Shell (Week 1)
1. Auth flows (login, register, logout, token refresh)
2. Layout (sidebar nav, header with auth state, dark/light theme)
3. Responsive shell (mobile-friendly sidebar collapse)
4. Loading skeletons and toast notifications

### Priority 2: Document Management (Week 2)
1. Drag-and-drop upload with file type/size validation
2. Upload progress tracking (polling status endpoint)
3. Document list with metadata and status badges
4. Document deletion with confirmation

### Priority 3: Chat and Streaming (Week 2-3)
1. Chat interface with input, message list, empty state
2. SSE streaming with typewriter effect and status phases
3. Basic citation list below each response
4. Confidence badge on responses
5. Markdown rendering in responses

### Priority 4: Enhanced Citations and Interactions (Week 3)
1. Inline numbered citations in answer text
2. Citation hover/click with highlighted passage preview
3. "Explain Simpler" button with level selector
4. Copy response button

### Priority 5: Comparison and Memory (Week 4)
1. Multi-document comparison selection and results display
2. Personal memory CRUD panel
3. Admin shared knowledge management page
4. Keyboard shortcuts / command palette

### Defer to Post-MVP
- Chat export, voice input, document preview, graph visualization, conversation branching, usage analytics

---

## Backend API Coverage Matrix

| Backend Endpoint | Frontend Feature | Priority | Status |
|-----------------|-----------------|----------|--------|
| `POST /auth/login` | Login form | P1 | Table Stakes |
| `POST /auth/register` | Registration form | P1 | Table Stakes |
| `POST /auth/refresh` | Silent token refresh | P1 | Table Stakes |
| `POST /auth/logout` | Logout button | P1 | Table Stakes |
| `POST /documents/upload` | Drag-drop upload | P2 | Table Stakes |
| `GET /documents/` | Document list | P2 | Table Stakes |
| `GET /documents/{id}/status` | Upload progress | P2 | Table Stakes |
| `DELETE /documents/{id}` | Document deletion | P2 | Table Stakes |
| `POST /query/stream` | Streaming chat | P3 | Table Stakes |
| `POST /query/enhanced` | Enhanced query with confidence + citations | P3 | Table Stakes |
| `POST /query/` | Basic query (fallback) | P3 | Table Stakes |
| `GET /query/documents/{id}/summary` | Document summary | P2 | Differentiator |
| `POST /query/simplify` | Text simplification | P4 | Differentiator |
| `POST /compare/` | Document comparison | P5 | Differentiator |
| `GET /compare/{session_id}/state` | Comparison session state | P5 | Differentiator |
| `POST /memory/` | Add personal memory | P5 | Differentiator |
| `GET /memory/` | List memories | P5 | Differentiator |
| `POST /memory/search` | Search memories | P5 | Differentiator |
| `DELETE /memory/{id}` | Delete memory | P5 | Differentiator |
| `POST /admin/memory/shared` | Add shared knowledge (admin) | P5 | Differentiator |
| `GET /admin/memory/shared` | List shared knowledge (admin) | P5 | Differentiator |
| `DELETE /admin/memory/shared/{id}` | Delete shared knowledge (admin) | P5 | Differentiator |

**Coverage:** 22/22 backend endpoints have corresponding frontend features (100%).

---

## Sources

- Backend endpoint analysis from `/backend/app/api/` route files
- Backend config analysis from `/backend/app/config.py` (50MB upload limit, 30-min token expiry, 7-day refresh)
- [shadcn/ui Components](https://ui.shadcn.com/docs/components) -- available component inventory
- [shadcn-chat](https://shadcn-chat.vercel.app/) -- chat component patterns for shadcn/ui
- [ShapeofAI - Citations Pattern](https://www.shapeof.ai/patterns/citations)
- [Agentic Design - Confidence Visualization](https://agentic-design.ai/patterns/ui-ux-patterns/confidence-visualization-patterns)
- [Upstash - Using SSE to stream LLM responses in Next.js](https://upstash.com/blog/sse-streaming-llm-responses)
