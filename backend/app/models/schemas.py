"""Pydantic schemas for request/response validation.

Defines data models for API endpoints including:
- User registration and authentication
- Token responses
- Standard message responses
- Document upload and info
- Query request/response with citations
"""

from typing import List, Optional

from pydantic import BaseModel, EmailStr


class UserRegister(BaseModel):
    """Schema for user registration request."""

    email: EmailStr
    password: str


class Token(BaseModel):
    """Schema for JWT token response (legacy, single token)."""

    access_token: str
    token_type: str = "bearer"


class TokenPair(BaseModel):
    """Schema for JWT token pair response (access + refresh)."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    """Schema for refresh token request."""

    refresh_token: str


class UserResponse(BaseModel):
    """Schema for user data in responses (excludes password)."""

    id: str
    email: str


class UserContext(BaseModel):
    """User context for request - works for both authenticated and anonymous.

    This provides a unified interface for all API endpoints:
    - Authenticated users have email and role
    - Anonymous users have is_anonymous=True and session_created timestamp

    All database queries filter by 'id' regardless of auth state.
    """

    id: str  # User UUID or anonymous session ID
    email: Optional[str] = None
    is_anonymous: bool = False
    role: str = "user"  # "user", "admin", or "anonymous"
    session_created: Optional[str] = None  # ISO timestamp for anonymous sessions
    jti: Optional[str] = None  # JWT ID for logout operations


class MessageResponse(BaseModel):
    """Schema for simple message responses."""

    message: str


# Document schemas


class DocumentUploadResponse(BaseModel):
    """Schema for document upload response."""

    document_id: str
    filename: str
    status: str
    message: str


class DocumentInfo(BaseModel):
    """Schema for document information."""

    id: str
    filename: str
    upload_date: Optional[str] = None
    chunk_count: Optional[int] = None


# Query schemas


class QueryRequest(BaseModel):
    """Schema for document query request."""

    query: str
    max_results: int = 3


class Citation(BaseModel):
    """Schema for a source citation in query response."""

    document_id: str
    filename: str
    chunk_text: str
    relevance_score: float


class QueryResponse(BaseModel):
    """Schema for query response with answer and citations."""

    answer: str
    citations: List[Citation]


# Memory schemas


class MemoryAddRequest(BaseModel):
    """Schema for adding a memory."""

    content: str
    metadata: Optional[dict] = None


class MemorySearchRequest(BaseModel):
    """Schema for searching memories."""

    query: str
    limit: int = 5


class MemoryResponse(BaseModel):
    """Schema for a single memory in responses."""

    id: str
    memory: str
    metadata: Optional[dict] = None
    score: Optional[float] = None
    is_shared: Optional[bool] = None


class MemoryListResponse(BaseModel):
    """Schema for list of memories response."""

    memories: List[MemoryResponse]
    count: int
