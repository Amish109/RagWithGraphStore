"""Authentication API routes.

Provides endpoints for:
- POST /register - Create new user account
- POST /login - Authenticate and get JWT token pair
- POST /refresh - Exchange refresh token for new token pair
- POST /logout - Logout and invalidate tokens via blocklist

Requirement references:
- API-07: POST /api/v1/auth/register
- API-08: POST /api/v1/auth/login
- API-10: POST /api/v1/auth/logout
- AUTH-01, AUTH-02, AUTH-06, AUTH-07
"""

from uuid import uuid4

import redis.asyncio as redis
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.core.auth import (
    create_token_pair,
    decode_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.core.exceptions import UserExistsException
from app.core.security import get_current_user
from app.db.redis_client import (
    add_token_to_blocklist,
    delete_refresh_token,
    get_redis,
    get_stored_refresh_token,
    store_refresh_token,
)
from app.models.schemas import MessageResponse, RefreshRequest, TokenPair, UserRegister
from app.models.user import create_user, get_user_by_email

router = APIRouter()


@router.post("/register", response_model=TokenPair, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister,
    redis_client: redis.Redis = Depends(get_redis),
):
    """Register a new user account.

    Creates user in Neo4j and returns JWT token pair.

    Args:
        user_data: Email and password for new account
        redis_client: Redis client for storing refresh token

    Returns:
        TokenPair with access_token, refresh_token, and token_type

    Raises:
        UserExistsException: If email already registered
    """
    # Check if user already exists
    existing_user = get_user_by_email(user_data.email)
    if existing_user:
        raise UserExistsException()

    # Generate user ID and hash password
    user_id = str(uuid4())
    hashed_password = hash_password(user_data.password)

    # Create user in database
    create_user(
        email=user_data.email,
        hashed_password=hashed_password,
        user_id=user_id,
    )

    # Generate token pair
    access_token, refresh_token, jti = create_token_pair(user_data.email, user_id)

    # Store hashed refresh token in Redis
    await store_refresh_token(
        user_id=user_id,
        jti=jti,
        token_hash=hash_refresh_token(refresh_token),
        redis_client=redis_client,
    )

    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.post("/login", response_model=TokenPair)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    redis_client: redis.Redis = Depends(get_redis),
):
    """Authenticate user and return JWT token pair.

    Uses OAuth2PasswordRequestForm for compatibility with FastAPI docs
    and standard OAuth2 clients. Email is passed as 'username' field.

    Args:
        form_data: OAuth2 form with username (email) and password
        redis_client: Redis client for storing refresh token

    Returns:
        TokenPair with access_token, refresh_token, and token_type

    Raises:
        HTTPException 401: If credentials are invalid
    """
    # Look up user by email (form_data.username contains email)
    user = get_user_by_email(form_data.username)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify password
    if not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Generate token pair with user's role
    access_token, refresh_token, jti = create_token_pair(
        user["email"], user["id"], user.get("role", "user")
    )

    # Store hashed refresh token in Redis
    await store_refresh_token(
        user_id=user["id"],
        jti=jti,
        token_hash=hash_refresh_token(refresh_token),
        redis_client=redis_client,
    )

    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.post("/refresh", response_model=TokenPair)
async def refresh_tokens(
    request: RefreshRequest,
    redis_client: redis.Redis = Depends(get_redis),
):
    """Exchange refresh token for new token pair.

    Implements single-use refresh token rotation:
    - Validates refresh token and checks it exists in Redis
    - Deletes old refresh token (single-use enforcement)
    - Issues new access + refresh token pair
    - Stores new refresh token in Redis

    SECURITY: Each refresh token can only be used once.
    If attacker uses stolen token, legitimate user's next refresh fails,
    alerting to potential compromise.

    Args:
        request: RefreshRequest with refresh_token
        redis_client: Redis client for token operations

    Returns:
        TokenPair with new access_token and refresh_token

    Raises:
        HTTPException 401: If refresh token is invalid, expired, or already used
    """
    # Decode refresh token
    payload = decode_refresh_token(request.refresh_token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_email = payload.get("sub")
    user_id = payload.get("user_id")
    jti = payload.get("jti")

    if not all([user_email, user_id, jti]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if token exists in Redis (not already used)
    stored_hash = await get_stored_refresh_token(user_id, jti, redis_client)
    if stored_hash is None:
        # Token already rotated or never existed - possible theft
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token already used or invalid",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify hash matches
    if stored_hash != hash_refresh_token(request.refresh_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token hash mismatch",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Delete old token (single-use enforcement)
    await delete_refresh_token(user_id, jti, redis_client)

    # Issue new token pair - preserve role from original token
    user_role = payload.get("role", "user")
    new_access, new_refresh, new_jti = create_token_pair(user_email, user_id, user_role)

    # Store new refresh token
    await store_refresh_token(
        user_id=user_id,
        jti=new_jti,
        token_hash=hash_refresh_token(new_refresh),
        redis_client=redis_client,
    )

    return TokenPair(
        access_token=new_access,
        refresh_token=new_refresh,
        token_type="bearer",
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    current_user: dict = Depends(get_current_user),
    redis_client: redis.Redis = Depends(get_redis),
):
    """Logout current user and invalidate token.

    Adds the current token's JTI to the blocklist so it cannot be reused.
    The blocklist has TTL matching token expiration to prevent unbounded growth.

    Args:
        current_user: Authenticated user from JWT token
        redis_client: Redis client for blocklist operations

    Returns:
        MessageResponse confirming logout
    """
    # Get JTI from current token via the user context
    jti = current_user.get("jti")
    if jti:
        await add_token_to_blocklist(jti, redis_client)

    return MessageResponse(message="Successfully logged out")
