"""Document upload and management endpoints.

Provides:
- POST /upload: Upload PDF or DOCX documents for processing
- GET /: List user's documents
- GET /{document_id}/status: Get document processing status

Following research Pattern 6: Document Upload with Async Processing.
Supports both authenticated and anonymous users via get_current_user_optional.
"""

import os
import tempfile
import uuid
from typing import List

from fastapi import (
    APIRouter,
    BackgroundTasks,
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
from app.services.document_processor import process_document_pipeline
from app.utils.task_tracker import task_tracker

router = APIRouter()

# Allowed MIME types for document upload
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: UserContext = Depends(get_current_user_optional),
) -> DocumentUploadResponse:
    """Upload a PDF or DOCX document for processing.

    The document will be processed in the background:
    1. Text extraction (PDF or DOCX)
    2. Semantic chunking
    3. Embedding generation
    4. Storage in Neo4j (metadata) and Qdrant (vectors)

    Implements requirements API-01, DOC-01, DOC-02.
    Supports both authenticated and anonymous users.

    Args:
        background_tasks: FastAPI background tasks.
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
    user_id = current_user.id  # Works for both authenticated and anonymous

    # Create task for status tracking
    task_tracker.create(document_id, user_id, file.filename)

    # Save file to temp location for background processing
    # Use appropriate extension based on content type
    ext = ".pdf" if file.content_type == "application/pdf" else ".docx"
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp_file:
        tmp_file.write(content)
        temp_path = tmp_file.name

    # Add document processing to background tasks
    # This avoids blocking the API response (Pitfall #7)
    background_tasks.add_task(
        process_document_pipeline,
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
    """List all documents for the current user.

    Works for both authenticated and anonymous users.

    Args:
        current_user: UserContext (authenticated or anonymous).

    Returns:
        List of DocumentInfo for user's documents.
    """
    user_id = current_user.id  # Works for both authenticated and anonymous
    documents = get_user_documents(user_id)
    return [DocumentInfo(**doc) for doc in documents]


@router.get("/{document_id}/status", response_model=TaskStatusResponse)
async def get_document_status(
    document_id: str,
    current_user: UserContext = Depends(get_current_user_optional),
) -> TaskStatusResponse:
    """Get document processing status.

    Returns current processing stage and progress percentage.
    If document is fully processed and not in task tracker,
    returns completed status.

    Args:
        document_id: UUID of the document.
        current_user: UserContext (authenticated or anonymous).

    Returns:
        TaskStatusResponse with status, progress, and message.

    Raises:
        HTTPException 404: If document not found.
    """
    user_id = current_user.id

    # Check task tracker first (for in-progress documents)
    task = task_tracker.get(document_id)
    if task:
        # Verify ownership
        if task.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
            )
        return TaskStatusResponse(
            document_id=document_id,
            status=task.status.value,
            progress=task.progress,
            message=task.message,
            error=task.error,
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
    """Delete a document and all associated data.

    Implements MGMT-02: Document deletion with cascade.

    CRITICAL: Order matters for consistency (Pitfall #2):
    1. Verify ownership in Neo4j
    2. Delete from Qdrant first (no rollback available)
    3. Delete from Neo4j (transactional)

    If Neo4j deletion fails after Qdrant, vectors are orphaned
    but that's safer than orphaned Neo4j data with missing vectors.

    Args:
        document_id: UUID of the document to delete.
        current_user: Authenticated or anonymous user from JWT/session.

    Returns:
        MessageResponse confirming deletion.

    Raises:
        HTTPException 404: If document not found or not owned by user.
    """
    user_id = current_user.id

    # Step 1: Verify ownership
    doc = get_document_by_id(document_id, user_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    # Step 2: Delete from Qdrant first
    # (Qdrant has no transaction support, so do it first)
    delete_by_document_id(document_id)

    # Step 3: Delete from Neo4j
    deleted = delete_document(document_id, user_id)
    if not deleted:
        # This shouldn't happen if ownership check passed,
        # but handle gracefully
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document from database"
        )

    # Clean up task tracker if still present
    task_tracker.remove(document_id)

    return MessageResponse(message="Document deleted successfully")
