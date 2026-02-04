"""Pydantic schemas for request/response validation.

Defines data models for API endpoints including:
- User registration and authentication
- Token responses
- Standard message responses
"""

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
