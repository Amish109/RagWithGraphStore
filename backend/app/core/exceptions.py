"""Custom exception classes for authentication and authorization errors."""

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
