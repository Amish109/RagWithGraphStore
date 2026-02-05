# Pitfalls Research: Streamlit Frontend for FastAPI Backend

**Domain:** Streamlit + FastAPI integration with JWT auth and SSE streaming
**Researched:** 2026-02-05
**Confidence:** HIGH

## Critical Pitfalls

### Pitfall 1: JWT Token Lost on Browser Refresh

**What goes wrong:**
JWT tokens stored in `st.session_state` disappear when users refresh their browser, logging them out unexpectedly. Session state exists only "as long as the tab is open and connected to the Streamlit server" and is not persisted across page refreshes that disconnect the session.

**Why it happens:**
Developers assume `st.session_state` provides persistence like localStorage, but it only survives script reruns within the same connection. Browser refresh creates a new session with blank state.

**How to avoid:**
Use HTTP-only cookies for JWT token storage. FastAPI backend sets tokens in secure, same-site cookies that Streamlit can read via cookie managers like `streamlit-cookies-manager` or `extra-streamlit-components`. The cookie persists across refreshes while session state does not.

**Warning signs:**
- Users report being "logged out" when refreshing
- Authentication state works during navigation but fails on F5/refresh
- Token exists in session state but no cookie backup mechanism

**Phase to address:**
Early authentication implementation phase. Token persistence must be designed from the start as retrofitting is architecturally disruptive.

---

### Pitfall 2: Infinite Rerun Loop in Authentication Flow

**What goes wrong:**
Authentication logic with `st.rerun()` creates infinite loops where the script continuously reruns without user control. The app becomes unresponsive and may crash.

**Why it happens:**
Calling `st.rerun()` inside button handlers without proper state guards causes the button to remain "pressed" across reruns. Streamlit buttons return `True` only on the click rerun, then immediately `False`, but if `st.rerun()` executes before state updates, the condition repeats indefinitely.

**How to avoid:**
1. Use session state flags instead of direct button checks: set `st.session_state.authenticated = True` in callback, check flag for rendering
2. Use callbacks on buttons rather than inline `st.rerun()` calls
3. Add state guards: `if not st.session_state.get('auth_in_progress', False)` before triggering rerun
4. Never call `st.rerun()` unconditionally in authentication handlers

**Warning signs:**
- App freezes on login/logout button clicks
- Console shows rapid repeated script executions
- CPU usage spikes when authentication triggers
- Error: "infinite looping may crash your app"

**Phase to address:**
Initial authentication UI implementation. Must establish proper state management patterns before building complex flows.

---

### Pitfall 3: SSE Streaming Buffered Instead of Real-Time

**What goes wrong:**
SSE responses from FastAPI appear all at once after completion rather than streaming incrementally. Users see no progress indication despite streaming being implemented on backend.

**Why it happens:**
Middleware, proxies, or app servers buffer responses until the route handler completes. For Streamlit specifically, using standard HTTP clients without proper SSE handling causes chunk buffering. Additionally, `st.write_stream()` expects Python generators/iterables, not raw SSE EventSource connections.

**How to avoid:**
1. Use `sseclient-py` library to consume SSE streams from FastAPI endpoints
2. Convert SSE stream to Python generator before passing to `st.write_stream()`
3. On FastAPI side, ensure `StreamingResponse` with `media_type="text/event-stream"` and proper chunk yielding
4. Disable buffering in deployment proxies (nginx `X-Accel-Buffering: no`, Cloudflare stream mode)
5. Use small chunk sizes and explicit flush on backend

**Warning signs:**
- Streaming works in curl/browser EventSource but not in Streamlit
- Progress indicators don't update during generation
- All content appears simultaneously after long wait
- Network tab shows data arriving incrementally but UI doesn't update

**Phase to address:**
Streaming implementation phase. Requires proper generator wrapping patterns established early.

---

### Pitfall 4: Anonymous Session Data Orphaned Without Migration

**What goes wrong:**
Users create content (upload docs, ask questions) as anonymous users, then register. Their previous work disappears because anonymous session ID doesn't migrate to authenticated user account. Users lose trust and abandon the app.

**Why it happens:**
Cookie-based anonymous sessions use temporary IDs. After authentication, new session starts with new user ID. Without explicit data migration logic, documents/memories remain tied to old anonymous ID in both Neo4j and Qdrant, unreachable by new authenticated identity.

**How to avoid:**
1. Store anonymous session ID in both session state AND HTTP-only cookie for persistence
2. On registration/login, check for `anonymous_session_id` cookie
3. Backend migration endpoint: query Neo4j/Qdrant for documents with `anonymous_session_id`, update to `authenticated_user_id`
4. Handle race conditions: lock during migration, prevent concurrent document operations
5. Log migration success/failure for debugging orphaned data
6. Implement cleanup job: TTL-based deletion of unmigrated anonymous data after configurable period (e.g., 30 days)

**Warning signs:**
- User uploads documents anonymously, then registers and sees empty document list
- Support requests about "lost documents after signing up"
- Database contains documents with orphaned anonymous session IDs
- Memory service shows conversation history for anonymous IDs but not after auth

**Phase to address:**
Multi-user isolation phase when anonymous sessions are introduced. Migration logic must be atomic and part of authentication flow.

---

### Pitfall 5: File Upload Fails with 422 Unprocessable Entity

**What goes wrong:**
Uploading files from Streamlit's `st.file_uploader()` to FastAPI backend returns 422 error. Request fails validation despite file being successfully read in Streamlit.

**Why it happens:**
`st.file_uploader()` returns `UploadedFile` object (BytesIO wrapper), not raw bytes. Sending this directly to FastAPI without proper multipart encoding causes type mismatch. FastAPI expects `UploadFile` or proper `multipart/form-data` formatting.

**How to avoid:**
```python
# WRONG: Direct file object
files = {"file": uploaded_file}
response = requests.post(f"{API_URL}/upload", files=files)

# CORRECT: Proper multipart encoding
files = {
    "file": (
        uploaded_file.name,  # filename
        uploaded_file.getvalue(),  # bytes
        uploaded_file.type  # mime type
    )
}
response = requests.post(f"{API_URL}/upload", files=files)

# OR use requests-toolbelt for complex multipart
from requests_toolbelt.multipart.encoder import MultipartEncoder
m = MultipartEncoder(fields={
    'file': (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)
})
response = requests.post(
    f"{API_URL}/upload",
    data=m,
    headers={'Content-Type': m.content_type}
)
```

FastAPI backend must install `python-multipart` and use `File(...)` or `UploadFile` parameter.

**Warning signs:**
- 422 errors on file upload with validation error about file field
- File uploads work with curl/Postman but fail from Streamlit
- Backend logs show missing or malformed file in request

**Phase to address:**
Document upload implementation phase. File handling patterns should be tested with real FastAPI integration immediately.

---

### Pitfall 6: Session State Pickle Vulnerability with Untrusted JWT Data

**What goes wrong:**
Streamlit uses `pickle` module internally for session state serialization. Storing JWT claims or user-provided data directly in session state creates arbitrary code execution vulnerability if attacker crafts malicious pickle data.

**Why it happens:**
Developers treat session state like a secure store without realizing pickle deserialization can execute arbitrary code. JWT claims from external auth providers may contain untrusted data that gets pickled.

**How to avoid:**
1. **Validate and sanitize** all JWT claims before storing in session state
2. Store only primitive types (str, int, bool, dict with primitive values) in session state
3. Never store raw JWT tokens in session state - only parsed, validated claims
4. Use separate secure storage (Redis, encrypted cookies) for sensitive authentication data
5. Implement input validation: whitelist allowed characters in user-provided fields
6. Consider using `st.secrets` for truly sensitive values instead of session state

**Warning signs:**
- Storing complex objects or raw serialized data in session state
- No validation on JWT claims before storage
- Storing entire JWT token payload without parsing
- Security scanner flags pickle usage in authentication flow

**Phase to address:**
Initial authentication phase. Security patterns must be established before handling user data.

---

### Pitfall 7: Async/Await in Streamlit Causes Event Loop Conflicts

**What goes wrong:**
Using `asyncio.run()` or `await` directly in Streamlit code causes "RuntimeError: Event loop is already running" or "This event loop is already running" errors. Async FastAPI client code fails unexpectedly.

**Why it happens:**
Streamlit runs inside Tornado's event loop. Calling `asyncio.run()` attempts to create a new event loop, conflicting with the existing one. Direct `await` calls fail because Streamlit functions aren't async contexts.

**How to avoid:**
1. Use synchronous HTTP clients (`requests`, not `httpx` async)
2. If async required, use `asyncio.create_task()` and `asyncio.gather()` within existing loop
3. For background tasks, use Streamlit's connection pooling or run in thread executor
4. FastAPI backend should be async, but Streamlit frontend should use sync API calls
5. If consuming async generators (SSE), convert to sync generator:
```python
import asyncio
def sync_generator(async_gen):
    loop = asyncio.new_event_loop()
    try:
        while True:
            yield loop.run_until_complete(async_gen.__anext__())
    except StopAsyncIteration:
        pass
    finally:
        loop.close()
```

**Warning signs:**
- RuntimeError about event loops when calling FastAPI endpoints
- Async/await syntax in `.py` files containing Streamlit code
- Using `httpx.AsyncClient` instead of `httpx.Client` or `requests`
- SSE client libraries designed for async contexts

**Phase to address:**
Initial API integration phase. Establish sync-only pattern for Streamlit frontend before building complex features.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Storing JWT in session state without cookies | Fast implementation, no cookie lib needed | Users logged out on refresh, poor UX | Never - undermines authentication reliability |
| Using `st.rerun()` in button handlers without callbacks | Direct control flow, intuitive logic | Infinite loops, brittle authentication flows | Never - callbacks are the correct pattern |
| Synchronous blocking calls to FastAPI for slow operations | Simple request/response code | UI freezes during processing, poor UX | Only for quick operations <500ms |
| Global session state variables without user prefixing | Easy to access, no namespacing needed | Multi-tab conflicts, state leakage between users | Never for multi-user apps |
| Skipping file upload multipart encoding | Seems to work with simple files | Random 422 errors, fails with certain file types | Never - proper encoding required |
| Storing entire API responses in session state | Caching avoids repeated API calls | Session state bloat, pickle vulnerabilities | Use `@st.cache_data` instead with TTL |
| Testing only in development without real auth flow | Faster iteration during development | Auth bugs surface only in production | Only in early prototyping, must test before deployment |

## Integration Gotchas

Common mistakes when connecting to FastAPI backend.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| JWT Authentication | Token in session state only, no cookie backup | Token in HTTP-only cookie + session state read for convenience |
| SSE Streaming | Using requests.get() which doesn't stream chunks | Use sseclient-py with generator wrapping for st.write_stream() |
| File Uploads | Passing UploadedFile object directly | Extract bytes with getvalue(), format as multipart with filename/type |
| CORS | Forgetting to allow credentials in CORS config | FastAPI: allow_credentials=True, Streamlit: withCredentials in requests |
| Anonymous Sessions | No backend session concept, only Streamlit state | Backend issues session ID in cookie, Streamlit reads and includes in headers |
| API Error Handling | Displaying raw error JSON to users | Parse error response, show friendly message, log details for debugging |
| Token Refresh | Manual refresh button or page reload required | Background refresh with httpx client, check expiry before each API call |
| Progress Tracking | Polling backend with st.rerun() in loop | SSE endpoint for real-time updates, or task ID with status endpoint |

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Session state bloat from caching API responses | Slow page loads, memory errors | Use @st.cache_data with TTL, store only IDs not full objects | >100KB session state per user |
| Rerunning entire script for small updates | Laggy interactions, high CPU | Use st.fragment for isolated reruns, callbacks for state updates | Apps with >500 lines or heavy processing |
| Synchronous API calls blocking UI thread | App freezes during backend operations | Async patterns (careful with event loop), or progress indicators + st.rerun | API calls >1 second |
| No request timeouts on FastAPI calls | Indefinite hangs if backend is slow/down | Set requests timeout (3-30s), show error after timeout | Any production deployment |
| Loading all documents/history on page load | Slow initial load, poor time-to-interactive | Pagination, lazy loading with "Load More" | >50 items to display |
| Polling for updates with aggressive st.rerun() | High server load, poor scalability | SSE for real-time updates, websockets for bidirectional | >10 concurrent users |
| Unoptimized image/file display in document list | Memory issues, browser crashes | Use thumbnails, lazy-load full images, limit resolution | >20 images/files visible |

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| Storing JWT in session state without validation | Pickle deserialization RCE | Validate/sanitize claims, store only primitives |
| Anonymous session ID in Streamlit state only | Session fixation, ID predictability | Backend-generated UUID in HTTP-only cookie |
| No CSRF protection on state-changing operations | CSRF attacks on document uploads/deletions | Use FastAPI CSRF tokens, verify origin header |
| Exposing API keys in Streamlit code | Key leakage in client-side code | Use st.secrets, pass only session tokens to client |
| No rate limiting on API calls from frontend | DoS from single malicious user | Backend rate limiting by session ID or IP |
| Trusting client-side role checks | Privilege escalation by modifying session state | Backend validates JWT roles on every request |
| Cookies without Secure/SameSite flags | Session hijacking, CSRF | Set Secure, HttpOnly, SameSite=Lax on all cookies |
| File upload without type/size validation | Malicious file upload, storage exhaustion | Validate on backend: whitelist extensions, size limits |

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| No loading indicator during streaming | Users think app is frozen, refresh page | Show spinner, then progressive display with st.write_stream |
| Login form re-displays on every rerun during auth | Flashing UI, looks broken | Use session state flag to hide form after submission until response |
| Error messages show stack traces or API errors | Confusion, lack of trust | Parse errors, show user-friendly messages, log details server-side |
| Anonymous users unaware data will be lost | Surprise when data disappears, lost work | Banner: "Sign up to save your work" with clear migration promise |
| No feedback when file upload completes | Uncertainty about success, duplicate uploads | Progress bar during upload, success message with document name |
| Streaming text appears then disappears | Confusing, looks like bug | Use st.empty() container, update in place without clearing |
| Logout doesn't visually reset to login screen | Users unsure if logout worked | Clear all session state, explicit st.rerun() to show login |
| Admin features visible but disabled for regular users | Frustration, looks like broken features | Conditionally render admin UI only if admin role, don't show disabled |

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Authentication:** Looks working in single tab, but test multi-tab behavior - both tabs should share auth state via cookies
- [ ] **JWT Expiry:** Login works, but verify token refresh logic when token expires mid-session
- [ ] **SSE Streaming:** Text streams in dev, but verify no buffering in production with nginx/cloudflare proxy
- [ ] **File Upload:** PDFs work, but test DOCX, large files (>10MB), special characters in filenames
- [ ] **Error Handling:** API returns 401, but verify Streamlit doesn't crash - should show login prompt
- [ ] **Anonymous Migration:** Registration succeeds, but verify documents actually migrated with backend query
- [ ] **Session Cleanup:** TTL configured, but verify cleanup job actually runs and removes data from Neo4j + Qdrant
- [ ] **Multi-User Isolation:** Users see their own documents, but verify concurrent operations don't cause race conditions
- [ ] **Role-Based Access:** Admin UI appears, but verify backend enforces role checks on API endpoints
- [ ] **Token Storage:** Auth works, but verify tokens are in HTTP-only cookies, not localStorage or session state only

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Token lost on refresh | LOW | Implement cookie storage, migrate existing users with re-login banner |
| Infinite rerun loop | LOW | Add state guard flag, refactor to callback pattern |
| SSE buffering | MEDIUM | Add sseclient-py wrapper, update generator pattern, configure proxy |
| Orphaned anonymous data | HIGH | Write migration script to match anonymous docs to users by timestamp/IP, manual review |
| File upload broken | LOW | Add proper multipart encoding, test with all supported file types |
| Pickle vulnerability exploited | HIGH | Audit all session state usage, sanitize existing data, add validation, security review |
| Event loop conflicts | MEDIUM | Remove all async code from Streamlit, convert to sync with thread executors |
| Session state bloat | MEDIUM | Implement cache clearing, add TTL to large objects, use external cache (Redis) |
| No CSRF protection | MEDIUM | Add FastAPI CSRF middleware, update frontend to include tokens |
| Multi-tab auth conflicts | LOW | Move auth state from session state to cookies, verify shared cookie access |

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| JWT token lost on refresh | Phase 1: Auth Implementation | Test: Refresh browser after login, verify still authenticated |
| Infinite rerun loop | Phase 1: Auth Implementation | Code review: No st.rerun() in button handlers without guards |
| SSE buffering | Phase 2: Streaming Implementation | Test: Watch network tab during streaming, verify incremental chunks |
| Anonymous migration failure | Phase 2: Multi-User Core | Test: Create docs as anon, register, verify docs appear in authenticated view |
| File upload 422 error | Phase 1: Document Upload | Test: Upload PDF, DOCX, large file, verify all succeed with 200 |
| Pickle vulnerability | Phase 1: Auth Implementation | Code review: All session state writes validated, no raw objects |
| Event loop conflicts | Phase 1: API Integration | Test: All API calls work, no async/await in Streamlit code |
| Session state bloat | Phase 3: Performance Optimization | Monitor: Session state size <50KB per user |
| CSRF vulnerability | Phase 1: Auth Implementation | Security test: Attempt CSRF attack, verify rejection |
| Multi-tab auth conflicts | Phase 1: Auth Implementation | Test: Login in tab A, open tab B, verify authenticated in both |

## Sources

**Streamlit + FastAPI Integration:**
- [Streamlit 2026 Release Notes](https://docs.streamlit.io/develop/quick-reference/release-notes/2026)
- [FastAPI Backend → Streamlit Frontend Discussion](https://discuss.streamlit.io/t/fastapi-backend-streamlit-frontend/55460)
- [Issue with Integrating FastAPI with Streamlit](https://discuss.streamlit.io/t/issue-with-integrating-fastapi-with-streamlit/66888)
- [My Experience Building A FastAPI + Streamlit App](https://pybit.es/articles/my-experience-building-a-fastapi-streamlit-app/)
- [From Backend To Frontend: Connecting FastAPI And Streamlit](https://pybit.es/articles/from-backend-to-frontend-connecting-fastapi-and-streamlit/)

**Session State & Authentication:**
- [Streamlit Session State Documentation](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.session_state)
- [Add Statefulness to Apps](https://docs.streamlit.io/develop/concepts/architecture/session-state)
- [Why Session State is Not Persisting Between Refresh](https://discuss.streamlit.io/t/why-session-state-is-not-persisting-between-refresh/32020)
- [Session State Not Persisting After Redirect - MSAL Auth Issue](https://discuss.streamlit.io/t/session-state-not-persisting-after-redirect-msal-authentication-issue-in-streamlit/94721)
- [How I Solved Streamlit Session Persistence](https://dev.to/hendrixaidev/how-i-solved-streamlit-session-persistence-after-3-failed-attempts-b4c)
- [Implement JWT Authentication for Streamlit](https://blog.yusufberki.net/implement-jwt-authentication-for-the-streamlit-application-2e3b0ef884ef)

**SSE Streaming:**
- [Bridging LangGraph and Streamlit: Streaming Graph State](https://medium.com/@yigitbekir/bridging-langgraph-and-streamlit-a-practical-approach-to-streaming-graph-state-13db0999c80d)
- [FASTAPI-SSE-Event-Streaming with Streamlit](https://github.com/sarthakkaushik/FASTAPI-SSE-Event-Streaming-with-Streamlit/blob/master/README.md)
- [st.write_stream Documentation](https://docs.streamlit.io/develop/api-reference/write-magic/st.write_stream)
- [Fixing Slow SSE Streaming in Next.js and Vercel](https://medium.com/@oyetoketoby80/fixing-slow-sse-server-sent-events-streaming-in-next-js-and-vercel-99f42fbdb996)

**Execution Model & Reruns:**
- [Working with Streamlit's Execution Model](https://docs.streamlit.io/develop/concepts/architecture)
- [st.rerun Documentation](https://docs.streamlit.io/develop/api-reference/execution-flow/st.rerun)
- [Using st.rerun in Button Causes Infinite Loop](https://github.com/streamlit/streamlit/issues/9232)
- [st.rerun Not Updating Button State](https://github.com/streamlit/streamlit/issues/7662)
- [Streamlit Unit Testing - Infinite Loop with st.rerun](https://discuss.streamlit.io/t/streamlit-unit-testing-infinite-loop-with-st-rerun/56268)

**File Uploads:**
- [Post Request with file_uploader Object Throws 422](https://discuss.streamlit.io/t/post-request-with-parameter-as-a-streamlit-file-uploader-object-for-a-pdf-throws-422-unprocessable-entity-on-fastapi/45020)
- [FastAPI Request Files Documentation](https://fastapi.tiangolo.com/tutorial/request-files/)
- [How to Implement File Uploads in FastAPI](https://oneuptime.com/blog/post/2026-01-26-fastapi-file-uploads/view)
- [Serving ML Model with FastAPI and Streamlit](https://testdriven.io/blog/fastapi-streamlit/)

**Cookies & Security:**
- [Cookies Support in Streamlit](https://discuss.streamlit.io/t/cookies-support-in-streamlit/16144)
- [Ultimate Guide to Securing JWT with httpOnly Cookies](https://www.wisp.blog/blog/ultimate-guide-to-securing-jwt-authentication-with-httponly-cookies)
- [streamlit-jwt-authenticator Package](https://pypi.org/project/streamlit-jwt-authenticator/)
- [Some Code for Cookie-based Session Management](https://discuss.streamlit.io/t/some-code-for-cookie-based-session-management/54200)

**Deployment & Secrets:**
- [Streamlit Secrets Management](https://docs.streamlit.io/develop/concepts/connections/secrets-management)
- [Managing Secrets When Deploying Your App](https://docs.streamlit.io/deploy/concepts/secrets)
- [Secrets Management for Community Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management)

**RBAC & Testing:**
- [Role Based Authentication Discussion](https://discuss.streamlit.io/t/role-based-authentication/36598)
- [streamlit-mock Package for Testing](https://pypi.org/project/streamlit-mock/)
- [Mastering Integration Testing with FastAPI](https://alex-jacobs.com/posts/fastapitests/)

---
*Pitfalls research for: Streamlit Frontend with FastAPI Backend Integration*
*Researched: 2026-02-05*
