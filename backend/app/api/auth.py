"""Authentication API routes.

Provides endpoints for:
- POST /register - Create new user account
- POST /login - Authenticate and get JWT token
- POST /logout - Logout (client-side token invalidation)

Requirement references:
- API-07: POST /api/v1/auth/register
- API-08: POST /api/v1/auth/login
- API-10: POST /api/v1/auth/logout
- AUTH-01, AUTH-02, AUTH-07
"""

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.core.auth import create_access_token, hash_password, verify_password
from app.core.exceptions import UserExistsException
from app.models.schemas import MessageResponse, Token, UserRegister
from app.models.user import create_user, get_user_by_email

router = APIRouter()


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister):
    """Register a new user account.

    Creates user in Neo4j and returns JWT access token.

    Args:
        user_data: Email and password for new account

    Returns:
        Token with access_token and token_type

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

    # Generate access token
    access_token = create_access_token(data={"sub": user_data.email})

    return Token(access_token=access_token, token_type="bearer")


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Authenticate user and return JWT token.

    Uses OAuth2PasswordRequestForm for compatibility with FastAPI docs
    and standard OAuth2 clients. Email is passed as 'username' field.

    Args:
        form_data: OAuth2 form with username (email) and password

    Returns:
        Token with access_token and token_type

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

    # Generate access token
    access_token = create_access_token(data={"sub": user["email"]})

    return Token(access_token=access_token, token_type="bearer")


@router.post("/logout", response_model=MessageResponse)
async def logout():
    """Logout current user.

    JWT is stateless - actual token invalidation is client-side.
    This endpoint exists for API completeness and to support
    client-side logout flows.

    NOTE: Server-side token invalidation (blocklist) planned for Phase 2+.

    Returns:
        MessageResponse confirming logout
    """
    return MessageResponse(message="Successfully logged out")
