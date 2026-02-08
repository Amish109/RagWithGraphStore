"""Admin API routes for shared memory and document management.

Provides admin-only endpoints for:
- POST /admin/memory/shared - Add fact to company-wide shared memory
- GET /admin/memory/shared - List all shared memories
- DELETE /admin/memory/shared/{memory_id} - Delete a shared memory
- POST /admin/documents/upload - Upload shared knowledge document
- GET /admin/documents/ - List shared documents
- DELETE /admin/documents/{document_id} - Delete a shared document

All endpoints require admin role via require_admin dependency.

Requirement references:
- MEM-05: Admin can add facts to shared memory
- AUTH-08: Admin role for privileged operations
"""

import os
import tempfile
import uuid
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status

from app.config import settings
from app.core.rbac import require_admin
from app.db.qdrant_client import delete_by_document_id
from app.models.document import delete_document, get_user_documents
from app.models.schemas import (
    DocumentInfo,
    DocumentUploadResponse,
    MemoryAddRequest,
    MemoryListResponse,
    MemoryResponse,
    MessageResponse,
    UserContext,
)
from app.services.document_processor import process_document_pipeline
from app.services.memory_service import (
    add_shared_memory,
    delete_shared_memory,
    get_shared_memories,
)
from app.utils.task_tracker import task_tracker

router = APIRouter(prefix="/admin", tags=["admin"])

# Allowed MIME types for document upload
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


@router.post("/memory/shared", response_model=dict)
async def add_shared_memory_endpoint(
    request: MemoryAddRequest,
    current_user: UserContext = Depends(require_admin),
):
    """Add fact to shared company memory (MEM-05).

    ADMIN ONLY. All authenticated users can query this memory.
    Anonymous users cannot access shared memory.

    Args:
        request: MemoryAddRequest with content and optional metadata.
        current_user: UserContext (must be admin).

    Returns:
        Dict with status, memory_id, scope, and added_by fields.
    """
    result = await add_shared_memory(
        content=request.content,
        metadata=request.metadata,
    )

    # Handle various Mem0 response formats
    memory_id = None
    if isinstance(result, dict):
        memory_id = result.get("id") or result.get("memory_id")
        if "results" in result and result["results"]:
            memory_id = result["results"][0].get("id")
    elif isinstance(result, str):
        memory_id = result

    return {
        "status": "added",
        "memory_id": str(memory_id) if memory_id else "created",
        "scope": "shared",
        "added_by": current_user.email,
    }


@router.get("/memory/shared", response_model=MemoryListResponse)
async def list_shared_memories(
    limit: int = 50,
    current_user: UserContext = Depends(require_admin),
):
    """List all shared company memories.

    ADMIN ONLY. Returns all memories in the company-wide shared memory.

    Args:
        limit: Maximum number of memories to return.
        current_user: UserContext (must be admin).

    Returns:
        MemoryListResponse with all shared memories and count.
    """
    results = await get_shared_memories(limit=limit)

    memories = [
        MemoryResponse(
            id=m.get("id", ""),
            memory=m.get("memory", m.get("text", "")),
            metadata=m.get("metadata"),
            is_shared=True,
        )
        for m in results
    ]

    return MemoryListResponse(memories=memories, count=len(memories))


@router.delete("/memory/shared/{memory_id}")
async def delete_shared_memory_endpoint(
    memory_id: str,
    current_user: UserContext = Depends(require_admin),
):
    """Delete a shared memory.

    ADMIN ONLY. Removes a fact from company-wide shared memory.

    Args:
        memory_id: ID of the memory to delete.
        current_user: UserContext (must be admin).

    Returns:
        Dict with status and memory_id.

    Raises:
        HTTPException 404: If memory not found or deletion failed.
    """
    success = await delete_shared_memory(memory_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Memory not found or already deleted",
        )

    return {"status": "deleted", "memory_id": memory_id}


# --- Shared Document Endpoints ---


@router.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_shared_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: UserContext = Depends(require_admin),
) -> DocumentUploadResponse:
    """Upload a document as shared knowledge.

    ADMIN ONLY. The document is processed and stored with the shared sentinel
    user ID so all authenticated users' queries include these documents.

    Args:
        background_tasks: FastAPI background tasks.
        file: Uploaded file (PDF or DOCX).
        current_user: UserContext (must be admin).

    Returns:
        DocumentUploadResponse with document_id and status.
    """
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {file.content_type}. Only PDF and DOCX are allowed.",
        )

    content = await file.read()
    file_size_mb = len(content) / (1024 * 1024)
    if file_size_mb > settings.MAX_UPLOAD_SIZE_MB:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large: {file_size_mb:.1f}MB. Maximum is {settings.MAX_UPLOAD_SIZE_MB}MB.",
        )

    document_id = str(uuid.uuid4())
    shared_user_id = settings.SHARED_MEMORY_USER_ID

    task_tracker.create(document_id, shared_user_id, file.filename)

    ext = ".pdf" if file.content_type == "application/pdf" else ".docx"
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp_file:
        tmp_file.write(content)
        temp_path = tmp_file.name

    background_tasks.add_task(
        process_document_pipeline,
        file_path=temp_path,
        document_id=document_id,
        user_id=shared_user_id,
        filename=file.filename,
    )

    return DocumentUploadResponse(
        document_id=document_id,
        filename=file.filename,
        status="processing",
        message="Shared document uploaded and queued for processing.",
    )


@router.get("/documents/", response_model=List[DocumentInfo])
async def list_shared_documents(
    current_user: UserContext = Depends(require_admin),
) -> List[DocumentInfo]:
    """List all shared knowledge documents.

    ADMIN ONLY. Returns documents uploaded as shared knowledge.
    """
    documents = get_user_documents(settings.SHARED_MEMORY_USER_ID)
    return [DocumentInfo(**doc) for doc in documents]


@router.delete("/documents/{document_id}", response_model=MessageResponse)
async def delete_shared_document(
    document_id: str,
    current_user: UserContext = Depends(require_admin),
) -> MessageResponse:
    """Delete a shared knowledge document.

    ADMIN ONLY. Removes the document and its chunks from both stores.
    """
    shared_user_id = settings.SHARED_MEMORY_USER_ID

    from app.models.document import get_document_by_id

    doc = get_document_by_id(document_id, shared_user_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shared document not found",
        )

    delete_by_document_id(document_id)

    deleted = delete_document(document_id, shared_user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document from database",
        )

    task_tracker.remove(document_id)

    return MessageResponse(message="Shared document deleted successfully")
