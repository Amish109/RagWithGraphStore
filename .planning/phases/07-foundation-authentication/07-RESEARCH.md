# Phase 7: Foundation & Authentication - Research

**Researched:** 2026-02-05
**Domain:** Streamlit authentication with FastAPI JWT backend
**Confidence:** MEDIUM

## Summary

Streamlit authentication with JWT backend requires careful handling of session persistence across browser refreshes. The standard approach uses st.navigation for dynamic page rendering based on authentication state, with session_state for runtime tracking and external storage (cookies or database) for persistence. The built-in st.login() with OIDC is unsuitable for custom FastAPI JWT backends.

Key findings: Session state alone loses authentication on refresh. The solution is either (1) use extra-streamlit-components CookieManager (client-side, simpler) or (2) store tokens server-side in Redis and use session IDs in cookies. For this phase, client-side httpx calls to FastAPI backend with session_state token storage suffices, with refresh token rotation handling persistence.

Critical pitfall: Inline st.rerun() in button handlers causes infinite loops. Use callback functions with on_click parameter instead to update session state without explicit reruns.

**Primary recommendation:** Use st.navigation for dynamic page rendering, httpx AsyncClient in @st.cache_resource context manager for API calls, session_state for token storage, and callback-based authentication flows to prevent infinite reruns.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| streamlit | 1.40.0+ | Web framework | Official framework, st.navigation added 1.35, OIDC support added 1.39 |
| httpx | 0.28.1+ | HTTP client | Async-native, superior to requests, supports context managers |
| pyjwt | Latest | JWT validation | Same library backend uses, ensures compatibility |
| python-dotenv | Latest | Config management | Load .env for API base URLs |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| extra-streamlit-components | Latest | Cookie management | If implementing persistent login across refreshes (optional for Phase 7) |
| streamlit-pydantic | Latest | Form validation | If using Pydantic models for form validation (optional, can use manual validation) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| httpx | requests | requests is sync-only, httpx is async-native and more modern |
| Manual forms | streamlit-authenticator | streamlit-authenticator conflicts with custom JWT backend, causes token mismatch |
| st.navigation | pages/ directory | pages/ is simpler but can't conditionally show pages based on auth state |

**Installation:**
```bash
pip install streamlit>=1.40.0 httpx>=0.28.1 pyjwt python-dotenv
# Optional for persistent login:
# pip install extra-streamlit-components
```

## Architecture Patterns

### Recommended Project Structure
```
frontend/
├── app.py                      # Entrypoint with st.navigation
├── .env                        # API_BASE_URL=http://localhost:8000
├── utils/
│   ├── __init__.py
│   ├── api_client.py           # httpx AsyncClient wrapper
│   ├── auth.py                 # Login/register/logout logic
│   └── session.py              # Session state initialization
└── pages/
    ├── __init__.py
    ├── login.py                # Login page (always available)
    ├── register.py             # Register page (always available)
    ├── home.py                 # Main page (auth required)
    └── debug.py                # Debug panel (auth required)
```

### Pattern 1: Dynamic Navigation with Authentication
**What:** Conditionally build page list based on session_state.is_authenticated, then call st.navigation once per run
**When to use:** All multi-page apps with role-based or authentication-based access control
**Example:**
```python
# Source: https://docs.streamlit.io/develop/concepts/multipage-apps/page-and-navigation
import streamlit as st

# Initialize session state
if "is_authenticated" not in st.session_state:
    st.session_state.is_authenticated = False
if "user_info" not in st.session_state:
    st.session_state.user_info = None

# Define pages
login_page = st.Page("pages/login.py", title="Login", icon="🔐")
register_page = st.Page("pages/register.py", title="Register", icon="📝")
home_page = st.Page("pages/home.py", title="Home", icon="🏠")
debug_page = st.Page("pages/debug.py", title="Debug", icon="🔧")

# Conditionally build navigation
if st.session_state.is_authenticated:
    pg = st.navigation({
        "Account": [home_page],
        "Tools": [debug_page],
    })
else:
    pg = st.navigation([login_page, register_page])

pg.run()
```

### Pattern 2: Cached API Client with AsyncClient
**What:** Use @st.cache_resource to create single AsyncClient instance, use asyncio.run() for async calls
**When to use:** All API communication from Streamlit to backend
**Example:**
```python
# Source: https://www.python-httpx.org/async/
import asyncio
import httpx
import streamlit as st
from typing import Optional

@st.cache_resource
def get_api_client() -> httpx.AsyncClient:
    """Create singleton AsyncClient for all API calls.

    IMPORTANT: Use context manager pattern OR ensure explicit cleanup.
    Since this is cached, we don't use context manager here.
    """
    return httpx.AsyncClient(
        base_url="http://localhost:8000",
        timeout=30.0,
        headers={"Content-Type": "application/json"}
    )

async def login_async(email: str, password: str) -> Optional[dict]:
    """Call backend login endpoint."""
    client = get_api_client()
    try:
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": email, "password": password}  # OAuth2 format
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        st.error(f"Login failed: {e.response.json().get('detail', 'Unknown error')}")
        return None

def login(email: str, password: str) -> Optional[dict]:
    """Synchronous wrapper for async login."""
    return asyncio.run(login_async(email, password))
```

### Pattern 3: Callback-Based Authentication Flow
**What:** Use on_click callbacks to update session_state, avoid inline st.rerun()
**When to use:** All authentication button handlers (login, logout, register)
**Example:**
```python
# Source: https://docs.streamlit.io/develop/api-reference/execution-flow/st.rerun
import streamlit as st

def handle_login():
    """Callback for login button - updates session state without explicit rerun."""
    email = st.session_state.email_input
    password = st.session_state.password_input

    # Call API
    result = login(email, password)

    if result:
        st.session_state.is_authenticated = True
        st.session_state.access_token = result["access_token"]
        st.session_state.refresh_token = result["refresh_token"]
        st.session_state.user_info = decode_token(result["access_token"])
        # NO st.rerun() needed - Streamlit auto-reruns after callback
    else:
        st.session_state.login_error = "Invalid credentials"

# In login page
st.text_input("Email", key="email_input")
st.text_input("Password", type="password", key="password_input")
st.button("Login", on_click=handle_login)  # Use callback, NOT inline logic

if "login_error" in st.session_state:
    st.error(st.session_state.login_error)
    del st.session_state.login_error  # Clear error after displaying
```

### Pattern 4: JWT Token Validation on Page Load
**What:** Check token expiry at start of each protected page, refresh if expired
**When to use:** All authenticated pages
**Example:**
```python
import streamlit as st
import jwt
from datetime import datetime, timezone

def is_token_expired(token: str) -> bool:
    """Check if JWT token is expired without validation (just read exp claim)."""
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
        exp = payload.get("exp")
        if not exp:
            return True
        return datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc)
    except:
        return True

def check_auth():
    """Validate authentication at page start. Redirect to login if invalid."""
    if not st.session_state.get("is_authenticated"):
        st.switch_page("pages/login.py")

    # Check token expiry and refresh if needed
    if is_token_expired(st.session_state.access_token):
        # Try to refresh token
        result = refresh_tokens(st.session_state.refresh_token)
        if result:
            st.session_state.access_token = result["access_token"]
            st.session_state.refresh_token = result["refresh_token"]
            st.rerun()  # OK to use here - guarded by expiry check
        else:
            # Refresh failed, logout
            st.session_state.clear()
            st.switch_page("pages/login.py")

# At top of every protected page
check_auth()
```

### Pattern 5: Anonymous Session Support
**What:** Backend creates anonymous sessions automatically, frontend tracks session_type (authenticated/anonymous)
**When to use:** Apps supporting anonymous browsing
**Example:**
```python
import streamlit as st

def init_session():
    """Initialize session state with anonymous or authenticated user."""
    if "session_type" not in st.session_state:
        # Check if user has tokens (authenticated)
        if st.session_state.get("access_token"):
            st.session_state.session_type = "authenticated"
        else:
            # Anonymous mode - backend will create session on first API call
            st.session_state.session_type = "anonymous"
            # Note: Backend returns session cookie, httpx handles automatically

# In sidebar
with st.sidebar:
    if st.session_state.session_type == "authenticated":
        st.write(f"👤 {st.session_state.user_info['email']}")
        st.write(f"🔒 Role: {st.session_state.user_info['role']}")
    else:
        st.write("🔓 Anonymous Session")
        st.info("Register to save your data permanently")
```

### Anti-Patterns to Avoid
- **Inline st.rerun() in button handlers:** Causes infinite loops. Use callbacks instead (on_click parameter).
- **Multiple AsyncClient instances:** Creates resource leaks. Use @st.cache_resource for singleton.
- **Storing passwords in session_state:** Even temporarily. Hash/validate server-side immediately.
- **Using streamlit-authenticator with custom JWT backend:** Causes token format mismatches.
- **Session state only for persistence:** Lost on refresh. Use cookies or backend for long-term storage.
- **Calling st.navigation multiple times:** Must call exactly once per run in entrypoint file.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JWT decode/validation | Manual base64 + JSON parsing | pyjwt library | Handles expiry, signatures, algorithms, vulnerabilities |
| HTTP client | urllib or requests | httpx AsyncClient | Modern async support, better error handling, context managers |
| Form validation | Manual if/else checks | streamlit-pydantic or backend validation | Edge cases, error messages, type coercion |
| Session persistence across refresh | Custom JavaScript + localStorage | extra-streamlit-components CookieManager | Handles SameSite, security, iframe edge cases |
| Authentication UI | Custom HTML/CSS components | Native st.text_input + st.button | Streamlit handles responsive design, state management |

**Key insight:** Streamlit's reactive rerun model makes manual state synchronization error-prone. Use built-in session_state and callbacks rather than custom state tracking.

## Common Pitfalls

### Pitfall 1: Session State Lost on Browser Refresh
**What goes wrong:** User logs in, stores JWT in session_state, refreshes browser, session_state clears, user logged out.
**Why it happens:** Session state is in-memory per WebSocket connection. Browser refresh creates new connection.
**How to avoid:**
- Option 1: Store tokens in cookies using extra-streamlit-components CookieManager
- Option 2: Store session ID in cookie, tokens in Redis (backend pattern)
- Option 3: Use Streamlit's built-in st.login() with OIDC (requires OIDC provider, not custom JWT)
**Warning signs:** Users complain about being logged out when refreshing page or opening new tab.

### Pitfall 2: Infinite Rerun Loop in Authentication Flow
**What goes wrong:** Button click triggers st.rerun(), which re-executes button block, triggering rerun again infinitely.
**Why it happens:** Putting st.rerun() directly in `if st.button():` block without state guard.
**How to avoid:**
- Use callback functions with on_click parameter
- If st.rerun() is necessary, guard it with session_state flag that prevents re-execution
- Let Streamlit auto-rerun after callback completes
**Warning signs:** App becomes unresponsive, CPU spikes, browser console shows rapid requests.

### Pitfall 3: Token Expiry Not Handled
**What goes wrong:** Access token expires (15 minutes default), API calls fail with 401, user sees errors.
**Why it happens:** Not checking token expiry before API calls or not implementing refresh flow.
**How to avoid:**
- Check token expiry at page load
- Implement automatic refresh token rotation
- Fallback to re-login if refresh fails
**Warning signs:** Intermittent 401 errors after user has been active for 15+ minutes.

### Pitfall 4: Storing Sensitive Data in Session State
**What goes wrong:** User opens browser console, accesses st.session_state, sees tokens or sensitive data.
**Why it happens:** Session state is client-side accessible via developer tools.
**How to avoid:**
- Accept that session_state is client-accessible (it's necessary for tokens)
- Never log tokens or passwords
- Use HTTPS in production
- Implement token expiry and rotation
**Warning signs:** Security audit flags client-side token storage (acknowledge as acceptable risk vs UX).

### Pitfall 5: Anonymous-to-Authenticated Migration Lost
**What goes wrong:** Anonymous user uploads documents, registers, documents disappear.
**Why it happens:** Frontend doesn't send anonymous session ID during registration.
**How to avoid:**
- Backend handles session cookie automatically (httpx preserves cookies)
- Ensure httpx client doesn't clear cookies between anonymous and authenticated calls
- Test migration flow explicitly
**Warning signs:** User reports data loss after registration.

### Pitfall 6: st.navigation Called Multiple Times or Outside Entrypoint
**What goes wrong:** Error "st.navigation can only be called once per app run" or navigation doesn't work.
**Why it happens:** Calling st.navigation in a page file or conditional block that executes multiple times.
**How to avoid:**
- Call st.navigation exactly once in app.py (entrypoint)
- Build page list conditionally BEFORE calling st.navigation
- Use st.switch_page() for programmatic navigation within pages
**Warning signs:** Navigation menu doesn't update when auth state changes, or Streamlit raises exception.

### Pitfall 7: Using requests Instead of httpx
**What goes wrong:** Synchronous blocking calls, can't use async patterns, harder to manage connections.
**Why it happens:** requests is more familiar, but Streamlit benefits from async for responsiveness.
**How to avoid:**
- Use httpx with asyncio.run() wrapper for simplicity
- Cache AsyncClient with @st.cache_resource
- Follow httpx context manager patterns
**Warning signs:** App feels sluggish, backend calls block UI updates.

## Code Examples

Verified patterns from official sources:

### Complete Login Page
```python
# pages/login.py
# Source: Combined from https://docs.streamlit.io/develop/concepts/multipage-apps/page-and-navigation
import streamlit as st
from utils.auth import login_user

st.title("🔐 Login")

def handle_login():
    """Callback for login button."""
    result = login_user(
        st.session_state.login_email,
        st.session_state.login_password
    )

    if result:
        st.session_state.is_authenticated = True
        st.session_state.access_token = result["access_token"]
        st.session_state.refresh_token = result["refresh_token"]
        # Auto-switches to authenticated navigation on next rerun
    else:
        st.session_state.show_error = True

st.text_input("Email", key="login_email")
st.text_input("Password", type="password", key="login_password")
st.button("Login", on_click=handle_login)

if st.session_state.get("show_error"):
    st.error("Invalid email or password")
    st.session_state.show_error = False

st.markdown("---")
st.info("Don't have an account? Go to Register page.")
```

### Sidebar User Info Display
```python
# utils/session.py
# Source: https://docs.streamlit.io/develop/api-reference/layout/st.sidebar
import streamlit as st
import jwt
from datetime import datetime, timezone

def render_user_info():
    """Display user info in sidebar (call from app.py)."""
    with st.sidebar:
        st.markdown("### 👤 User Info")

        if st.session_state.get("is_authenticated"):
            # Decode token to get user info
            payload = jwt.decode(
                st.session_state.access_token,
                options={"verify_signature": False}
            )

            st.write(f"**Email:** {payload['sub']}")
            st.write(f"**Role:** {payload.get('role', 'user')}")
            st.write(f"**Session:** Authenticated")

            # Token expiry
            exp = datetime.fromtimestamp(payload['exp'], tz=timezone.utc)
            remaining = exp - datetime.now(timezone.utc)
            st.write(f"**Token expires in:** {remaining.seconds // 60} minutes")

        else:
            st.write("**Session:** Anonymous")
            st.caption("Login to save your data")
```

### Debug Panel with JWT Info
```python
# pages/debug.py
# Source: Combined patterns
import streamlit as st
import jwt
from datetime import datetime, timezone

st.title("🔧 Debug Panel")

if not st.session_state.get("is_authenticated"):
    st.warning("Login required")
    st.stop()

st.subheader("JWT Token Info")

# Decode without validation to show contents
payload = jwt.decode(
    st.session_state.access_token,
    options={"verify_signature": False}
)

col1, col2 = st.columns(2)

with col1:
    st.metric("User ID", payload.get("user_id", "N/A"))
    st.metric("Role", payload.get("role", "user"))

with col2:
    exp_timestamp = payload.get("exp")
    if exp_timestamp:
        exp_dt = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
        remaining = exp_dt - datetime.now(timezone.utc)
        st.metric("Token Expires", f"{remaining.seconds // 60}m {remaining.seconds % 60}s")

    iat_timestamp = payload.get("iat")
    if iat_timestamp:
        iat_dt = datetime.fromtimestamp(iat_timestamp, tz=timezone.utc)
        st.metric("Issued At", iat_dt.strftime("%Y-%m-%d %H:%M:%S"))

st.subheader("Session State")
st.json({
    "is_authenticated": st.session_state.is_authenticated,
    "session_type": st.session_state.get("session_type", "unknown"),
    "token_type": "bearer"
})

# Show raw token (expandable)
with st.expander("Raw Access Token"):
    st.code(st.session_state.access_token)

with st.expander("Decoded Payload"):
    st.json(payload)
```

### Logout Callback
```python
# utils/auth.py
import streamlit as st
import asyncio
import httpx

async def logout_async() -> bool:
    """Call backend logout endpoint."""
    client = get_api_client()
    try:
        response = await client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {st.session_state.access_token}"}
        )
        return response.status_code == 200
    except:
        return False

def handle_logout():
    """Callback for logout button."""
    # Call backend logout (adds token to blocklist)
    asyncio.run(logout_async())

    # Clear session state
    for key in list(st.session_state.keys()):
        del st.session_state[key]

    # Will auto-redirect to login page on next rerun via st.navigation logic

# Use in any authenticated page
st.button("Logout", on_click=handle_logout)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| pages/ directory | st.navigation + st.Page | Streamlit 1.35 (2024-Q2) | Dynamic page rendering based on auth state |
| streamlit-authenticator | Custom JWT + backend integration | Always preferred for custom backends | Avoids token format conflicts |
| requests library | httpx AsyncClient | httpx 0.28+ (2024) | Async-native, better error handling |
| st.experimental_rerun | st.rerun | Streamlit 1.27 (2023) | API stabilization, same behavior |
| Manual cookie JS | extra-streamlit-components | Stable since 2022 | Handles security headers, SameSite |
| Session state only | OIDC with st.login | Streamlit 1.39 (2025-Q4) | Auto-managed identity cookies for OIDC providers |

**Deprecated/outdated:**
- **st.experimental_rerun**: Replaced by st.rerun (same functionality, stable API)
- **streamlit-authenticator for JWT backends**: Use for standalone apps only, conflicts with custom JWT
- **requests for new projects**: httpx is modern standard for Python HTTP clients

## Open Questions

Things that couldn't be fully resolved:

1. **Cookie-based persistence implementation details**
   - What we know: extra-streamlit-components CookieManager exists, can store JWT tokens
   - What's unclear: Whether it properly handles HttpOnly flag (security requirement), SameSite settings in shared environments
   - Recommendation: Phase 7 can skip persistent login (accept refresh logout), implement in Phase 8+ if needed. Use session_state only for MVP.

2. **Backend session cookie handling with httpx**
   - What we know: Backend sets HTTP-only session cookies for anonymous sessions, httpx preserves cookies automatically
   - What's unclear: Whether Streamlit's per-user isolation affects cookie storage across reruns
   - Recommendation: Test anonymous session flow early, verify cookies persist in httpx client cached with @st.cache_resource.

3. **Token refresh timing strategy**
   - What we know: Access tokens expire in 15 minutes, refresh tokens in 7 days
   - What's unclear: Best UX for refresh - check on every page load, background timer, or only on API failure
   - Recommendation: Check on page load in check_auth() function (Pattern 4). Simple, reliable, acceptable latency.

4. **Error display across page navigation**
   - What we know: st.error() shows until next rerun, cleared when navigating pages
   - What's unclear: How to show persistent error notifications across page switches
   - Recommendation: Use session_state flags for errors, check/display in app.py before pg.run(), clear after display.

## Sources

### Primary (HIGH confidence)
- Streamlit official docs - st.navigation API: https://docs.streamlit.io/develop/concepts/multipage-apps/page-and-navigation
- Streamlit official docs - Dynamic navigation tutorial: https://docs.streamlit.io/develop/tutorials/multipage/dynamic-navigation
- Streamlit official docs - Authentication concepts: https://docs.streamlit.io/develop/concepts/connections/authentication
- Streamlit official docs - st.rerun behavior: https://docs.streamlit.io/develop/api-reference/execution-flow/st.rerun
- httpx official docs - Async API: https://www.python-httpx.org/async/
- Backend auth.py source code - Token format and endpoints

### Secondary (MEDIUM confidence)
- Streamlit community - Multi-page authentication patterns: https://discuss.streamlit.io/t/a-multi-page-app-with-authentication-verification-and-session-state/18526
- Streamlit community - Persistent login discussions: https://discuss.streamlit.io/t/persistent-logins/43300
- Streamlit community - Session state refresh issues: https://discuss.streamlit.io/t/user-logged-out-after-page-refresh-need-persistent-session/78834
- Streamlit blog - Authenticator patterns: https://blog.streamlit.io/streamlit-authenticator-part-1-adding-an-authentication-component-to-your-app/

### Tertiary (LOW confidence)
- WebSearch results on CookieManager HTTP-only support (2024 discussions, no 2026 updates found)
- Community patterns for httpx with Streamlit (various blogs, not official)
- streamlit-pydantic form validation (optional library, not deeply researched)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Official Streamlit docs confirm st.navigation patterns, httpx is established standard
- Architecture: MEDIUM - Patterns verified from official docs, but cookie persistence not fully tested
- Pitfalls: HIGH - Infinite rerun loop, session state refresh, st.navigation constraints all documented in official sources

**Research date:** 2026-02-05
**Valid until:** 2026-03-05 (30 days - Streamlit stable, patterns unlikely to change)

**Key constraints from backend:**
- Access token expires: 15 minutes (ACCESS_TOKEN_EXPIRE_MINUTES)
- Refresh token expires: 7 days (REFRESH_TOKEN_EXPIRE_DAYS)
- Token format: JWT with claims {sub: email, user_id, role, jti, exp}
- Endpoints: POST /auth/login, POST /auth/register, POST /auth/logout, POST /auth/refresh
- Anonymous sessions: Automatic, tracked via HTTP-only cookie (backend-managed)
