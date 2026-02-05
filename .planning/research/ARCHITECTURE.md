# Architecture Research: Streamlit Frontend Integration

**Domain:** Streamlit multi-page app consuming FastAPI backend
**Researched:** 2026-02-05
**Confidence:** HIGH

## Recommended Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Streamlit Frontend                               │
│                         (Port 8501)                                     │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                 │
│  │   app.py     │  │   pages/     │  │   utils/     │                 │
│  │  (Entrypoint)│  │  (Pages)     │  │ (API Client) │                 │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘                 │
│         │                  │                 │                          │
│         └──────────────────┴─────────────────┘                          │
│                            │                                            │
│                            │ HTTP/SSE Requests                          │
│                            ↓                                            │
├─────────────────────────────────────────────────────────────────────────┤
│                        FastAPI Backend                                  │
│                         (Port 8000)                                     │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐  ┌──────┐│
│  │ /auth  │  │ /docs  │  │ /query │  │/compare│  │/memory │  │/admin││
│  └────┬───┘  └────┬───┘  └────┬───┘  └────┬───┘  └────┬───┘  └───┬──┘│
│       │           │           │           │           │          │    │
├───────┴───────────┴───────────┴───────────┴───────────┴──────────┴────┤
│                        Data Layer                                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐               │
│  │  Neo4j   │  │  Qdrant  │  │  Redis   │  │PostgreSQL│               │
│  │ (Graph)  │  │ (Vector) │  │(Sessions)│  │(Workflow)│               │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘               │
└─────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|---------------|------------------------|
| app.py (Entrypoint) | Navigation menu, auth state management, common layout | st.navigation(), session state init, dynamic page routing |
| pages/*.py | Individual feature pages (login, docs, Q&A, etc.) | Streamlit UI components, calls to utils/api_client |
| utils/api_client.py | Centralized API communication with backend | requests.Session with token management, SSE handling |
| utils/auth.py | Authentication helpers (login, logout, check auth) | Token storage in session state, auth state helpers |
| utils/components.py | Reusable UI components | Custom widgets, common layouts, error displays |

## Recommended Project Structure

```
frontend/
├── app.py                    # Entrypoint with st.navigation
├── pages/                    # Multi-page app pages
│   ├── 01_login.py          # Login/register (anonymous or authenticated)
│   ├── 02_documents.py      # Document upload, list, delete
│   ├── 03_chat.py           # RAG Q&A with streaming
│   ├── 04_comparison.py     # Document comparison
│   ├── 05_memory.py         # Personal memory management
│   └── 06_admin.py          # Admin-only shared knowledge (conditional)
├── utils/                    # Business logic and API layer
│   ├── __init__.py
│   ├── api_client.py        # Centralized FastAPI client
│   ├── auth.py              # Auth state management helpers
│   ├── components.py        # Reusable UI components
│   └── streaming.py         # SSE streaming helpers
├── .streamlit/              # Streamlit configuration
│   └── config.toml          # Theme, server settings
├── requirements.txt         # Python dependencies
└── README.md                # Setup instructions
```

### Structure Rationale

- **app.py as frame:** Uses st.Page and st.navigation (preferred over pages/ directory) for maximum flexibility in conditional navigation based on auth state and roles
- **Numbered page prefixes:** Following Streamlit convention (01_*, 02_*) for logical ordering and better autocomplete
- **Centralized utils/:** Separates UI (pages) from business logic (utils), making code testable and maintainable
- **api_client.py singleton:** Single source of truth for backend communication, handles auth headers consistently across all pages

## Architectural Patterns

### Pattern 1: Centralized API Client with Session State

**What:** Single API client instance stored in st.session_state that manages authentication tokens and requests

**When to use:** All API communication (this is the recommended approach)

**Trade-offs:**
- Pros: DRY, consistent auth header management, token refresh in one place
- Cons: Session state resets on WebSocket disconnect (mitigated by st.query_params for token persistence)

**Example:**
```python
# utils/api_client.py
import requests
from typing import Optional
import streamlit as st

class APIClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()

    def set_auth_token(self, access_token: str):
        """Set JWT in Authorization header"""
        self.session.headers.update({
            "Authorization": f"Bearer {access_token}"
        })

    def clear_auth(self):
        """Remove auth headers"""
        self.session.headers.pop("Authorization", None)

    def post(self, endpoint: str, **kwargs):
        """POST request with error handling"""
        try:
            response = self.session.post(
                f"{self.base_url}{endpoint}",
                **kwargs
            )
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as e:
            st.error(f"API Error: {e.response.json().get('detail', str(e))}")
            return None

# Initialize in app.py
if 'api_client' not in st.session_state:
    st.session_state.api_client = APIClient()
```

### Pattern 2: Dynamic Navigation Based on Auth State

**What:** Build navigation menu dynamically using st.navigation with conditional page visibility based on user role

**When to use:** Multi-page apps with authentication and role-based access control

**Trade-offs:**
- Pros: Native Streamlit feature, clean UX, enforces access control at navigation level
- Cons: Must rebuild page dictionary on every rerun (minimal overhead)

**Example:**
```python
# app.py
import streamlit as st

# Initialize auth state
if 'role' not in st.session_state:
    st.session_state.role = None  # None = not logged in, 'user' or 'admin'

# Define all possible pages
login_page = st.Page("pages/01_login.py", title="Login", icon="🔐")
documents_page = st.Page("pages/02_documents.py", title="Documents", icon="📄")
chat_page = st.Page("pages/03_chat.py", title="Chat", icon="💬")
comparison_page = st.Page("pages/04_comparison.py", title="Compare", icon="🔍")
memory_page = st.Page("pages/05_memory.py", title="Memory", icon="🧠")
admin_page = st.Page("pages/06_admin.py", title="Admin", icon="⚙️")

# Build page dictionary based on role
page_dict = {}

if st.session_state.role is None:
    # Not logged in - show only login
    page_dict["Account"] = [login_page]
else:
    # Logged in - show main features
    page_dict["Account"] = [login_page]  # For logout
    page_dict["Features"] = [documents_page, chat_page, comparison_page, memory_page]

    # Admin-only pages
    if st.session_state.role == "admin":
        page_dict["Admin"] = [admin_page]

# Create navigation and run
pg = st.navigation(page_dict)
pg.run()
```

### Pattern 3: Token Persistence Across Reloads

**What:** Combine st.session_state (for runtime) with st.query_params (for reload persistence) to maintain authentication

**When to use:** Production apps where users expect to stay logged in across page refreshes

**Trade-offs:**
- Pros: Better UX, tokens survive WebSocket reconnection
- Cons: Tokens visible in URL (use short-lived tokens + refresh pattern), cleared on multi-page navigation

**Example:**
```python
# utils/auth.py
import streamlit as st
from datetime import datetime, timedelta

def init_auth_state():
    """Initialize auth state from query params or session state"""
    # Check query params first (persists across reload)
    if 'token' in st.query_params and 'access_token' not in st.session_state:
        # Restore from URL
        st.session_state.access_token = st.query_params['token']
        st.session_state.role = st.query_params.get('role', 'user')
        # Update API client
        st.session_state.api_client.set_auth_token(st.session_state.access_token)

    # Validate token hasn't expired (check expiry stored in session state)
    if 'token_expiry' in st.session_state:
        if datetime.now() > st.session_state.token_expiry:
            logout()

def login(access_token: str, refresh_token: str, role: str = "user"):
    """Store auth tokens and update UI state"""
    st.session_state.access_token = access_token
    st.session_state.refresh_token = refresh_token
    st.session_state.role = role
    st.session_state.token_expiry = datetime.now() + timedelta(minutes=15)

    # Persist in query params for reload
    st.query_params['token'] = access_token
    st.query_params['role'] = role

    # Update API client
    st.session_state.api_client.set_auth_token(access_token)

    st.rerun()  # Rebuild navigation

def logout():
    """Clear auth state"""
    # Clear session state
    st.session_state.pop('access_token', None)
    st.session_state.pop('refresh_token', None)
    st.session_state.pop('role', None)
    st.session_state.pop('token_expiry', None)

    # Clear query params
    st.query_params.clear()

    # Clear API client auth
    st.session_state.api_client.clear_auth()

    st.rerun()
```

### Pattern 4: SSE Streaming with st.write_stream

**What:** Consume FastAPI SSE (Server-Sent Events) endpoints using st.write_stream for typewriter-effect responses

**When to use:** Real-time streaming responses (LLM generation, document processing progress)

**Trade-offs:**
- Pros: Native Streamlit support, smooth UX, works with OpenAI-style streams
- Cons: Requires wrapper generator for custom SSE formats

**Example:**
```python
# utils/streaming.py
import requests
import json
from typing import Generator

def stream_query_response(api_client, query: str) -> Generator[str, None, None]:
    """Generator that yields chunks from FastAPI SSE endpoint"""
    response = api_client.session.post(
        f"{api_client.base_url}/api/v1/query/stream",
        json={"query": query},
        stream=True,
        headers={"Accept": "text/event-stream"}
    )

    for line in response.iter_lines():
        if line:
            decoded = line.decode('utf-8')
            # SSE format: "data: {json}\n\n"
            if decoded.startswith('data: '):
                data = json.loads(decoded[6:])
                if 'chunk' in data:
                    yield data['chunk']

# In pages/03_chat.py
import streamlit as st
from utils.streaming import stream_query_response

st.title("💬 Chat with Documents")

query = st.text_input("Ask a question:")
if st.button("Send") and query:
    # Stream response with typewriter effect
    response = st.write_stream(
        stream_query_response(st.session_state.api_client, query)
    )

    # Response is accumulated string, can store in history
    st.session_state.messages.append({
        "role": "assistant",
        "content": response
    })
```

### Pattern 5: Progress Tracking for Document Upload

**What:** Poll backend task status endpoint and display progress using st.progress and st.status

**When to use:** Long-running background tasks (document processing, comparison workflows)

**Trade-offs:**
- Pros: Native progress UI, good UX feedback
- Cons: Polling overhead (mitigate with reasonable intervals)

**Example:**
```python
# In pages/02_documents.py
import streamlit as st
import time

uploaded_file = st.file_uploader("Upload document", type=["pdf", "docx"])
if uploaded_file:
    # Upload file
    files = {"file": (uploaded_file.name, uploaded_file, uploaded_file.type)}
    response = st.session_state.api_client.post("/api/v1/documents/upload", files=files)

    if response:
        task_id = response['task_id']

        # Poll for status with progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()

        while True:
            status_response = st.session_state.api_client.get(
                f"/api/v1/documents/{task_id}/status"
            )

            if status_response:
                progress = status_response['progress']
                stage = status_response['stage']

                progress_bar.progress(progress / 100)
                status_text.text(f"Status: {stage}")

                if status_response['status'] == 'completed':
                    st.success("Document processed successfully!")
                    break
                elif status_response['status'] == 'failed':
                    st.error(f"Processing failed: {status_response.get('error')}")
                    break

            time.sleep(1)  # Poll every second
```

## Data Flow

### Authentication Flow

```
User (Streamlit) → POST /api/v1/auth/login → FastAPI
                 ← {access_token, refresh_token}

Store in st.session_state:
- access_token (for API calls)
- refresh_token (for token renewal)
- role (for navigation)

Update st.query_params:
- token=<access_token>
- role=<role>

Set API client Authorization header:
- Authorization: Bearer <access_token>

Call st.rerun() → Rebuild navigation with new role
```

### Query Flow with Streaming

```
User types query → pages/03_chat.py
                 ↓
utils/streaming.stream_query_response()
                 ↓
POST /api/v1/query/stream (SSE)
                 ↓
FastAPI streams chunks → Generator yields chunks
                 ↓
st.write_stream() → Typewriter display
                 ↓
Store final response in st.session_state.messages
```

### Document Upload Flow

```
User uploads file → pages/02_documents.py
                  ↓
POST /api/v1/documents/upload
                  ↓
FastAPI returns {task_id}
                  ↓
Poll GET /api/v1/documents/{task_id}/status
                  ↓
Update st.progress() based on status
                  ↓
On completion → Refresh document list
```

### Key Data Flows

1. **Auth State Propagation:** Login → session_state → query_params → API client → All pages
2. **Role-Based Navigation:** session_state.role → page_dict building → st.navigation → Visible pages
3. **API Token Management:** session_state.access_token → API client headers → All backend requests

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 1-10 users | Current architecture sufficient; single Streamlit instance with direct backend calls |
| 10-100 users | Add connection pooling in api_client.py; consider caching frequently accessed data with @st.cache_data |
| 100-1000 users | Deploy multiple Streamlit instances behind load balancer; use st.cache_resource for shared connections; implement request timeout handling |
| 1000+ users | Consider Streamlit Community Cloud or containerized deployment; optimize with component-level caching; add CDN for static assets |

### Scaling Priorities

1. **First bottleneck:** Session state memory usage with many concurrent users
   - **Fix:** Use st.cache_resource for shared objects (API client can be global), limit session state to user-specific data only

2. **Second bottleneck:** SSE connection limits
   - **Fix:** Implement connection pooling, add timeout handling, consider WebSocket alternative for high-concurrency scenarios

## Anti-Patterns

### Anti-Pattern 1: Per-Page API Client Creation

**What people do:** Create new API client instance in each page file

```python
# BAD: In every page
import requests
response = requests.post("http://localhost:8000/api/v1/query", ...)
```

**Why it's wrong:**
- No centralized auth header management
- Token updates require changes in multiple files
- Cannot reuse connections (performance hit)
- Inconsistent error handling

**Do this instead:** Use centralized api_client from session state

```python
# GOOD: In every page
response = st.session_state.api_client.post("/api/v1/query", ...)
```

### Anti-Pattern 2: Storing Sensitive Tokens in Query Params Long-Term

**What people do:** Keep full JWT in URL indefinitely via st.query_params

**Why it's wrong:**
- Tokens visible in browser history and server logs
- URL sharing exposes credentials
- XSS vulnerability if tokens are long-lived

**Do this instead:** Use query params only for initial load, then clear; rely on session state during session; use short-lived access tokens with refresh token pattern

```python
# GOOD
def init_auth_state():
    if 'token' in st.query_params and 'access_token' not in st.session_state:
        st.session_state.access_token = st.query_params['token']
        st.query_params.clear()  # Clear immediately after reading
```

### Anti-Pattern 3: Using pages/ Directory for Complex Auth

**What people do:** Use automatic pages/ directory with auth checks inside each page

**Why it's wrong:**
- Pages appear in navigation even when user shouldn't access them
- Requires duplicate auth checks in every page
- Poor UX (users see pages they can't use)

**Do this instead:** Use st.navigation with dynamic page building

```python
# GOOD: Only show pages user can access
page_dict = {}
if st.session_state.role == "admin":
    page_dict["Admin"] = [admin_page]
# Page never appears for non-admin users
```

### Anti-Pattern 4: Polling Without Debouncing

**What people do:** Poll status endpoints in tight loop without rate limiting

```python
# BAD
while True:
    check_status()
    # No delay - hammers backend
```

**Why it's wrong:**
- Unnecessary backend load
- Poor user experience (constant UI updates)
- Can hit rate limits

**Do this instead:** Use reasonable polling intervals with time.sleep()

```python
# GOOD
while not complete:
    status = check_status()
    time.sleep(2)  # Poll every 2 seconds
```

### Anti-Pattern 5: Session State for Global Config

**What people do:** Store API base URL, app settings in st.session_state

**Why it's wrong:**
- Session state is per-user (wasteful for shared config)
- Duplicated across all sessions
- Doesn't persist across WebSocket reconnects

**Do this instead:** Use module-level constants or st.cache_resource for shared config

```python
# GOOD
# config.py
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

@st.cache_resource
def get_shared_config():
    return {
        "api_url": API_BASE_URL,
        "theme": "dark"
    }
```

## Integration Points

### Backend API Integration

| Backend Endpoint | Frontend Integration Pattern | Notes |
|------------------|------------------------------|-------|
| POST /api/v1/auth/login | api_client.post() → store tokens in session_state | Use OAuth2PasswordRequestForm format (username, password) |
| POST /api/v1/auth/register | api_client.post() → auto-login with returned tokens | Migrate anonymous session if exists |
| POST /api/v1/documents/upload | multipart/form-data file upload → poll status | Use st.file_uploader for file, then api_client.post with files= |
| GET /api/v1/documents | api_client.get() → display in st.dataframe or st.table | Cache with @st.cache_data(ttl=60) for performance |
| DELETE /api/v1/documents/{id} | api_client.delete() → refresh list | Show confirmation dialog with st.dialog |
| POST /api/v1/query/stream | SSE streaming → st.write_stream | Use utils/streaming.py generator wrapper |
| POST /api/v1/compare | api_client.post() → display results | Long-running, consider polling status similar to upload |
| GET /api/v1/memory/personal | api_client.get() → display memories | Show in expandable sections with st.expander |
| POST /api/v1/memory/personal | api_client.post() → add memory | Simple form with st.text_input |
| GET /api/v1/admin/shared-memory | api_client.get() → admin page only | Check role before showing page |
| POST /api/v1/admin/shared-memory | api_client.post() → admin page only | Restrict via navigation, double-check on backend |

### Session Management

| Requirement | Implementation | Notes |
|-------------|----------------|-------|
| Persist auth across page nav | st.session_state + st.query_params | Query params cleared on multi-page navigation (Streamlit limitation) |
| Anonymous sessions | Cookie-based session ID from backend → store in session_state | Backend returns anon_session_id in response |
| Refresh token rotation | Store refresh_token in session_state → call /refresh before access_token expires | Implement token expiry check in api_client |
| Role-based UI | st.session_state.role → conditional page building | Update role on login/register response |

## Build Order (Dependency-Based)

### Wave 1: Foundation (Start here)
**Goal:** Basic app structure, auth, API client

1. **Setup project structure** (app.py, utils/, pages/, requirements.txt)
   - Install dependencies: streamlit, requests, python-dotenv
   - Create .streamlit/config.toml for theme

2. **Build utils/api_client.py** (centralized backend communication)
   - APIClient class with requests.Session
   - Methods: post(), get(), delete(), set_auth_token(), clear_auth()

3. **Build utils/auth.py** (auth state helpers)
   - init_auth_state(), login(), logout()
   - Session state initialization

4. **Build pages/01_login.py** (login/register page)
   - Login form → POST /api/v1/auth/login
   - Register form → POST /api/v1/auth/register
   - Anonymous session support (backend handles)

5. **Build app.py** (navigation entrypoint)
   - Initialize session state (api_client, auth state)
   - Dynamic navigation with role-based page building
   - Run navigation

**Deliverable:** Users can login/register, navigation menu appears

### Wave 2: Core Features (Documents + Chat)
**Goal:** Main user-facing functionality

6. **Build pages/02_documents.py** (document management)
   - File uploader → POST /api/v1/documents/upload
   - Progress polling → GET /api/v1/documents/{task_id}/status
   - Document list → GET /api/v1/documents
   - Delete button → DELETE /api/v1/documents/{id}

7. **Build utils/streaming.py** (SSE stream helpers)
   - stream_query_response() generator wrapper

8. **Build pages/03_chat.py** (RAG Q&A)
   - Query input → POST /api/v1/query/stream (SSE)
   - st.write_stream for typewriter effect
   - Display citations with st.expander
   - Conversation history in session state

**Deliverable:** Users can upload docs, ask questions, see streaming responses

### Wave 3: Advanced Features (Comparison + Memory)
**Goal:** Differentiation features

9. **Build pages/04_comparison.py** (document comparison)
   - Multi-select documents → POST /api/v1/compare
   - Display comparison results with citations
   - Handle long-running comparison (progress indicator)

10. **Build pages/05_memory.py** (personal memory)
    - List memories → GET /api/v1/memory/personal
    - Add memory form → POST /api/v1/memory/personal
    - Display in organized sections

**Deliverable:** Users can compare docs, manage personal memory

### Wave 4: Admin Features (Conditional)
**Goal:** Admin-only shared knowledge

11. **Build pages/06_admin.py** (admin panel)
    - Conditional in navigation (only if role=admin)
    - Shared memory management → GET/POST /api/v1/admin/shared-memory
    - Display shared knowledge facts

**Deliverable:** Admins can manage shared knowledge base

### Wave 5: Polish (UX enhancements)
**Goal:** Production-ready UX

12. **Build utils/components.py** (reusable UI components)
    - error_display(), success_display()
    - citation_card(), document_card()
    - loading_spinner()

13. **Add error handling** (throughout)
    - api_client error responses → st.error displays
    - Network failures → retry logic or user guidance
    - Token refresh on 401 responses

14. **Add caching** (performance optimization)
    - @st.cache_data for document lists
    - @st.cache_resource for API client
    - Session-scoped caching where appropriate

**Deliverable:** Polished, production-ready UI with good error handling

## Sources

### Official Streamlit Documentation (HIGH Confidence)
- [Multipage apps overview](https://docs.streamlit.io/develop/concepts/multipage-apps)
- [st.Page and st.navigation (preferred approach)](https://docs.streamlit.io/develop/concepts/multipage-apps/page-and-navigation)
- [Session State API](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.session_state)
- [st.query_params for URL parameters](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.query_params)
- [st.write_stream for streaming content](https://docs.streamlit.io/develop/api-reference/write-magic/st.write_stream)
- [Dynamic navigation tutorial](https://docs.streamlit.io/develop/tutorials/multipage/dynamic-navigation)
- [User authentication concepts](https://docs.streamlit.io/develop/concepts/connections/authentication)

### Streamlit 2026 Release Notes (HIGH Confidence)
- [2026 release notes](https://docs.streamlit.io/develop/quick-reference/release-notes/2026) - st.App ASGI entry point, st.user.tokens for OIDC, session-scoped caching

### Community Patterns and Integration Examples (MEDIUM Confidence)
- [Streamlit + FastAPI integration patterns](https://pybit.es/articles/from-backend-to-frontend-connecting-fastapi-and-streamlit/)
- [FastAPI SSE streaming with Streamlit](https://github.com/sarthakkaushik/FASTAPI-SSE-Event-Streaming-with-Streamlit)
- [Project structure for medium/large apps](https://discuss.streamlit.io/t/project-structure-for-medium-and-large-apps-full-example-ui-and-logic-splitted/59967)
- [JWT authentication implementation](https://blog.yusufberki.net/implement-jwt-authentication-for-the-streamlit-application-2e3b0ef884ef)
- [Best practices for GenAI apps](https://blog.streamlit.io/best-practices-for-building-genai-apps-with-streamlit/)
- [Role-based authentication discussion](https://discuss.streamlit.io/t/role-based-authentication/36598)

### Third-Party Libraries (MEDIUM Confidence)
- [streamlit-authenticator](https://github.com/mkhorasani/Streamlit-Authenticator) - Community auth library (not used in this project, but patterns referenced)
- [sse-starlette](https://pypi.org/project/sse-starlette/) - FastAPI SSE support library

---
*Architecture research for: Streamlit frontend integration with FastAPI backend*
*Researched: 2026-02-05*
