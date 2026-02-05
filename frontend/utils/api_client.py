"""API client wrapper using httpx AsyncClient.

Provides a cached singleton AsyncClient for all backend API calls.
Uses @st.cache_resource to prevent connection leaks.

Backend endpoint contract:
- POST /api/v1/auth/login - form data (username=email, password), returns TokenPair
- POST /api/v1/auth/register - JSON {email, password}, returns TokenPair
- POST /api/v1/auth/logout - requires Bearer token, returns {message}
- POST /api/v1/auth/refresh - JSON {refresh_token}, returns TokenPair
"""

import asyncio
import os
from typing import Optional

import httpx
import streamlit as st
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


@st.cache_resource
def get_api_client() -> httpx.AsyncClient:
    """Create singleton AsyncClient for all API calls.

    Uses @st.cache_resource to ensure single instance per Streamlit app.
    This prevents connection leaks from creating new clients per request.

    Returns:
        httpx.AsyncClient configured with base URL and timeout.
    """
    return httpx.AsyncClient(
        base_url=API_BASE_URL,
        timeout=30.0,
        headers={"Content-Type": "application/json"},
    )


async def _login_async(email: str, password: str) -> Optional[dict]:
    """Call backend login endpoint (async).

    Uses OAuth2 form data format as expected by backend.

    Args:
        email: User's email address.
        password: User's password.

    Returns:
        Token pair dict with access_token, refresh_token, token_type on success.
        None on failure.
    """
    client = get_api_client()
    try:
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": email, "password": password},  # OAuth2 form format
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        # Extract error detail from response if available
        try:
            detail = e.response.json().get("detail", "Login failed")
        except Exception:
            detail = f"HTTP {e.response.status_code}"
        st.error(f"Login failed: {detail}")
        return None
    except httpx.RequestError as e:
        st.error(f"Connection error: {str(e)}")
        return None


def login(email: str, password: str) -> Optional[dict]:
    """Synchronous wrapper for async login.

    Streamlit callbacks are synchronous, so we need this wrapper.

    Args:
        email: User's email address.
        password: User's password.

    Returns:
        Token pair dict on success, None on failure.
    """
    return asyncio.run(_login_async(email, password))


async def _register_async(email: str, password: str) -> Optional[dict]:
    """Call backend register endpoint (async).

    Uses JSON body format as expected by backend.

    Args:
        email: User's email address.
        password: User's password.

    Returns:
        Token pair dict with access_token, refresh_token, token_type on success.
        None on failure.
    """
    client = get_api_client()
    try:
        response = await client.post(
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


def register(email: str, password: str) -> Optional[dict]:
    """Synchronous wrapper for async register.

    Args:
        email: User's email address.
        password: User's password.

    Returns:
        Token pair dict on success, None on failure.
    """
    return asyncio.run(_register_async(email, password))


async def _logout_async(access_token: str) -> bool:
    """Call backend logout endpoint (async).

    Requires Bearer token authorization.

    Args:
        access_token: JWT access token to invalidate.

    Returns:
        True on successful logout, False on failure.
    """
    client = get_api_client()
    try:
        response = await client.post(
            "/api/v1/auth/logout",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
        )
        response.raise_for_status()
        return True
    except httpx.HTTPStatusError:
        return False
    except httpx.RequestError:
        return False


def logout(access_token: str) -> bool:
    """Synchronous wrapper for async logout.

    Args:
        access_token: JWT access token to invalidate.

    Returns:
        True on successful logout, False on failure.
    """
    return asyncio.run(_logout_async(access_token))


async def _refresh_tokens_async(refresh_token: str) -> Optional[dict]:
    """Call backend refresh endpoint (async).

    Exchanges refresh token for new token pair.

    Args:
        refresh_token: Current refresh token.

    Returns:
        New token pair dict on success, None on failure.
    """
    client = get_api_client()
    try:
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError:
        return None
    except httpx.RequestError:
        return None


def refresh_tokens(refresh_token: str) -> Optional[dict]:
    """Synchronous wrapper for async refresh.

    Args:
        refresh_token: Current refresh token.

    Returns:
        New token pair dict on success, None on failure.
    """
    return asyncio.run(_refresh_tokens_async(refresh_token))
