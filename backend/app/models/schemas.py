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
    """Schema for JWT token response."""

    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """Schema for user data in responses (excludes password)."""

    id: str
    email: str


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
