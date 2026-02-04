"""Custom exception classes for authentication, authorization, and domain errors.

Provides structured exceptions for:
- Authentication: CredentialsException, UserExistsException
- Documents: DocumentNotFoundError, DocumentProcessingError
- Queries: QueryGenerationError

All exceptions extend HTTPException for consistent FastAPI handling.
"""

from fastapi import HTTPException, status


class CredentialsException(HTTPException):
    """Exception raised when credentials validation fails."""

    def __init__(self, detail: str = "Could not validate credentials"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class UserExistsException(HTTPException):
    """Exception raised when attempting to register an existing email."""

    def __init__(self, detail: str = "Email already registered"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        )


# Document exceptions


class DocumentNotFoundError(HTTPException):
    """Raised when document not found or not owned by user."""

    def __init__(self, document_id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document not found: {document_id}",
        )


class DocumentProcessingError(HTTPException):
    """Raised when document processing fails."""

    def __init__(self, message: str = "Document processing failed"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=message,
        )


# Query exceptions


class QueryGenerationError(HTTPException):
    """Raised when LLM query generation fails."""

    def __init__(self, message: str = "Failed to generate response"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=message,
        )
