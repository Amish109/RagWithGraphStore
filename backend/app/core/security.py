"""FastAPI security dependencies for authentication.

Provides OAuth2 scheme and current user dependency for protecting routes.
Following research Pattern 5 for secure JWT authentication.
"""

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from app.core.auth import decode_access_token
from app.core.exceptions import CredentialsException
from app.models.user import get_user_by_email

# OAuth2 scheme with token URL matching the login endpoint
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """Dependency to get the current authenticated user from JWT token.

    Args:
        token: JWT token extracted from Authorization header

    Returns:
        User dict from database

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

    return user
