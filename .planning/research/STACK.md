# Technology Stack: Streamlit Frontend

**Project:** RAG with Graph Store - Streamlit Test Frontend
**Researched:** 2026-02-05
**Confidence:** HIGH

## Recommended Stack

### Core Framework

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Streamlit | 1.54.0+ | Web UI framework | Latest stable release (Feb 4, 2026). Native multi-page apps, session state management, built-in file upload widgets. New st.App feature enables ASGI integration with FastAPI. Python 3.10+ required. |
| Python | 3.10+ | Runtime | Required by Streamlit 1.54.0. Matches backend compatibility. |

### HTTP Client & Communication

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| httpx | 0.28.1+ | HTTP client for API calls | Modern requests alternative with async/sync support, HTTP/2, familiar API. Outperforms requests (~20% faster). Better for both sync and async patterns needed for FastAPI integration. |
| sseclient-py | 1.7.2+ | SSE stream consumption | Pure-Python SSE client, seamlessly integrates with requests/httpx. Updated Jan 2, 2026. Handles FastAPI SSE streaming responses for real-time query tokens. |

### Authentication & Session Management

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| python-dotenv | 1.0.0+ | Environment variable management | Standard for loading API URLs and config from .env files. Works alongside Streamlit's secrets management. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pydantic | 2.7.0+ | Request/response validation | Optional but recommended - validate API responses match backend schemas. Reuse backend models if creating shared package. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| Streamlit Dev Tools | Live reloading | Built-in with `streamlit run --server.runOnSave true` |
| Browser DevTools | SSE stream inspection | Use Network tab to debug EventSource connections |

## Installation

```bash
# Core dependencies
pip install streamlit>=1.54.0
pip install httpx>=0.28.1
pip install sseclient-py>=1.7.2
pip install python-dotenv>=1.0.0

# Optional validation
pip install pydantic>=2.7.0

# Save to requirements.txt
cat > frontend/requirements.txt <<EOF
streamlit>=1.54.0
httpx>=0.28.1
sseclient-py>=1.7.2
python-dotenv>=1.0.0
pydantic>=2.7.0
EOF
```

## Architecture Integration Patterns

### JWT Authentication Flow

**DO NOT use streamlit-authenticator** - it manages its own user database. Your backend already handles auth.

**Recommended pattern:**
1. Store JWT tokens in `st.session_state` after login
2. Include tokens in Authorization header for all API calls
3. Handle token refresh before expiration
4. Clear session state on logout

```python
# Pattern for authenticated API calls
if "access_token" in st.session_state:
    headers = {"Authorization": f"Bearer {st.session_state.access_token}"}
    response = httpx.get(f"{API_URL}/endpoint", headers=headers)
```

### SSE Streaming Pattern

**Challenge:** Streamlit's synchronous execution model doesn't natively support SSE.

**Recommended pattern:**
1. Use `sseclient-py` with `httpx` streaming
2. Update UI incrementally using `st.empty()` containers
3. Handle disconnect gracefully

```python
# Pattern for consuming SSE streams
import sseclient
import httpx

placeholder = st.empty()
accumulated_text = ""

with httpx.stream("POST", f"{API_URL}/queries/stream",
                  json=payload, headers=headers) as response:
    client = sseclient.SSEClient(response)
    for event in client.events():
        if event.event == "token":
            accumulated_text += event.data
            placeholder.markdown(accumulated_text)
        elif event.event == "citations":
            # Handle citations
            pass
```

### Multi-Page App Structure

**Use st.navigation (preferred) over pages/ directory** for better control.

```
frontend/
├── app.py                    # Entrypoint with st.navigation
├── .env                      # API_URL, etc
├── requirements.txt
├── config.py                 # Shared config
├── api_client.py             # Centralized API calls with httpx
├── auth.py                   # Auth helpers (login, logout, token refresh)
└── pages/
    ├── 01_login.py           # Auth flows
    ├── 02_documents.py       # Upload, list, delete
    ├── 03_query.py           # Q&A with streaming
    ├── 04_comparison.py      # Document comparison
    ├── 05_memory.py          # Chat history
    └── 06_admin.py           # Admin features (role-gated)
```

### File Upload Pattern

**Streamlit uploads are in-memory BytesIO objects.**

```python
uploaded_file = st.file_uploader("Upload PDF/DOCX", type=["pdf", "docx"])
if uploaded_file:
    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
    response = httpx.post(f"{API_URL}/documents",
                          files=files,
                          headers=headers)
```

**Note:** Default limit is 200MB. Override with `st.file_uploader(..., max_file_size=500)` if needed (new in 2026).

## Alternatives Considered

| Category | Recommended | Alternative | When to Use Alternative |
|----------|-------------|-------------|-------------------------|
| HTTP Client | httpx | requests | If you only need synchronous calls and want absolute simplicity. httpx's async support future-proofs for potential async patterns. |
| SSE Client | sseclient-py | aiohttp-sse-client | If you fully commit to async/await patterns. sseclient-py works with both sync and async httpx. |
| Auth Pattern | Session state + JWT | streamlit-authenticator | NEVER for this project - it manages its own user DB and conflicts with FastAPI backend auth. |
| Multi-page | st.navigation | pages/ directory | pages/ is simpler but st.navigation gives better control over navigation logic, icons, and conditional pages (e.g., admin-only). |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| streamlit-authenticator | Manages its own user database, conflicts with FastAPI JWT auth. Creates duplicate authentication logic. | Direct JWT token storage in st.session_state with backend auth |
| requests library | Older sync-only library. Missing HTTP/2, slower than httpx. | httpx (20% faster, HTTP/2, async/sync support) |
| WebSocket for streaming | Backend uses SSE, not WebSocket. Mismatch creates unnecessary complexity. | sseclient-py for SSE consumption |
| Hardcoded API URLs | Makes environment switching (dev/prod) painful. | python-dotenv with .env files |
| Global state outside session_state | Shared across all users, breaks multi-user isolation. | Always use st.session_state for user-specific data |

## Stack Patterns by Use Case

**If building quick prototype (1-2 days):**
- Use pages/ directory for simplicity
- Skip pydantic validation
- Hardcode some UI elements

**If building maintainable demo (production-quality):**
- Use st.navigation with structured pages
- Add pydantic validation for API responses
- Centralize API client logic in api_client.py
- Add proper error handling and loading states
- Include token refresh logic

**If extending to production later:**
- Consider migrating to React/Next.js frontend
- Streamlit is excellent for demos but has limitations for complex production UIs
- Backend API is production-ready, frontend is test/demo layer

## Version Compatibility

| Frontend Package | Compatible Backend | Notes |
|------------------|-------------------|-------|
| streamlit>=1.54.0 | FastAPI 0.126.0+ | Backend uses SSE-starlette 2.0.0+ for streaming |
| httpx>=0.28.1 | Any HTTP/1.1, HTTP/2 server | Backend is HTTP/1.1 (FastAPI/Uvicorn default) |
| sseclient-py>=1.7.2 | SSE-starlette>=2.0.0 | Backend's EventSourceResponse compatible |
| pydantic>=2.7.0 | pydantic>=2.7.0 (backend) | MUST match major version for schema compatibility |

## Key Integration Points

### Backend Endpoints to Support

| Endpoint | Method | Frontend Need |
|----------|--------|---------------|
| `/api/v1/auth/register` | POST | Registration form |
| `/api/v1/auth/login` | POST | Login form (OAuth2PasswordRequestForm) |
| `/api/v1/auth/logout` | POST | Logout button |
| `/api/v1/auth/refresh` | POST | Token refresh before expiration |
| `/api/v1/documents` | POST, GET, DELETE | File upload, list, delete |
| `/api/v1/queries/stream` | POST | SSE streaming Q&A |
| `/api/v1/queries/enhanced` | POST | Enhanced query with confidence |
| `/api/v1/comparisons` | POST | Document comparison |
| `/api/v1/memory` | GET, POST | Memory management |
| `/api/v1/admin/*` | Various | Admin features (role-gated) |

### Environment Variables Needed

```bash
# .env file
API_BASE_URL=http://localhost:8000/api/v1
API_TIMEOUT=30
ENABLE_DEBUG=false
```

## 2026-Specific Features to Leverage

### New in Streamlit 1.54.0 (Jan 2026)

1. **st.App (Experimental)** - ASGI integration with FastAPI
   - **Use case:** Could embed Streamlit within FastAPI backend process
   - **Recommendation:** Skip for this milestone - adds complexity. Keep frontend/backend separate for clarity.

2. **OIDC token exposure** - `st.user.tokens`
   - **Use case:** If backend supported OIDC instead of JWT
   - **Recommendation:** Not applicable - backend uses custom JWT auth

3. **Enhanced file_uploader** - Per-widget size limits
   - **Use case:** Override 200MB default for large documents
   - **Recommendation:** Use if backend supports >200MB files

4. **st.logout** - Official logout function
   - **Use case:** Could replace manual session state clearing
   - **Recommendation:** Only if backend integrates OIDC provider. Current backend uses custom logout endpoint - call that instead.

## Performance Considerations

### API Call Optimization

1. **Cache repeated calls** - Use `@st.cache_data` for document lists if they don't change frequently
2. **Batch operations** - If deleting multiple documents, consider backend batch endpoint
3. **Lazy loading** - Don't fetch all documents on load, paginate or load on demand

### Session State Management

1. **Minimize state size** - Don't store large documents in session_state
2. **Clear unused state** - Clean up when navigating away from pages
3. **Token refresh** - Check token expiration before each API call, refresh proactively

### SSE Streaming

1. **Handle backpressure** - Don't update UI faster than 100ms intervals
2. **Disconnect detection** - Stop consuming stream if user navigates away
3. **Error recovery** - Provide retry button if stream fails

## Sources

**Official Documentation (HIGH confidence):**
- [Streamlit 2026 Release Notes](https://docs.streamlit.io/develop/quick-reference/release-notes/2026) - st.App, OIDC tokens, file_uploader improvements
- [Streamlit 1.54.0 PyPI](https://pypi.org/project/streamlit/) - Latest version, Python 3.10+ requirement
- [HTTPX 0.28.1 PyPI](https://pypi.org/project/httpx/) - Latest version, HTTP/2 support
- [Streamlit Multi-page Apps](https://docs.streamlit.io/develop/concepts/multipage-apps) - st.navigation best practices
- [Streamlit Session State](https://docs.streamlit.io/develop/concepts/architecture/session-state) - State management patterns
- [Streamlit File Uploader](https://docs.streamlit.io/develop/api-reference/widgets/st.file_uploader) - Upload widget API

**Community Resources (MEDIUM confidence):**
- [Pybites: FastAPI + Streamlit Integration](https://pybit.es/articles/from-backend-to-frontend-connecting-fastapi-and-streamlit/) - Client-server architecture patterns
- [Medium: Streamlit JWT Authentication](https://blog.yusufberki.net/implement-jwt-authentication-for-the-streamlit-application-2e3b0ef884ef) - Token storage patterns
- [Medium: LangGraph + Streamlit SSE](https://medium.com/@yigitbekir/bridging-langgraph-and-streamlit-a-practical-approach-to-streaming-graph-state-13db0999c80d) - SSE streaming patterns
- [sseclient-py PyPI](https://pypi.org/project/sseclient-py/) - SSE client library

**Ecosystem Research (MEDIUM confidence):**
- [Streamlit Discuss: FastAPI Backend](https://discuss.streamlit.io/t/fastapi-backend-streamlit-frontend/55460) - Integration patterns
- [ScrapingAnt: Requests vs HTTPX](https://scrapingant.com/blog/requests-vs-httpx) - HTTP client comparison
- [Oxylabs: HTTPX vs Requests vs AIOHTTP](https://oxylabs.io/blog/httpx-vs-requests-vs-aiohttp) - Performance benchmarks

---
*Stack research for: Streamlit Frontend for RAG with Graph Store*
*Researched: 2026-02-05*
*Focus: Integration with existing FastAPI backend (JWT auth, SSE streaming, multi-user isolation)*
