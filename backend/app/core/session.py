"""Anonymous session management with HTTP-only cookies.

Provides:
- Anonymous session ID generation with configurable prefix
- HTTP-only cookie management for security
- Session extraction from requests

SECURITY NOTES:
- Session IDs use HTTP-only cookies (prevents XSS)
- Never expose session IDs in URLs (Pitfall #4)
- secure=True required for production (HTTPS)
- samesite="lax" prevents CSRF attacks
"""

import secrets
from datetime import datetime, timezone
from typing import Optional

from fastapi import Request, Response

from app.config import settings


def generate_anonymous_session_id() -> str:
    """Generate unique anonymous session ID.

    Format: anon_{random_24_chars}
    Prefix distinguishes from authenticated user UUIDs.

    Returns:
        Unique anonymous session ID string.
    """
    return f"{settings.ANONYMOUS_PREFIX}{secrets.token_urlsafe(24)}"


def is_anonymous_session(session_id: str) -> bool:
    """Check if session ID is anonymous (starts with prefix).

    Args:
        session_id: Session ID to check.

    Returns:
        True if session ID starts with anonymous prefix.
    """
    return session_id.startswith(settings.ANONYMOUS_PREFIX)


def set_session_cookie(
    response: Response,
    session_id: str,
    max_age_days: Optional[int] = None,
) -> None:
    """Set HTTP-only session cookie.

    SECURITY: httponly prevents XSS, secure requires HTTPS, samesite prevents CSRF.

    Args:
        response: FastAPI Response object.
        session_id: Session ID to set in cookie.
        max_age_days: Optional custom expiration (default: settings.ANONYMOUS_SESSION_EXPIRE_DAYS).
    """
    max_age = (max_age_days or settings.ANONYMOUS_SESSION_EXPIRE_DAYS) * 24 * 3600
    response.set_cookie(
        key="session_id",
        value=session_id,
        max_age=max_age,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
    )


def get_session_from_request(request: Request) -> Optional[str]:
    """Extract session ID from cookie.

    Args:
        request: FastAPI Request object.

    Returns:
        Session ID if present in cookies, None otherwise.
    """
    return request.cookies.get("session_id")


def clear_session_cookie(response: Response) -> None:
    """Clear session cookie (for logout or session migration).

    Args:
        response: FastAPI Response object.
    """
    response.delete_cookie(key="session_id")
