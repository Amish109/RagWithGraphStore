"""API client wrapper using httpx Client (synchronous).

Uses synchronous httpx.Client to avoid asyncio event loop conflicts with Streamlit.
Manages anonymous session cookies via st.session_state for per-user isolation.

Backend endpoint contract:
- POST /api/v1/auth/login - form data (username=email, password), returns TokenPair
- POST /api/v1/auth/register - JSON {email, password}, returns TokenPair
- POST /api/v1/auth/logout - requires Bearer token, returns {message}
- POST /api/v1/auth/refresh - JSON {refresh_token}, returns TokenPair
- POST /api/v1/documents/upload - multipart file upload, returns DocumentUploadResponse
- GET /api/v1/documents/ - list user documents, returns List[DocumentInfo]
- GET /api/v1/documents/{id}/status - processing status, returns TaskStatusResponse
- DELETE /api/v1/documents/{id} - delete document, returns MessageResponse
- POST /api/v1/query/ - query documents, returns QueryResponse
- POST /api/v1/query/stream - streaming query via SSE
"""

import os
from typing import Generator, List, Optional

import httpx
import streamlit as st
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


def _get_headers() -> dict:
    """Build request headers with auth token or session cookie."""
    headers = {}
    token = st.session_state.get("access_token")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _get_cookies() -> dict:
    """Get session cookie for anonymous users."""
    session_id = st.session_state.get("anon_session_id")
    if session_id:
        return {"session_id": session_id}
    return {}


def _save_session_cookie(response: httpx.Response) -> None:
    """Save anonymous session cookie from response to session state and URL."""
    session_id = response.cookies.get("session_id")
    if session_id:
        st.session_state.anon_session_id = session_id
        # Persist in URL query params so it survives page refresh
        st.query_params["sid"] = session_id


def _request(method: str, url: str, **kwargs) -> httpx.Response:
    """Make an HTTP request with auth headers and session cookies.

    Automatically saves any session_id cookie from the response.
    """
    headers = _get_headers()
    headers.update(kwargs.pop("headers", {}))
    cookies = _get_cookies()
    cookies.update(kwargs.pop("cookies", {}))

    with httpx.Client(base_url=API_BASE_URL, timeout=30.0) as client:
        response = client.request(
            method, url, headers=headers, cookies=cookies, **kwargs
        )
        _save_session_cookie(response)
        return response


# =============================================================================
# Auth endpoints
# =============================================================================

def login(email: str, password: str) -> Optional[dict]:
    """Call backend login endpoint.

    Uses OAuth2 form data format as expected by backend.
    """
    try:
        response = _request(
            "POST",
            "/api/v1/auth/login",
            data={"username": email, "password": password},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        try:
            detail = e.response.json().get("detail", "Login failed")
        except Exception:
            detail = f"HTTP {e.response.status_code}"
        st.error(f"Login failed: {detail}")
        return None
    except httpx.RequestError as e:
        st.error(f"Connection error: {str(e)}")
        return None


def register(email: str, password: str) -> Optional[dict]:
    """Call backend register endpoint."""
    try:
        response = _request(
            "POST",
            "/api/v1/auth/register",
            json={"email": email, "password": password},
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        try:
            detail = e.response.json().get("detail", "Registration failed")
        except Exception:
            detail = f"HTTP {e.response.status_code}"
        st.error(f"Registration failed: {detail}")
        return None
    except httpx.RequestError as e:
        st.error(f"Connection error: {str(e)}")
        return None


def logout(access_token: str) -> bool:
    """Call backend logout endpoint."""
    try:
        response = _request(
            "POST",
            "/api/v1/auth/logout",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
        )
        response.raise_for_status()
        return True
    except (httpx.HTTPStatusError, httpx.RequestError):
        return False


def refresh_tokens(refresh_token: str) -> Optional[dict]:
    """Call backend refresh endpoint."""
    try:
        response = _request(
            "POST",
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        response.raise_for_status()
        return response.json()
    except (httpx.HTTPStatusError, httpx.RequestError):
        return None


# =============================================================================
# Document endpoints
# =============================================================================

def upload_document(
    file_bytes: bytes, filename: str, content_type: str
) -> Optional[dict]:
    """Upload a document to the backend."""
    try:
        response = _request(
            "POST",
            "/api/v1/documents/upload",
            files={"file": (filename, file_bytes, content_type)},
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        try:
            detail = e.response.json().get("detail", "Upload failed")
        except Exception:
            detail = f"HTTP {e.response.status_code}"
        st.error(f"Upload failed: {detail}")
        return None
    except httpx.RequestError as e:
        st.error(f"Connection error: {str(e)}")
        return None


def list_documents() -> List[dict]:
    """List user's documents."""
    try:
        response = _request("GET", "/api/v1/documents/")
        response.raise_for_status()
        return response.json()
    except (httpx.HTTPStatusError, httpx.RequestError):
        return []


def get_document_status(document_id: str) -> Optional[dict]:
    """Get document processing status."""
    try:
        response = _request("GET", f"/api/v1/documents/{document_id}/status")
        response.raise_for_status()
        return response.json()
    except (httpx.HTTPStatusError, httpx.RequestError):
        return None


def delete_document(document_id: str) -> bool:
    """Delete a document."""
    try:
        response = _request("DELETE", f"/api/v1/documents/{document_id}")
        response.raise_for_status()
        return True
    except (httpx.HTTPStatusError, httpx.RequestError):
        return False


# =============================================================================
# Query endpoints
# =============================================================================

def query_documents(query: str, max_results: int = 3) -> Optional[dict]:
    """Query documents."""
    try:
        response = _request(
            "POST",
            "/api/v1/query/",
            json={"query": query, "max_results": max_results},
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        try:
            detail = e.response.json().get("detail", "Query failed")
        except Exception:
            detail = f"HTTP {e.response.status_code}"
        st.error(f"Query failed: {detail}")
        return None
    except httpx.RequestError as e:
        st.error(f"Connection error: {str(e)}")
        return None


def query_documents_stream(query: str, max_results: int = 3) -> Generator:
    """Stream query response via SSE.

    Yields tuples of (event_type, data) for each SSE event.
    Event types: 'status', 'citations', 'token', 'done', 'error'.
    """
    headers = _get_headers()
    headers["Accept"] = "text/event-stream"
    cookies = _get_cookies()

    with httpx.Client(base_url=API_BASE_URL, timeout=120.0) as client:
        with client.stream(
            "POST",
            "/api/v1/query/stream",
            json={"query": query, "max_results": max_results},
            headers=headers,
            cookies=cookies,
        ) as response:
            _save_session_cookie(response)
            event_type = "message"
            for line in response.iter_lines():
                if line.startswith("event:"):
                    event_type = line[6:].strip()
                elif line.startswith("data:"):
                    # SSE spec: "data:" followed by optional single space
                    # Remove only the spec space, preserve token whitespace
                    data = line[5:]
                    if data.startswith(" "):
                        data = data[1:]
                    yield (event_type, data)
                    event_type = "message"
