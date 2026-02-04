"""Document upload and management endpoints.

Provides:
- POST /upload: Upload PDF or DOCX documents for processing
- GET /: List user's documents

Following research Pattern 6: Document Upload with Async Processing.
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
from app.core.security import get_current_user
from app.models.document import get_user_documents
from app.models.schemas import DocumentInfo, DocumentUploadResponse
from app.services.document_processor import process_document_pipeline

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
    current_user: dict = Depends(get_current_user),
) -> DocumentUploadResponse:
    """Upload a PDF or DOCX document for processing.

    The document will be processed in the background:
    1. Text extraction (PDF or DOCX)
    2. Semantic chunking
    3. Embedding generation
    4. Storage in Neo4j (metadata) and Qdrant (vectors)

    Implements requirements API-01, DOC-01, DOC-02.

    Args:
        background_tasks: FastAPI background tasks.
        file: Uploaded file (PDF or DOCX).
        current_user: Authenticated user from JWT.

    Returns:
        DocumentUploadResponse with document_id and status.

    Raises:
        HTTPException 400: If file type not supported or file too large.
        HTTPException 401: If not authenticated.
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
    user_id = current_user["id"]

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
    )

    return DocumentUploadResponse(
        document_id=document_id,
        filename=file.filename,
        status="processing",
        message="Document uploaded and queued for processing.",
    )


@router.get("/", response_model=List[DocumentInfo])
async def list_documents(
    current_user: dict = Depends(get_current_user),
) -> List[DocumentInfo]:
    """List all documents for the current user.

    Args:
        current_user: Authenticated user from JWT.

    Returns:
        List of DocumentInfo for user's documents.
    """
    user_id = current_user["id"]
    documents = get_user_documents(user_id)
    return [DocumentInfo(**doc) for doc in documents]
