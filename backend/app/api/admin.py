"""Admin API routes for shared memory management.

Provides admin-only endpoints for:
- POST /admin/memory/shared - Add fact to company-wide shared memory
- GET /admin/memory/shared - List all shared memories
- DELETE /admin/memory/shared/{memory_id} - Delete a shared memory

All endpoints require admin role via require_admin dependency.

Requirement references:
- MEM-05: Admin can add facts to shared memory
- AUTH-08: Admin role for privileged operations
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.rbac import require_admin
from app.models.schemas import (
    MemoryAddRequest,
    MemoryListResponse,
    MemoryResponse,
    UserContext,
)
from app.services.memory_service import (
    add_shared_memory,
    delete_shared_memory,
    get_shared_memories,
)

router = APIRouter(prefix="/admin", tags=["admin"])


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
