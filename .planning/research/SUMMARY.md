# Project Research Summary

**Project:** RAG with Graph Store - Streamlit Test Frontend
**Domain:** Test/Demo UI for FastAPI RAG Backend
**Researched:** 2026-02-05
**Confidence:** HIGH

## Executive Summary

A Streamlit test UI for a FastAPI backend serves a distinct purpose: comprehensive verification of backend functionality through a functional, debuggable interface. Unlike production UIs that hide complexity, test UIs should expose what's happening under the hood - showing request/response payloads, displaying backend errors verbatim, and exposing configuration options. This isn't bad UX for a test tool; it's essential for thorough backend validation.

The recommended approach leverages Streamlit 1.54.0's strengths for rapid prototyping: built-in components (file upload, session state), st.navigation for dynamic multi-page apps with role-based access, and SSE streaming via sseclient-py for real-time LLM responses. The core integration pattern uses a centralized API client (httpx 0.28.1+) stored in session state with JWT tokens in HTTP-only cookies for persistence across browser refreshes. Critical to success: avoid storing JWT tokens solely in session state (lost on refresh), prevent infinite rerun loops in authentication flows, and properly handle SSE streaming with generator wrappers for st.write_stream().

Key risks center on authentication state management (JWT persistence, anonymous session migration), SSE streaming buffering (requires proper generator conversion and proxy configuration), and file upload multipart encoding (Streamlit's UploadedFile must be converted to proper format). Mitigation: establish cookie-based token storage from the start, use sseclient-py with generator patterns for streaming, and implement proper multipart encoding with filename/bytes/type tuples. The 10-day timeline is realistic for covering all 24 backend features if SSE streaming complexity is addressed early in Phase 3.

## Key Findings

### Recommended Stack

Streamlit 1.54.0+ (latest as of Feb 2026) provides native multi-page apps with st.navigation, built-in session state management, and new st.App ASGI integration (skip for this milestone - adds complexity). Python 3.10+ required. For HTTP communication, httpx 0.28.1+ is recommended over requests (20% faster, HTTP/2 support, async/sync flexibility), paired with sseclient-py 1.7.2+ for consuming FastAPI SSE endpoints. Development uses python-dotenv 1.0.0+ for environment variable management alongside Streamlit's secrets system.

**Core technologies:**
- **Streamlit 1.54.0+**: Web UI framework - native multi-page apps with st.navigation, session state, file upload widgets, and st.write_stream for SSE consumption
- **httpx 0.28.1+**: HTTP client for API calls - modern requests alternative with async/sync support, HTTP/2, ~20% faster performance
- **sseclient-py 1.7.2+**: SSE stream consumption - pure-Python client for FastAPI EventSourceResponse, seamlessly integrates with httpx streaming
- **python-dotenv 1.0.0+**: Environment variable management - standard for loading API URLs and config from .env files

**Critical anti-pattern:** DO NOT use streamlit-authenticator library - it manages its own user database and conflicts with FastAPI JWT auth. Store JWT tokens in st.session_state after login and include in Authorization headers for all API calls.

### Expected Features

Test UIs differ from production UIs: polish matters less than coverage and debuggability. Features should enable thorough testing without becoming a maintenance burden.

**Must have (table stakes):**
- **Authentication testing:** Login/register forms, logout button, token refresh, anonymous session support, auth state display showing current user/role/token expiry
- **Document management testing:** File upload widget with progress bar, document list display (verify user isolation), delete document functionality, document summary view
- **RAG query testing:** Query input, streaming response display with SSE, citation display with confidence scores, chat history for context verification, simplification request toggle
- **Memory management testing:** Add personal fact, add shared knowledge (admin only), view memory, clear memory for test cleanup
- **Multi-user isolation testing:** Multi-tab login capability, user switching for test accounts, isolation verification showing user sees only their data, anonymous to auth migration flow
- **Debugging & observability:** Request/response inspector (raw JSON), error display (full backend errors), API endpoint selector (localhost/staging/prod), performance metrics (latency tracking)

**Should have (competitive):**
- **Enhanced testing features:** Bulk document upload for load testing, query templates for repetitive tests, test data generator for fake users/documents, state snapshot (export/import session state), automated test scenarios
- **Enhanced UX features:** Sidebar navigation with st.navigation, export test results to JSON/CSV, comparison view for side-by-side response testing
- **Advanced debugging:** Token counter for API cost monitoring, memory inspector to visualize Mem0 state (complex, may use Neo4j Browser instead)

**Defer (v2+):**
- Production-grade design polish (default Streamlit components are sufficient for test UI)
- Responsive mobile layout (developers test on desktop)
- Custom CSS/styling beyond basics (maintenance burden)
- Backend logs viewer (complex, requires log streaming endpoint)
- Session replay (complex in Streamlit's execution model)
- Real-time collaboration (not testing collaborative features)

**Anti-features (don't build):**
- Hiding backend errors (test UI must show what failed)
- Auto-retry on failure (masks intermittent issues)
- Mocking backend responses (defeats purpose of testing real backend)
- Input validation on frontend (test backend validation instead)
- User management UI (create test users via backend scripts)

### Architecture Approach

The architecture separates concerns: app.py as navigation entrypoint with st.navigation, pages/ directory for individual feature pages, utils/ for business logic (API client, auth helpers, streaming utilities, reusable components). This structure makes code testable and maintainable.

**Major components:**
1. **app.py (Entrypoint)** - Navigation menu using st.navigation with dynamic page building based on auth state and role. Initializes session state (api_client, auth tokens), builds page dictionary conditionally (admin pages only for admin role), runs navigation.
2. **utils/api_client.py (Centralized API Communication)** - Single APIClient instance in session state manages authentication headers and requests. Uses httpx.Session with JWT tokens in Authorization header, handles token refresh on 401, provides consistent error handling across all pages.
3. **pages/*.py (Feature Pages)** - Individual pages for login (01_login.py), documents (02_documents.py), chat (03_chat.py), comparison (04_comparison.py), memory (05_memory.py), admin (06_admin.py). Each calls utils/api_client for backend communication.
4. **utils/auth.py (Auth State Management)** - Handles login/logout flows, stores JWT tokens in HTTP-only cookies (persistence across refresh) + session state (runtime access), manages token expiry checking and refresh, provides is_authenticated() helpers.
5. **utils/streaming.py (SSE Streaming Helpers)** - Converts FastAPI SSE endpoints to Python generators for st.write_stream(). Wraps sseclient-py to consume EventSourceResponse, yields chunks incrementally for typewriter effect.

**Key architectural patterns:**
- **Centralized API client with session state:** Single source of truth for backend communication, consistent auth header management, token refresh in one place
- **Dynamic navigation based on auth state:** st.navigation with conditional page visibility (admin pages only for admin role), enforces access control at navigation level
- **Token persistence across reloads:** HTTP-only cookies (persists across refresh) + session state (runtime convenience), mitigates WebSocket disconnect issue
- **SSE streaming with st.write_stream:** Consume FastAPI SSE with sseclient-py, convert to generator, display with typewriter effect
- **Progress tracking for uploads:** Poll backend task status endpoint, display with st.progress and st.status for long-running tasks

### Critical Pitfalls

1. **JWT Token Lost on Browser Refresh** - JWT tokens stored only in st.session_state disappear on browser refresh, logging users out unexpectedly. Session state survives script reruns but not WebSocket disconnects or page refreshes. **Prevention:** Store JWT tokens in HTTP-only cookies (using streamlit-cookies-manager or extra-streamlit-components) as primary storage, with session state as read cache. Backend sets tokens in secure, same-site cookies that persist across refreshes.

2. **Infinite Rerun Loop in Authentication Flow** - Calling st.rerun() inside button handlers without state guards creates infinite loops. Buttons return True only on click rerun, then immediately False, but if st.rerun() executes before state updates, condition repeats indefinitely. **Prevention:** Use session state flags instead of direct button checks (set st.session_state.authenticated = True in callback), use callbacks on buttons rather than inline st.rerun() calls, add state guards (if not st.session_state.get('auth_in_progress')) before triggering rerun.

3. **SSE Streaming Buffered Instead of Real-Time** - SSE responses from FastAPI appear all at once after completion rather than streaming incrementally. Using standard HTTP clients without proper SSE handling causes chunk buffering. st.write_stream() expects Python generators, not raw SSE EventSource. **Prevention:** Use sseclient-py library to consume SSE streams, convert SSE stream to Python generator before passing to st.write_stream(), ensure FastAPI StreamingResponse with media_type="text/event-stream", disable buffering in proxies (nginx X-Accel-Buffering: no).

4. **Anonymous Session Data Orphaned Without Migration** - Users create content as anonymous users, then register. Without explicit migration logic, their documents/memories remain tied to old anonymous ID in Neo4j/Qdrant, unreachable after auth. **Prevention:** Store anonymous session ID in HTTP-only cookie for persistence, on registration check for anonymous_session_id cookie, backend migration endpoint updates documents from anonymous_session_id to authenticated_user_id, handle race conditions with locking, implement TTL-based cleanup job for unmigrated anonymous data.

5. **File Upload Fails with 422 Unprocessable Entity** - st.file_uploader() returns UploadedFile object (BytesIO wrapper), not raw bytes. Sending directly to FastAPI causes type mismatch and validation failure. **Prevention:** Extract bytes with uploaded_file.getvalue(), format as proper multipart tuple with (filename, bytes, mime_type), use requests files parameter correctly: files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}

## Implications for Roadmap

Based on research, this is a 10-day project with 5 phases focused on feature coverage over polish. Critical path: establish authentication foundation with cookie persistence first, then document management, then SSE streaming (complex but essential), then memory/multi-user testing, finally debugging enhancements.

### Phase 1: Authentication Foundation (Day 1-2)
**Rationale:** All features depend on working auth. Token persistence and session state management must be established correctly from the start - retrofitting cookie storage after building on session-state-only auth is architecturally disruptive. Dynamic navigation with st.navigation enables role-based access control needed for admin features.

**Delivers:** Users can login/register, logout, see auth state (current user/role/token status), navigate between test areas. Anonymous session support enabled. Navigation menu appears with role-based page visibility.

**Addresses:** Login form, registration form, logout button, token refresh, anonymous session, auth state display (from FEATURES.md table stakes)

**Avoids:** Pitfall #1 (JWT token lost on refresh) by implementing HTTP-only cookies from start, Pitfall #2 (infinite rerun loop) by using callbacks and state guards in auth flow, Pitfall #6 (pickle vulnerability) by validating JWT claims before session state storage

**Stack elements:** Streamlit 1.54.0 with st.navigation, httpx for API calls, python-dotenv for API_URL config

**Research flag:** SKIP - Well-documented patterns for Streamlit auth and st.navigation

### Phase 2: Document Upload & Management (Day 3-4)
**Rationale:** Documents are foundational for RAG queries. Must work before testing Q&A features. Progress tracking pattern established here applies to other long-running operations (document comparison).

**Delivers:** Users can upload documents (PDF/DOCX) with progress indication, see document list filtered by user (verify isolation), delete documents with confirmation, view document summaries. Error handling for upload failures.

**Addresses:** File upload widget, upload progress bar, document list display, delete document, document summary view (from FEATURES.md table stakes)

**Avoids:** Pitfall #5 (file upload 422 error) by implementing proper multipart encoding with getvalue()/filename/type tuple pattern

**Stack elements:** Streamlit file_uploader widget (200MB default limit, override if needed), httpx multipart/form-data upload

**Implements:** Document management component from ARCHITECTURE.md, polling status endpoint pattern

**Research flag:** SKIP - Standard file upload patterns, well-documented

### Phase 3: RAG Query & SSE Streaming (Day 5-7)
**Rationale:** Core product feature and most complex technical challenge. SSE streaming requires generator wrapper patterns and proper proxy configuration. Citations and confidence scores are table stakes for RAG testing. This phase takes longest due to SSE complexity.

**Delivers:** Users can submit queries, see streaming responses with typewriter effect, view citations (source doc, page, confidence score), access chat history for context verification, request simplified answers. Performance metrics track latency.

**Addresses:** Query input, streaming response display, citation display, confidence score, chat history, simplification request (from FEATURES.md table stakes)

**Avoids:** Pitfall #3 (SSE buffering) by using sseclient-py with generator conversion for st.write_stream(), proper FastAPI StreamingResponse configuration, proxy buffering disabled if needed

**Stack elements:** sseclient-py 1.7.2+ for SSE consumption, httpx streaming, st.write_stream for typewriter display

**Implements:** Query & Response component from ARCHITECTURE.md with SSE streaming pattern, utils/streaming.py generator wrapper

**Research flag:** NEEDS RESEARCH - SSE streaming in Streamlit is non-trivial, test with real backend early to catch buffering issues

### Phase 4: Memory & Multi-User Testing (Day 8-9)
**Rationale:** Memory features (personal/shared) and multi-user isolation testing are differentiating capabilities. Anonymous-to-auth migration is unique feature requiring careful testing. Role-based access (admin-only shared knowledge) validates RBAC implementation.

**Delivers:** Users can add personal facts, view stored memories, clear memory for test cleanup. Admins can add shared knowledge (role-gated UI). Multi-tab testing instructions provided. User switching dropdown for quick test account login. Isolation verification display confirms user sees only their data. Anonymous → auth migration test flow validates data transfer.

**Addresses:** Add personal fact, add shared knowledge (admin), view memory, clear memory, multi-tab login, user switching, isolation verification, anonymous → auth migration (from FEATURES.md table stakes)

**Avoids:** Pitfall #4 (anonymous session orphaning) by implementing and testing migration flow end-to-end, verifying documents appear in authenticated view after registration

**Stack elements:** Memory API endpoints (personal/shared), admin page with conditional navigation

**Implements:** Memory Features component from ARCHITECTURE.md, admin features with role checking

**Research flag:** SKIP - Standard REST API patterns, migration flow needs testing but not research

### Phase 5: Debugging & Polish (Day 10)
**Rationale:** Debugging features improve testing efficiency but aren't blocking for functionality. Request/response inspector, error display, and API endpoint selector accelerate issue diagnosis. These are "nice-to-have" enhancements for production-quality test UI.

**Delivers:** Request/response inspector shows raw JSON for debugging. Error display shows full backend error messages and stack traces. API endpoint selector switches between localhost/staging/prod. Performance metrics track request/streaming/total latency. Export test results downloads session data as JSON.

**Addresses:** Request/response inspector, error display, API endpoint selector, performance metrics, export test results (from FEATURES.md table stakes + differentiators)

**Stack elements:** Streamlit expander/columns for inspector UI, JSON display components

**Implements:** utils/components.py reusable UI components (error_display, citation_card, loading_spinner)

**Research flag:** SKIP - Standard Streamlit UI patterns

### Phase Ordering Rationale

- **Auth first (Phase 1)** because all subsequent features require working JWT token management. Cookie persistence must be architecturally correct from start - retrofitting is disruptive.
- **Documents before queries (Phase 2)** because RAG queries in Phase 3 need documents to query against. Upload/list/delete establishes foundational CRUD patterns.
- **Streaming early (Phase 3)** because SSE is most complex technical challenge. Solving generator wrapper patterns and proxy configuration early prevents late-stage blocking issues.
- **Memory + multi-user testing late (Phase 4)** because they depend on working auth (Phase 1) and documents (Phase 2). Migration testing requires full auth flow.
- **Debugging last (Phase 5)** because it's enhancement, not blocking. Inspector/metrics improve testing efficiency but UI is functional without them.

This order matches ARCHITECTURE.md build order (Wave 1-5) and addresses PITFALLS.md critical issues in prevention phases.

### Research Flags

**Phases needing deeper research during planning:**
- **Phase 3 (SSE Streaming):** SSE consumption in Streamlit is non-trivial. Generator wrapper patterns with sseclient-py, proxy buffering configuration, handling disconnect/reconnect. Test with real backend early to catch buffering issues before full implementation.

**Phases with standard patterns (skip research-phase):**
- **Phase 1 (Auth Foundation):** Well-documented Streamlit session state + JWT patterns, st.navigation examples in official docs
- **Phase 2 (Document Management):** Standard file upload and CRUD patterns, well-documented in Streamlit + FastAPI integration guides
- **Phase 4 (Memory & Multi-User):** Standard REST API integration, migration is implementation not research
- **Phase 5 (Debugging & Polish):** Standard Streamlit UI components, no novel patterns

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Streamlit 1.54.0 and httpx are latest stable versions with official documentation. SSE patterns verified in community examples. |
| Features | HIGH | Test UI feature landscape well-defined by domain. Table stakes vs differentiators clear from RAG demo best practices and Streamlit use cases. |
| Architecture | HIGH | Multi-page Streamlit app patterns documented in official guides. FastAPI integration patterns proven in multiple 2026 community examples. st.navigation approach is recommended 2026 pattern. |
| Pitfalls | HIGH | All 7 critical pitfalls sourced from real-world Streamlit + FastAPI integration issues in GitHub issues, Stack Overflow, Streamlit Discuss forums. Prevention strategies verified. |

**Overall confidence:** HIGH

Research is based on official 2026 Streamlit documentation (1.54.0 release notes, st.navigation guide, session state API), FastAPI integration patterns from Pybites and TestDriven.io tutorials, and real-world pitfalls from Streamlit Discuss forums and GitHub issues. SSE streaming patterns verified in multiple community implementations.

### Gaps to Address

- **SSE streaming reliability with Streamlit reruns:** sseclient-py pattern is documented but interaction with Streamlit's rerun model needs validation. Does connection persist across reruns or need reconnect? Test with prototype early in Phase 3.

- **File upload size limits interaction:** Streamlit default is 200MB. Does this conflict with FastAPI limits? Backend configuration should be checked and aligned. Test with large files (>10MB) in Phase 2.

- **Token refresh timing strategy:** Should UI proactively refresh tokens before expiry (better UX, more complex), or reactively on 401 (simpler, occasional auth hiccups)? Recommend proactive for production-quality test UI, decide in Phase 1.

- **Anonymous session ID generation ownership:** Should Streamlit UI generate session ID or backend? Recommend backend for consistency and security (prevents client-side ID manipulation), confirm in Phase 1.

- **Memory inspector visualization value:** Is there value in visualizing Neo4j graph/Qdrant vectors in test UI, or is Neo4j Browser sufficient? Recommend Neo4j Browser to avoid complexity, reassess in Phase 4 if needed.

## Sources

### Primary (HIGH confidence)
- [Streamlit 2026 Release Notes](https://docs.streamlit.io/develop/quick-reference/release-notes/2026) - st.App ASGI entry point, OIDC tokens, file_uploader improvements, session-scoped caching
- [Streamlit Multi-page Apps](https://docs.streamlit.io/develop/concepts/multipage-apps) - st.navigation best practices, dynamic page building
- [Streamlit Session State](https://docs.streamlit.io/develop/concepts/architecture/session-state) - State management patterns, persistence limitations
- [Streamlit st.write_stream](https://docs.streamlit.io/develop/api-reference/write-magic/st.write_stream) - Streaming content display with generators
- [HTTPX 0.28.1 PyPI](https://pypi.org/project/httpx/) - Latest version, HTTP/2 support, performance benchmarks
- [sseclient-py PyPI](https://pypi.org/project/sseclient-py/) - SSE client library for consuming FastAPI SSE endpoints
- [FastAPI Request Files](https://fastapi.tiangolo.com/tutorial/request-files/) - File upload handling with UploadFile

### Secondary (MEDIUM confidence)
- [From Backend To Frontend: Connecting FastAPI And Streamlit - Pybites](https://pybit.es/articles/from-backend-to-frontend-connecting-fastapi-and-streamlit/) - Client-server architecture patterns, API integration
- [Serving ML Model with FastAPI and Streamlit - TestDriven.io](https://testdriven.io/blog/fastapi-streamlit/) - File upload patterns, deployment
- [Implement JWT Authentication for Streamlit - Medium](https://blog.yusufberki.net/implement-jwt-authentication-for-the-streamlit-application-2e3b0ef884ef) - JWT token storage patterns, session state management
- [FASTAPI-SSE-Event-Streaming with Streamlit - GitHub](https://github.com/sarthakkaushik/FASTAPI-SSE-Event-Streaming-with-Streamlit) - SSE streaming implementation example
- [Bridging LangGraph and Streamlit - Medium](https://medium.com/@yigitbekir/bridging-langgraph-and-streamlit-a-practical-approach-to-streaming-graph-state-13db0999c80d) - SSE streaming patterns for LLM responses
- [Why Session State Not Persisting Between Refresh - Streamlit Discuss](https://discuss.streamlit.io/t/why-session-state-is-not-persisting-between-refresh/32020) - Session state limitations, cookie persistence patterns
- [Post Request with file_uploader Throws 422 - Streamlit Discuss](https://discuss.streamlit.io/t/post-request-with-parameter-as-a-streamlit-file-uploader-object-for-a-pdf-throws-422-unprocessable-entity-on-fastapi/45020) - File upload multipart encoding solution
- [Using st.rerun in Button Causes Infinite Loop - GitHub Issue #9232](https://github.com/streamlit/streamlit/issues/9232) - Rerun loop prevention strategies
- [Ultimate Guide to Securing JWT with httpOnly Cookies - Wisp Blog](https://www.wisp.blog/blog/ultimate-guide-to-securing-jwt-authentication-with-httponly-cookies) - Cookie security best practices

### Tertiary (LOW confidence)
- [8 Streamlit/Gradio Patterns to Demo AI - Medium](https://medium.com/@Nexumo_/8-streamlit-gradio-patterns-to-demo-ai-like-a-pro-f6a0c6114ff8) - Demo UI patterns for RAG apps
- [RAG Based Conversational Chatbot Using Streamlit - Medium](https://medium.com/@mrcoffeeai/rag-based-conversational-chatbot-using-streamlit-364c4c02c2f1) - Chat UI patterns
- [ScrapingAnt: Requests vs HTTPX](https://scrapingant.com/blog/requests-vs-httpx) - HTTP client performance comparison
- [Oxylabs: HTTPX vs Requests vs AIOHTTP](https://oxylabs.io/blog/httpx-vs-requests-vs-aiohttp) - HTTP client benchmarks

---
*Research completed: 2026-02-05*
*Ready for roadmap: yes*
