"""Document upload and management endpoints.

Provides:
- POST /upload: Upload PDF or DOCX documents for processing
- GET /: List user's documents
- GET /{document_id}/status: Get document processing status
- GET /processing: Get all processing tasks for current user

Uses Celery for background processing — tasks survive server restarts.
Uses Redis for status tracking — status survives page refreshes.
Supports both authenticated and anonymous users via get_current_user_optional.
"""

import os
import tempfile
import uuid
from typing import List

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)

from app.config import settings
from app.core.security import get_current_user_optional
from app.db.qdrant_client import delete_by_document_id
from app.models.document import delete_document, get_document_by_id, get_user_documents
from app.models.schemas import (
    DocumentInfo,
    DocumentUploadResponse,
    MessageResponse,
    TaskStatusResponse,
    UserContext,
)
from app.utils.task_tracker import task_tracker

router = APIRouter()

# Allowed MIME types for document upload
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    current_user: UserContext = Depends(get_current_user_optional),
) -> DocumentUploadResponse:
    """Upload a PDF or DOCX document for processing.

    The document is saved to disk and a Celery task is dispatched
    for background processing. Returns immediately with document_id.

    Args:
        file: Uploaded file (PDF or DOCX).
        current_user: UserContext (authenticated or anonymous).

    Returns:
        DocumentUploadResponse with document_id and status.

    Raises:
        HTTPException 400: If file type not supported or file too large.
    """
    # Validate content type
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {file.content_type}. Only PDF and DOCX are allowed.",
        )

    # Check file size (read content to check size)
    content = await file.read()
    file_size_mb = len(content) / (1024 * 1024)
    if file_size_mb > settings.MAX_UPLOAD_SIZE_MB:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large: {file_size_mb:.1f}MB. Maximum size is {settings.MAX_UPLOAD_SIZE_MB}MB.",
        )

    # Generate document ID
    document_id = str(uuid.uuid4())
    user_id = current_user.id

    # Create task in Redis for status tracking (persists across refreshes)
    task_tracker.create(document_id, user_id, file.filename)

    # Save file to temp location for Celery worker to pick up
    ext = ".pdf" if file.content_type == "application/pdf" else ".docx"
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp_file:
        tmp_file.write(content)
        temp_path = tmp_file.name

    # Dispatch Celery task — runs in separate worker process
    from app.tasks import process_document_task

    process_document_task.delay(
        file_path=temp_path,
        document_id=document_id,
        user_id=user_id,
        filename=file.filename,
        file_size=len(content),
    )

    return DocumentUploadResponse(
        document_id=document_id,
        filename=file.filename,
        status="processing",
        message="Document uploaded and queued for processing.",
    )


@router.get("/", response_model=List[DocumentInfo])
async def list_documents(
    current_user: UserContext = Depends(get_current_user_optional),
) -> List[DocumentInfo]:
    """List all documents for the current user."""
    user_id = current_user.id
    documents = get_user_documents(user_id)
    return [DocumentInfo(**doc) for doc in documents]


@router.get("/processing", response_model=List[TaskStatusResponse])
async def get_processing_documents(
    current_user: UserContext = Depends(get_current_user_optional),
) -> List[TaskStatusResponse]:
    """Get all in-progress processing tasks for the current user.

    Called on page load to restore processing state after refresh.
    Reads from Redis so it survives server restarts.
    """
    user_id = current_user.id
    tasks = task_tracker.get_user_tasks(user_id)
    return [
        TaskStatusResponse(
            document_id=t["document_id"],
            status=t["status"],
            progress=t["progress"],
            message=t["message"],
            filename=t.get("filename"),
            error=t.get("error"),
        )
        for t in tasks
        if t["status"] not in ("completed", "failed")  # Only return active tasks
    ]


@router.get("/{document_id}/status", response_model=TaskStatusResponse)
async def get_document_status(
    document_id: str,
    current_user: UserContext = Depends(get_current_user_optional),
) -> TaskStatusResponse:
    """Get document processing status from Redis.

    Persists across server restarts and page refreshes.
    """
    user_id = current_user.id

    # Check Redis task tracker first (for in-progress documents)
    task = task_tracker.get(document_id)
    if task:
        # Verify ownership
        if task["user_id"] != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
            )
        return TaskStatusResponse(
            document_id=document_id,
            status=task["status"],
            progress=task["progress"],
            message=task["message"],
            filename=task.get("filename"),
            error=task.get("error"),
        )

    # Check if document exists in Neo4j (already processed)
    doc = get_document_by_id(document_id, user_id)
    if doc:
        return TaskStatusResponse(
            document_id=document_id,
            status="completed",
            progress=100,
            message="Document ready",
        )

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
    )


@router.delete("/{document_id}", response_model=MessageResponse)
async def delete_document_endpoint(
    document_id: str,
    current_user: UserContext = Depends(get_current_user_optional),
) -> MessageResponse:
    """Delete a document and all associated data."""
    user_id = current_user.id

    # Step 1: Verify ownership
    doc = get_document_by_id(document_id, user_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    # Step 2: Delete from Qdrant first
    delete_by_document_id(document_id)

    # Step 3: Delete from Neo4j
    deleted = delete_document(document_id, user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document from database"
        )

    # Clean up task tracker if still present
    task_tracker.remove(document_id)

    # Clean up pre-generated summaries from Redis
    from app.services.summary_storage import delete_summaries
    delete_summaries(document_id)

    return MessageResponse(message="Document deleted successfully")
