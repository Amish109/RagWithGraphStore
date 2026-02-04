"""FastAPI security dependencies for authentication.

Provides OAuth2 scheme and current user dependencies for protecting routes:
- get_current_user: Requires authentication (401 if not authenticated)
- get_current_user_optional: Handles both authenticated and anonymous users

Following research Pattern 5 for secure JWT authentication.
Following research Pattern 3 for anonymous session management.
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, Request, Response
from fastapi.security import OAuth2PasswordBearer

from app.core.auth import decode_access_token
from app.core.exceptions import CredentialsException
from app.core.session import (
    generate_anonymous_session_id,
    get_session_from_request,
    is_anonymous_session,
    set_session_cookie,
)
from app.models.schemas import UserContext
from app.models.user import get_user_by_email

# OAuth2 scheme with token URL matching the login endpoint
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# OAuth2 scheme that doesn't auto-error (for optional auth)
oauth2_scheme_optional = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=False,
)


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """Dependency to get the current authenticated user from JWT token.

    Args:
        token: JWT token extracted from Authorization header

    Returns:
        User dict from database with additional token info (jti, role)

    Raises:
        CredentialsException: If token is invalid or user not found
    """
    # Decode and validate token
    payload = decode_access_token(token)
    if payload is None:
        raise CredentialsException()

    # Extract email from token subject
    email: str = payload.get("sub")
    if email is None:
        raise CredentialsException()

    # Look up user in database
    user = get_user_by_email(email)
    if user is None:
        raise CredentialsException()

    # Include JTI from token for logout/blocklist operations
    jti = payload.get("jti")
    if jti:
        user["jti"] = jti

    # Include role from token (faster than DB lookup each request)
    # Token role is authoritative - DB role used for initial login
    role = payload.get("role", user.get("role", "user"))
    user["role"] = role

    return user


async def get_current_user_optional(
    request: Request,
    response: Response,
    token: Optional[str] = Depends(oauth2_scheme_optional),
) -> UserContext:
    """Get current user or create/retrieve anonymous session.

    Returns UserContext with 'id' key. For anonymous users:
    - id: anonymous session ID (anon_xxx)
    - is_anonymous: True
    - session_created: timestamp

    CRITICAL: Anonymous and authenticated users use SAME interface.
    All queries filter by user_context.id regardless of auth status.

    Args:
        request: FastAPI Request for reading cookies.
        response: FastAPI Response for setting cookies.
        token: Optional JWT token from Authorization header.

    Returns:
        UserContext for either authenticated or anonymous user.
    """
    if token:
        # Try to validate JWT
        try:
            payload = decode_access_token(token)
            if payload:
                user = get_user_by_email(payload.get("sub"))
                if user:
                    return UserContext(
                        id=user["id"],
                        email=user["email"],
                        is_anonymous=False,
                        role=user.get("role", "user"),
                        jti=payload.get("jti"),
                    )
        except Exception:
            pass  # Fall through to anonymous

    # No valid token - use/create anonymous session
    session_id = get_session_from_request(request)

    if not session_id or not is_anonymous_session(session_id):
        # Create new anonymous session
        session_id = generate_anonymous_session_id()
        set_session_cookie(response, session_id)

    return UserContext(
        id=session_id,
        is_anonymous=True,
        role="anonymous",
        session_created=datetime.now(timezone.utc).isoformat(),
    )
