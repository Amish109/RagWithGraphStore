# Feature Research: Streamlit Test UI for FastAPI Backend

**Domain:** Test/Demo UI for RAG Backend Testing
**Researched:** 2026-02-05
**Confidence:** HIGH (based on 2026 Streamlit documentation, FastAPI integration patterns, and RAG demo UI best practices)

## Executive Summary

A Streamlit test UI for a FastAPI backend serves a distinct purpose: **comprehensive verification of backend functionality**, not production-grade user experience. The feature landscape differs from production UIs in that polish and edge-case handling matter less than coverage and debuggability.

Key insight: **Test UIs should expose what's happening under the hood**. Production UIs hide complexity; test UIs reveal it. Show request/response payloads, display backend errors verbatim, expose all configuration options. This isn't bad UX for a test tool—it's the whole point.

For testing a RAG backend with JWT auth, document management, SSE streaming, and multi-user isolation, the critical decision is: **What features enable thorough testing without becoming a maintenance burden?** Streamlit's strengths (rapid prototyping, built-in components, session state) align perfectly with test UI needs, but its weaknesses (limited real-time capabilities, rerun model) require workarounds.

---

## Feature Landscape

### Table Stakes (Must Have for Test UI)

Features essential for exercising backend functionality. Missing these = can't test critical backend features.

#### Authentication Testing

| Feature | Why Expected | Complexity | Backend Dependency | Notes |
|---------|--------------|------------|-------------------|-------|
| **Login Form** | Must test JWT auth flow | Low | POST /auth/login | Streamlit st.text_input for email/password, st.button for submit. Store token in st.session_state. |
| **Registration Form** | Must test user creation | Low | POST /auth/register | Similar to login. Needs email, password, confirmation fields. |
| **Logout Button** | Must test token invalidation | Low | POST /auth/logout | Clear st.session_state, call logout endpoint. |
| **Token Refresh** | Must test refresh token flow | Medium | POST /auth/refresh | Auto-refresh on 401 errors. Show refresh status for debugging. |
| **Anonymous Session** | Must test anonymous user flows | Medium | Backend session ID generation | Generate session ID, store in st.session_state, pass to backend. |
| **Auth State Display** | Must show current auth status | Low | None (frontend only) | Show: logged in as [user], role, token expiry. Critical for debugging. |

#### Document Management Testing

| Feature | Why Expected | Complexity | Backend Dependency | Notes |
|---------|--------------|------------|-------------------|-------|
| **File Upload Widget** | Must test document ingestion | Low | POST /documents/upload | st.file_uploader with PDF/DOCX accept. Show file metadata before upload. |
| **Upload Progress Bar** | Must verify streaming progress works | Medium | Backend streaming upload | Use st.progress with upload chunks. Backend must support progress reporting. |
| **Document List Display** | Must verify user isolation | Low | GET /documents | Show table with: name, size, upload date, user. Test filtering by user. |
| **Delete Document** | Must test document removal | Low | DELETE /documents/{id} | st.button per document. Confirm before delete (st.warning). |
| **Document Summary View** | Must test summarization endpoint | Medium | GET /documents/{id}/summary | Display generated summary. Show generation time, token count. |

#### RAG Query Testing

| Feature | Why Expected | Complexity | Backend Dependency | Notes |
|---------|--------------|------------|-------------------|-------|
| **Query Input** | Must test Q&A endpoint | Low | POST /query | st.text_area or st.chat_input. Allow multi-line questions. |
| **Streaming Response Display** | Must verify SSE streaming | High | SSE endpoint with streaming | **Critical but complex.** Use sseclient-py to consume SSE. Display tokens as they arrive. |
| **Citation Display** | Must verify citation extraction | Medium | Response includes citations | Show cited chunks with: source doc, page number, confidence score. Linkable to source. |
| **Confidence Score** | Must verify confidence calculation | Low | Response includes score | Display as percentage + color (red <50%, yellow 50-80%, green >80%). |
| **Chat History** | Must test conversation context | Medium | Backend maintains context | Display previous Q&A pairs. Test context is maintained across queries. |
| **Simplification Request** | Must test "explain like I'm 5" feature | Low | POST /query with simplify=true | Toggle or button to request simplified answer. |

#### Memory Management Testing

| Feature | Why Expected | Complexity | Backend Dependency | Notes |
|---------|--------------|------------|-------------------|-------|
| **Add Personal Fact** | Must test private memory API | Low | POST /memory/personal | Form to add fact. Show stored facts list. |
| **Add Shared Knowledge (Admin)** | Must test shared memory + role check | Medium | POST /memory/shared (admin only) | Only show if user is admin. Test permission enforcement. |
| **View Memory** | Must verify memory retrieval | Low | GET /memory | Display stored facts with metadata (source, timestamp, user). |
| **Clear Memory** | Must test memory deletion | Low | DELETE /memory | Clear button with confirmation. Useful for test cleanup. |

#### Multi-User Isolation Testing

| Feature | Why Expected | Complexity | Backend Dependency | Notes |
|---------|--------------|------------|-------------------|-------|
| **Multi-Tab Login** | Must test concurrent users | Low | None (browser feature) | Instructions to open multiple tabs, login as different users. |
| **User Switching** | Must quickly change logged-in user | Medium | Logout + Login | Quick-switch dropdown for test accounts. Pre-populate credentials. |
| **Isolation Verification** | Must show user sees only their data | Low | Document list filtered by user | Display user ID next to each resource. Verify cross-contamination. |
| **Anonymous → Auth Migration** | Must test data migration flow | High | Backend migration endpoint | Use anonymous → register → verify data migrated. Show before/after. |

#### Debugging & Observability

| Feature | Why Expected | Complexity | Backend Dependency | Notes |
|---------|--------------|------------|-------------------|-------|
| **Request/Response Inspector** | Must debug API issues | Medium | None (frontend logging) | Show raw JSON request/response in expandable st.expander. |
| **Error Display** | Must show backend errors verbatim | Low | Backend error responses | Don't hide errors. Show full stack trace if available. |
| **API Endpoint Selector** | Must test against different environments | Low | None (frontend only) | Dropdown: localhost, staging, prod. Store in st.session_state. |
| **Performance Metrics** | Must measure query latency | Low | Frontend timing | Show: request time, streaming start time, total time. |

---

### Differentiators (Nice-to-Have for Testing)

Features that improve testing experience but aren't essential for coverage.

#### Enhanced Testing Features

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Bulk Document Upload** | Test system under load | Medium | Upload multiple files at once. Track individual progress. |
| **Query Templates** | Speed up repetitive testing | Low | Pre-defined test queries: "Summarize doc", "Compare docs A and B". |
| **Test Data Generator** | Auto-create test scenarios | Medium | Generate fake users, documents, queries for load testing. |
| **State Snapshot** | Save/restore UI state | Medium | Export st.session_state to JSON. Import to restore. |
| **Automated Test Scenarios** | Run test sequences | High | Define test flows (register → upload → query). Run automatically. |

#### Enhanced UX Features

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Sidebar Navigation** | Organize test features | Low | Use st.navigation or st.sidebar for page switching. |
| **Dark Mode** | Preference for developers | Low | Streamlit supports theme config. |
| **Keyboard Shortcuts** | Faster testing workflow | Medium | Limited in Streamlit. Use st.components for custom shortcuts. |
| **Export Test Results** | Save test session | Low | Export chat history, errors, metrics to JSON/CSV. |
| **Comparison View** | Side-by-side response testing | Medium | Show responses from different models/configs side-by-side. |

#### Advanced Debugging

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Backend Logs Viewer** | Debug server-side issues | High | Tail backend logs in UI. Requires backend log streaming endpoint. |
| **Token Counter** | Monitor API costs | Low | Count tokens in queries/responses. Estimate cost. |
| **Memory Inspector** | Visualize Mem0 state | High | Show graph/vector store contents. Requires backend inspection endpoint. |
| **Session Replay** | Reproduce bugs | High | Record all actions, replay them. Complex in Streamlit. |

---

### Anti-Features (Don't Build for Test UI)

Features that add complexity without improving testability.

#### Over-Polished UX

| Anti-Feature | Why Avoid | What to Do Instead | Severity |
|--------------|-----------|-------------------|----------|
| **Production-Grade Design** | Test UIs should be functional, not beautiful | Use default Streamlit components. Focus on functionality over aesthetics. | Low |
| **Responsive Mobile Layout** | Developers test on desktop | Design for desktop only. Mobile support is wasted effort. | Medium |
| **Custom CSS/Styling** | Maintenance burden for test tool | Stick to Streamlit defaults. Add minimal custom CSS if needed. | Low |
| **Animations/Transitions** | No value for testing | Use instant state changes. Skip loading animations unless testing them. | Low |
| **Marketing Copy** | Test tool, not product | Use technical labels. "POST /query" not "Ask Your Documents Anything". | Low |

#### Complexity Without Testing Value

| Anti-Feature | Why Avoid | What to Do Instead | Severity |
|--------------|-----------|-------------------|----------|
| **Real-Time Collaboration** | Not testing collaborative features | Single-user testing is sufficient. | High |
| **Offline Support** | Test UI requires backend connection | Always assume network. No service workers/caching. | Medium |
| **Advanced State Management** | Streamlit session state is sufficient | Don't add Redux/Zustand. Use st.session_state. | Medium |
| **Custom Component Library** | Maintenance overhead | Use built-in st.* components. Only custom if absolutely needed. | High |
| **Internationalization** | English-only for test tool | Don't add i18n. All text in English. | Low |

#### Testing Anti-Patterns

| Anti-Feature | Why Avoid | What to Do Instead | Severity |
|--------------|-----------|-------------------|----------|
| **Hiding Backend Errors** | Need to see what failed | Show full error messages, stack traces, status codes. | Critical |
| **Auto-Retry on Failure** | Masks intermittent issues | Fail fast. Show error. Let user manually retry. | High |
| **Mocking Backend Responses** | Defeats purpose of testing real backend | Always hit real backend. Use test environment if needed. | Critical |
| **Simplified Configuration** | Need access to all backend options | Expose all query parameters, headers, auth options. | High |
| **Input Validation** | Backend should validate | Don't validate on frontend. Test backend validation. | Medium |

#### Feature Bloat

| Anti-Feature | Why Avoid | What to Do Instead | Severity |
|--------------|-----------|-------------------|----------|
| **User Management UI** | Not testing user CRUD | Create test users via backend scripts. UI just tests login. | Medium |
| **Admin Dashboard** | Not a production tool | Basic admin features (add shared knowledge) only. | Medium |
| **Analytics/Metrics** | Not gathering product metrics | Simple per-session metrics only. No persistent analytics. | Low |
| **Payment Integration** | Not testing billing | Skip entirely for test UI. | N/A |
| **Email Notifications** | Not testing notifications | Skip. Test backend endpoints directly. | Low |

---

## Feature Dependencies

Understanding what features depend on others for Streamlit UI.

### Dependency Graph

```
Authentication (FOUNDATIONAL)
  ├─> Session State Management
  │     ├─> Token Storage
  │     ├─> User Info Display
  │     └─> Auth-Gated Features
  │           ├─> Document Upload
  │           ├─> Query Submission
  │           └─> Memory Management
  │
  └─> Anonymous Session (PARALLEL)
        └─> Anonymous-to-Auth Migration Testing

Document Management
  ├─> File Upload (FOUNDATIONAL)
  │     └─> Upload Progress
  │           └─> Processing Status
  │
  └─> Document List (FOUNDATIONAL)
        ├─> Document Selection
        │     └─> Query Context
        └─> Document Deletion

Query & Response
  ├─> Query Input (FOUNDATIONAL)
  │     ├─> Basic Text Response
  │     │     └─> Streaming Response
  │     │           └─> Citation Display
  │     │                 └─> Confidence Scores
  │     │
  │     └─> Chat History
  │           └─> Conversation Context
  │
  └─> Document Context Selection (PREREQUISITE)
        └─> Multi-Document Queries

Memory Features
  ├─> Personal Memory (FOUNDATIONAL)
  │     ├─> Add Facts
  │     └─> View Facts
  │
  └─> Shared Memory (ADVANCED)
        └─> Admin Role Check
              └─> Permission Testing

Testing Infrastructure
  ├─> Multi-User Testing (FOUNDATIONAL)
  │     ├─> User Switching
  │     └─> Isolation Verification
  │
  └─> Debugging Tools (PARALLEL)
        ├─> Request Inspector
        ├─> Error Display
        └─> Performance Metrics
```

### Critical Path for Test UI MVP

1. **Auth Foundation** → Login Form → Token Storage → Auth State Display
2. **Document Testing** → Upload Widget → Document List → Delete
3. **Query Testing** → Query Input → Basic Response → Streaming Display
4. **Citation Testing** → Citation Extraction → Display with Confidence
5. **Multi-User Testing** → User Switching → Isolation Verification
6. **Memory Testing** → Add Personal Fact → View Memory

---

## MVP Feature Recommendation

For a **Streamlit test UI to exercise FastAPI RAG backend**, build in phases:

### Phase 1: Authentication & Basic Navigation (Day 1-2)
**Goal:** Can login, see auth state, navigate between test areas.

1. Login form (email/password)
2. Registration form
3. Logout button
4. Auth state display (current user, role, token status)
5. Sidebar navigation (Auth, Documents, Query, Memory, Admin)
6. Session state management (persist auth across reruns)
7. Anonymous session support

### Phase 2: Document Upload & Management (Day 3-4)
**Goal:** Can upload documents, see list, delete.

1. File upload widget (PDF/DOCX)
2. Upload progress bar
3. Document list table (name, size, date, user)
4. Delete document button
5. Document summary view
6. Error handling for upload failures

### Phase 3: RAG Query & Streaming (Day 5-7)
**Goal:** Can ask questions, see streaming responses, citations.

1. Query input (text area)
2. Basic response display
3. **SSE streaming integration** (critical, complex)
4. Citation display (source, page, confidence)
5. Chat history display
6. Confidence score visualization
7. Simplification toggle

### Phase 4: Memory & Multi-User Testing (Day 8-9)
**Goal:** Can test memory APIs, verify user isolation.

1. Add personal fact form
2. View stored memories
3. Admin: Add shared knowledge (role-gated)
4. Multi-tab testing instructions
5. User switching (quick login as test users)
6. Isolation verification display
7. Anonymous → Auth migration test flow

### Phase 5: Debugging & Observability (Day 10)
**Goal:** Can debug issues, inspect requests/responses.

1. Request/response inspector (JSON display)
2. Error display (full messages)
3. API endpoint selector (localhost/staging)
4. Performance metrics (latency tracking)
5. Export test results (JSON download)

### Defer to Post-MVP
- Bulk document upload
- Test data generator
- Automated test scenarios
- Backend log viewer
- Memory inspector
- Session replay
- Token counter
- Comparison view

---

## Streamlit-Specific Implementation Notes

### Handling SSE Streaming

**Challenge:** Streamlit's rerun model conflicts with SSE streaming.

**Solution:**
```python
import sseclient
import requests
from typing import Generator

def stream_query(query: str, token: str) -> Generator[str, None, None]:
    """Stream SSE response from backend."""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(
        f"{API_URL}/query",
        json={"query": query},
        headers=headers,
        stream=True
    )
    client = sseclient.SSEClient(response)
    for event in client.events():
        yield event.data

# In UI:
placeholder = st.empty()
full_response = ""
for chunk in stream_query(query, st.session_state.token):
    full_response += chunk
    placeholder.markdown(full_response)
```

### Session State for Auth

**Pattern:**
```python
# Initialize session state
if "token" not in st.session_state:
    st.session_state.token = None
if "user" not in st.session_state:
    st.session_state.user = None

# Check auth
def is_authenticated():
    return st.session_state.token is not None

# Require auth
if not is_authenticated():
    st.warning("Please login first")
    st.stop()
```

### Multi-Page Navigation

**Recommended:** Use `st.navigation` (Streamlit 2026 feature).

```python
import streamlit as st

# Define pages
auth_page = st.Page("pages/auth.py", title="Authentication")
docs_page = st.Page("pages/documents.py", title="Documents")
query_page = st.Page("pages/query.py", title="Query")
memory_page = st.Page("pages/memory.py", title="Memory")
admin_page = st.Page("pages/admin.py", title="Admin")

# Conditional navigation based on auth
pages = [auth_page, docs_page, query_page, memory_page]
if st.session_state.get("user", {}).get("is_admin"):
    pages.append(admin_page)

pg = st.navigation(pages)
pg.run()
```

### File Upload with Progress

```python
uploaded_file = st.file_uploader("Upload PDF/DOCX", type=["pdf", "docx"])
if uploaded_file and st.button("Process"):
    progress_bar = st.progress(0)
    status_text = st.empty()

    # Upload with progress callback
    files = {"file": uploaded_file}
    headers = {"Authorization": f"Bearer {st.session_state.token}"}

    with requests.post(
        f"{API_URL}/documents/upload",
        files=files,
        headers=headers,
        stream=True
    ) as response:
        total = int(response.headers.get('content-length', 0))
        for i, chunk in enumerate(response.iter_content(chunk_size=8192)):
            progress = min(i * 8192 / total, 1.0)
            progress_bar.progress(progress)
            status_text.text(f"Uploading... {int(progress * 100)}%")

    st.success("Upload complete!")
```

### Request/Response Inspector

```python
with st.expander("🔍 Request/Response Inspector"):
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Request")
        st.json({
            "method": "POST",
            "url": f"{API_URL}/query",
            "headers": {"Authorization": "Bearer ***"},
            "body": {"query": query}
        })

    with col2:
        st.subheader("Response")
        st.json(response.json())

    st.text(f"⏱️ Latency: {response.elapsed.total_seconds():.2f}s")
```

---

## Complexity vs. Impact Matrix

Prioritize features by balancing implementation effort against testing value.

### High Impact, Low Complexity (DO FIRST)
- Login/logout/register forms
- Auth state display
- File upload widget
- Document list display
- Query input and basic response
- Citation display
- Error display (verbatim)
- Performance metrics

### High Impact, High Complexity (DO STRATEGICALLY)
- **SSE streaming response display** (critical for testing, complex to implement)
- Anonymous → Auth migration test flow
- Multi-user isolation verification
- Request/response inspector

### Low Impact, Low Complexity (DO WHEN CONVENIENT)
- Sidebar navigation
- Export test results
- Query templates
- Dark mode
- Token counter

### Low Impact, High Complexity (DON'T DO)
- Backend log viewer
- Memory inspector (graph visualization)
- Session replay
- Automated test scenarios
- Custom component library
- Real-time collaboration

---

## Project-Specific Testing Priorities

Given your backend features, prioritize testing:

### Critical Test Scenarios

1. **Multi-User Isolation**
   - Login as User A → Upload doc → Query
   - Login as User B → Verify can't see A's docs
   - **High priority:** Data leak prevention

2. **Anonymous → Auth Migration**
   - Use anonymous → Upload doc → Ask question
   - Register account
   - Verify: doc and conversation migrated
   - **High priority:** Unique feature to test

3. **Streaming RAG with Citations**
   - Submit query → Verify streaming starts <2s
   - Check citations appear with confidence scores
   - Verify citations link to correct source docs
   - **High priority:** Core product feature

4. **Memory Persistence**
   - Add personal fact → Ask related question
   - Verify LLM uses stored fact in answer
   - Admin: Add shared fact → Login as user → Verify access
   - **High priority:** Differentiating feature

5. **Document Comparison (GraphRAG)**
   - Upload 2+ docs → Ask comparison question
   - Verify answer draws from multiple docs
   - Check graph relationships used
   - **Medium priority:** Advanced feature

### Test UI Success Criteria

Test UI is successful if:
- [ ] Can verify all 24 backend features (from Active requirements)
- [ ] Multi-user isolation is testable (login as different users)
- [ ] Anonymous migration is testable (workflow visible)
- [ ] SSE streaming works (see tokens arrive in real-time)
- [ ] Citations display correctly (source + confidence)
- [ ] Errors surface clearly (not hidden)
- [ ] Can switch between test users quickly (<10s)
- [ ] Request/response debugging is easy (inspector shows all)

---

## Confidence Assessment & Sources

| Area | Confidence | Reasoning |
|------|------------|-----------|
| Streamlit Basics | HIGH | Official 2026 documentation, Context7 verified |
| FastAPI Integration | HIGH | Multiple 2026 guides, community patterns |
| SSE Streaming | MEDIUM | Workarounds exist but non-trivial in Streamlit |
| Multi-Page Apps | HIGH | st.navigation is official 2026 feature |
| Auth Patterns | HIGH | JWT with session state is well-documented |
| Test UI Patterns | MEDIUM-HIGH | Based on demo app patterns, not test-specific docs |

### Key Sources

**Streamlit + FastAPI Integration:**
- [From Backend To Frontend: Connecting FastAPI And Streamlit - Pybites](https://pybit.es/articles/from-backend-to-frontend-connecting-fastapi-and-streamlit/)
- [Serving a Machine Learning Model with FastAPI and Streamlit - TestDriven.io](https://testdriven.io/blog/fastapi-streamlit/)
- [Fastapi backend -> streamlit frontend? - Streamlit Community](https://discuss.streamlit.io/t/fastapi-backend-streamlit-frontend/55460)
- [Streamlit + FastAPI: The Python Duo - Towards Data Science](https://towardsdatascience.com/fastapi-and-streamlit-the-python-duo-you-must-know-about-72825def1243/)

**Streamlit 2026 Features:**
- [2026 release notes - Streamlit Docs](https://docs.streamlit.io/develop/quick-reference/release-notes/2026)
- [App design concepts and considerations - Streamlit Docs](https://docs.streamlit.io/develop/concepts/design)

**Session State & Authentication:**
- [Implement JWT Authentication for Streamlit - Medium](https://blog.yusufberki.net/implement-jwt-authentication-for-the-streamlit-application-2e3b0ef884ef)
- [streamlit-jwt-authenticator - PyPI](https://pypi.org/project/streamlit-jwt-authenticator/)
- [Streamlit-Authenticator, Part 1 - Streamlit Blog](https://blog.streamlit.io/streamlit-authenticator-part-1-adding-an-authentication-component-to-your-app/)
- [User authentication and information - Streamlit Docs](https://docs.streamlit.io/develop/concepts/connections/authentication)

**File Upload & Progress:**
- [File Upload and Download with Streamlit - DEV Community](https://dev.to/tsubasa_tech/file-upload-and-download-with-streamlit-in-snowflake-1joi)
- [Streamlit Upload File Guide - Kanaries](https://docs.kanaries.net/topics/Streamlit/streamlit-upload-file)

**SSE Streaming:**
- [FASTAPI-SSE-Event-Streaming-with-Streamlit - GitHub](https://github.com/sarthakkaushik/FASTAPI-SSE-Event-Streaming-with-Streamlit/blob/master/README.md)
- [Listening for updates from an API server - Streamlit Community](https://discuss.streamlit.io/t/listening-for-updates-from-an-api-server/48486)

**Multi-Page Apps:**
- [Multipage apps - Streamlit Docs](https://docs.streamlit.io/develop/concepts/multipage-apps)
- [st.navigation - Streamlit Docs](https://docs.streamlit.io/develop/api-reference/navigation/st.navigation)
- [Define multipage apps with st.Page and st.navigation](https://docs.streamlit.io/develop/concepts/multipage-apps/page-and-navigation)

**RAG Demo Patterns:**
- [8 Streamlit/Gradio Patterns to Demo AI - Medium](https://medium.com/@Nexumo_/8-streamlit-gradio-patterns-to-demo-ai-like-a-pro-f6a0c6114ff8)
- [RAG Based Conversational Chatbot Using Streamlit - Medium](https://medium.com/@mrcoffeeai/rag-based-conversational-chatbot-using-streamlit-364c4c02c2f1)
- [RAG and Streamlit Chatbot: Chat with Documents - Analytics Vidhya](https://www.analyticsvidhya.com/blog/2024/04/rag-and-streamlit-chatbot-chat-with-documents-using-llm/)

**Multi-User Testing:**
- [What is the best way to test web applications with multiple user roles?](https://www.linkedin.com/advice/0/what-best-way-test-web-applications-multiple-mg0hc)
- [How to Implement Multi-User Testing - Escape.tech](https://escape.tech/blog/multi-user-dast-testing-real-world-examples/amp/)

---

## Open Questions for Implementation

1. **SSE Streaming Reliability**: How robust is sseclient-py with Streamlit reruns? Does connection persist or need reconnect? (Test with prototype)

2. **File Upload Size Limits**: What's max file size Streamlit can handle? Does it conflict with FastAPI limits? (Check Streamlit docs, test with large files)

3. **Multi-Tab Session State**: When opening multiple tabs, does st.session_state isolate properly for multi-user testing? (Verify with test)

4. **Token Refresh Timing**: Should UI proactively refresh tokens before expiry, or reactively on 401? (Recommend proactive for better UX)

5. **Anonymous Session ID**: Should UI generate session ID or backend? (Recommend backend for consistency)

6. **Memory Inspector**: Is there value in visualizing Neo4j graph in test UI, or use Neo4j Browser directly? (Recommend Neo4j Browser, avoid complexity)

---

## Conclusion

**For Streamlit test UI to exercise FastAPI RAG backend:**

**Table Stakes (Must Have):**
- Login/register/logout forms with session state
- File upload with progress for documents
- Document list (verify user isolation)
- Query input with streaming response display
- Citation display with confidence scores
- Chat history (verify context persistence)
- Add personal/shared memory (test APIs)
- Error display (show backend errors verbatim)

**Differentiators (Testing Value-Add):**
- Request/response inspector (debug API calls)
- User switching (quick multi-user testing)
- Anonymous → Auth migration test flow
- Performance metrics (track latency)
- Export test results (save session data)

**Anti-Features (Don't Build):**
- Production-grade UI polish
- Custom CSS/styling (beyond basics)
- Mobile responsive design
- Hiding backend errors
- Input validation (test backend validation instead)
- User management UI (use backend scripts)

**Critical Success Factors:**
1. **SSE streaming works reliably** (core product feature)
2. **Multi-user isolation is easily testable** (security requirement)
3. **Errors surface clearly** (debugging requirement)
4. **Fast iteration** (test UI should be quick to modify)

**Recommended Timeline:** 10 days to functional test UI covering all 24 backend features. Focus on coverage over polish.
