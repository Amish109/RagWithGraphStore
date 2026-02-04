"""Pydantic schemas for request/response validation.

Defines data models for API endpoints including:
- User registration and authentication
- Token responses
- Standard message responses
- Document upload and info
- Query request/response with citations
- Document comparison request/response
"""

from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


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
    summary: Optional[str] = None  # Auto-generated summary for quick reference


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


# Summary schemas


class SummaryResponse(BaseModel):
    """Schema for document summary response (QRY-06).

    Returned by GET /documents/{document_id}/summary endpoint.
    """

    document_id: str
    summary_type: str  # "brief", "detailed", "executive", "bullet"
    summary: str
    method: str  # "stuff" or "map_reduce"
    chunks_processed: Optional[int] = None  # Only for map_reduce


# Simplification schemas


class SimplifyRequest(BaseModel):
    """Schema for text simplification request (QRY-07).

    Used by POST /simplify endpoint.
    """

    text: str
    document_id: Optional[str] = None  # For context retrieval
    level: str = "general"  # eli5, general, professional


class SimplifyResponse(BaseModel):
    """Schema for text simplification response (QRY-07).

    Returned by POST /simplify endpoint.
    """

    original_text: str  # Truncated to 500 chars if longer
    simplified_text: str
    level: str
    level_description: str


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


# Error response schemas


class ErrorResponse(BaseModel):
    """Schema for standardized error responses.

    Used by global exception handlers to return consistent error format.
    All API errors use this schema for predictable client handling.
    """

    error: str  # Error type identifier (e.g., "validation_error", "not_found")
    message: str  # User-friendly message
    detail: Optional[str] = None  # Optional additional context


# Task status schemas


class TaskStatusResponse(BaseModel):
    """Schema for document processing status response.

    Used by GET /documents/{document_id}/status to report progress.
    Progress stages: pending(0%), extracting(10%), chunking(25%),
    embedding(40%), indexing(70%), summarizing(85%), completed(100%).
    """

    document_id: str
    status: str  # TaskStatus value (pending, extracting, chunking, etc.)
    progress: int  # 0-100 percentage
    message: str  # Human-readable status message
    error: Optional[str] = None  # Error details if status is "failed"


# Comparison schemas


class ComparisonRequest(BaseModel):
    """Request schema for document comparison.

    Used by POST /api/v1/compare to initiate document comparison workflow.
    Requires 2-5 document IDs and a comparison query.
    """

    document_ids: List[str] = Field(
        ...,
        min_length=2,
        max_length=5,
        description="IDs of documents to compare (2-5 documents)",
    )
    query: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="Comparison query or focus area",
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Session ID for multi-turn conversations",
    )


class ComparisonCitation(BaseModel):
    """Citation from a source document in comparison response.

    Provides attribution to specific document sections used in analysis.
    """

    document_id: str
    chunk_id: str
    filename: str
    text: str = Field(..., max_length=500, description="Cited text excerpt")


class ComparisonResponse(BaseModel):
    """Response schema for document comparison.

    Contains detailed analysis including similarities, differences,
    cross-document insights, and citations for attribution.
    """

    similarities: List[str]
    differences: List[str]
    cross_document_insights: List[str]
    response: str
    citations: List[ComparisonCitation]
    session_id: str
    status: str
