"""JWT authentication and password hashing utilities.

Implements secure authentication following research Pattern 5:
- Argon2 password hashing (GPU-resistant, recommended for 2024+)
- PyJWT for token generation (NOT python-jose)
- Timezone-aware timestamps for token expiration
- Refresh token rotation with single-use enforcement (Phase 2)

SECURITY NOTES:
- Never log passwords or full tokens
- Never accept algorithm="none" in JWT decoding
- Always use HS256 or stronger algorithm
- Hash refresh tokens with SHA-256 before storage
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from app.config import settings

# Initialize Argon2 password hasher (GPU-resistant, recommended)
password_hash = PasswordHash((Argon2Hasher(),))


def hash_password(password: str) -> str:
    """Hash a password using Argon2.

    Args:
        password: Plain text password to hash

    Returns:
        Hashed password string
    """
    return password_hash.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash.

    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password to check against

    Returns:
        True if password matches, False otherwise
    """
    return password_hash.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token.

    Args:
        data: Payload data to encode in the token (typically {"sub": email})
        expires_delta: Optional custom expiration time. Defaults to settings.ACCESS_TOKEN_EXPIRE_MINUTES

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )

    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT access token.

    Args:
        token: JWT token string to decode

    Returns:
        Decoded payload dict if valid, None if expired or invalid

    SECURITY: Explicitly specifies allowed algorithms to prevent
    algorithm confusion attacks (never accepts "none").
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],  # Explicit list prevents "none" attack
        )
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def create_token_pair(user_email: str, user_id: str) -> Tuple[str, str, str]:
    """Create access token and refresh token pair.

    Each token pair shares a JTI (JWT ID) for tracking and revocation.
    Refresh token is long-lived, access token is short-lived.

    Args:
        user_email: User's email address (subject claim).
        user_id: User's unique identifier.

    Returns:
        Tuple of (access_token, refresh_token, jti).
    """
    jti = secrets.token_urlsafe(32)  # Unique token ID

    # Access token (short-lived)
    access_token = create_access_token(
        data={"sub": user_email, "user_id": user_id, "jti": jti}
    )

    # Refresh token (long-lived)
    refresh_expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    refresh_payload = {
        "sub": user_email,
        "user_id": user_id,
        "jti": jti,
        "exp": refresh_expire,
        "type": "refresh",
    }
    refresh_token = jwt.encode(
        refresh_payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )

    return access_token, refresh_token, jti


def hash_refresh_token(token: str) -> str:
    """Hash refresh token for secure storage.

    SECURITY: Never store raw refresh tokens. Hash with SHA-256.

    Args:
        token: Raw refresh token string.

    Returns:
        SHA-256 hash of the token.
    """
    return hashlib.sha256(token.encode()).hexdigest()


def decode_refresh_token(token: str) -> Optional[dict]:
    """Decode and validate a refresh token.

    Args:
        token: JWT refresh token string.

    Returns:
        Decoded payload dict if valid and is refresh type, None otherwise.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        # Verify this is a refresh token
        if payload.get("type") != "refresh":
            return None
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
