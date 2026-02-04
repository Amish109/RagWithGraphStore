"""Global exception handlers for consistent error responses.

Registers handlers for:
- RequestValidationError: Pydantic validation failures (422)
- HTTPException: Explicit API errors (various)
- Exception: Catch-all for unhandled errors (500)

CRITICAL: Never expose stack traces or internal details to users.
Log full details internally, return sanitized messages externally.
"""

import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.models.schemas import ErrorResponse

logger = logging.getLogger(__name__)


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle Pydantic validation errors with user-friendly messages."""
    # Extract first error for user message
    errors = exc.errors()
    if errors:
        first_error = errors[0]
        loc = first_error.get("loc", [])
        # Skip 'body' prefix if present
        field_parts = [str(x) for x in loc if x != "body"]
        field = ".".join(field_parts)
        msg = first_error.get("msg", "Invalid value")
        user_message = f"Invalid {field}: {msg}" if field else msg
    else:
        user_message = "Invalid request data"

    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            error="validation_error",
            message=user_message,
            detail=str(errors) if errors else None,
        ).model_dump(),
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle explicit HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=_status_to_error_type(exc.status_code),
            message=str(exc.detail),
        ).model_dump(),
        headers=getattr(exc, "headers", None),
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unhandled exceptions - log internally, sanitize externally.

    CRITICAL: Never expose internal details to users.
    """
    # Log full exception for debugging
    logger.exception(
        f"Unhandled exception on {request.method} {request.url.path}: {exc}"
    )

    # Return sanitized response
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="internal_error",
            message="An unexpected error occurred. Please try again later.",
        ).model_dump(),
    )


def _status_to_error_type(status_code: int) -> str:
    """Map HTTP status codes to error type strings."""
    mapping = {
        400: "bad_request",
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        409: "conflict",
        422: "validation_error",
        429: "rate_limited",
        500: "internal_error",
        503: "service_unavailable",
    }
    return mapping.get(status_code, "error")


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers on the FastAPI app."""
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
