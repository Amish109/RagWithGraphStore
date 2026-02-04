"""Memory API routes for user memory management.

Provides endpoints for:
- POST /memory - Add a fact to user's private memory
- POST /memory/search - Search memories with natural language
- GET /memory - List all user memories
- DELETE /memory/{id} - Delete a specific memory
- POST /memory/shared - Add to shared company memory (admin only)

Requirement references:
- MEM-01: Conversation history within sessions
- MEM-03: User preferences across sessions
- MEM-04: User can add arbitrary facts to private memory
- MEM-05: Admin can add facts to shared memory
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.rbac import require_admin
from app.core.security import get_current_user_optional
from app.models.schemas import (
    MemoryAddRequest,
    MemoryListResponse,
    MemoryResponse,
    MemorySearchRequest,
    UserContext,
)
from app.services.memory_service import (
    add_shared_memory,
    add_user_memory,
    delete_user_memory,
    get_user_memories,
    search_user_memories,
    search_with_shared,
)

router = APIRouter(prefix="/memory", tags=["memory"])


@router.post("/", response_model=dict)
async def add_memory(
    request: MemoryAddRequest,
    current_user: UserContext = Depends(get_current_user_optional),
):
    """Add a fact to user's private memory (MEM-04).

    Authenticated users: stored permanently with user ID.
    Anonymous users: stored with session ID (expires with session TTL).

    Args:
        request: MemoryAddRequest with content and optional metadata.
        current_user: UserContext from authentication.

    Returns:
        Dict with status, memory_id, and user_id.
    """
    result = await add_user_memory(
        user_id=current_user.id,
        content=request.content,
        metadata=request.metadata,
    )

    # Handle various Mem0 response formats
    memory_id = None
    if isinstance(result, dict):
        memory_id = result.get("id") or result.get("memory_id")
        # Sometimes Mem0 returns results as a list
        if "results" in result and result["results"]:
            memory_id = result["results"][0].get("id")
    elif isinstance(result, str):
        memory_id = result

    return {
        "status": "added",
        "memory_id": str(memory_id) if memory_id else "created",
        "user_id": current_user.id,
    }


@router.post("/search", response_model=MemoryListResponse)
async def search_memories(
    request: MemorySearchRequest,
    current_user: UserContext = Depends(get_current_user_optional),
):
    """Search user's memories with natural language query.

    For authenticated users, includes shared company memory.
    For anonymous users, only searches their session memory.

    Args:
        request: MemorySearchRequest with query and limit.
        current_user: UserContext from authentication.

    Returns:
        MemoryListResponse with matching memories and count.
    """
    # Include shared memory only for authenticated users
    include_shared = not current_user.is_anonymous

    results = await search_with_shared(
        user_id=current_user.id,
        query=request.query,
        limit=request.limit,
        include_shared=include_shared,
    )

    memories = [
        MemoryResponse(
            id=m.get("id", ""),
            memory=m.get("memory", m.get("text", "")),
            metadata=m.get("metadata"),
            score=m.get("score"),
            is_shared=m.get("is_shared"),
        )
        for m in results
    ]

    return MemoryListResponse(memories=memories, count=len(memories))


@router.get("/", response_model=MemoryListResponse)
async def list_memories(
    limit: int = 50,
    current_user: UserContext = Depends(get_current_user_optional),
):
    """List all user's memories.

    Returns all memories stored for the current user.

    Args:
        limit: Maximum number of memories to return.
        current_user: UserContext from authentication.

    Returns:
        MemoryListResponse with all user memories and count.
    """
    results = await get_user_memories(
        user_id=current_user.id,
        limit=limit,
    )

    memories = [
        MemoryResponse(
            id=m.get("id", ""),
            memory=m.get("memory", m.get("text", "")),
            metadata=m.get("metadata"),
        )
        for m in results
    ]

    return MemoryListResponse(memories=memories, count=len(memories))


@router.delete("/{memory_id}")
async def delete_memory(
    memory_id: str,
    current_user: UserContext = Depends(get_current_user_optional),
):
    """Delete a specific memory.

    Note: Mem0 doesn't enforce ownership at the API level.
    We trust user_id from authentication for isolation.

    Args:
        memory_id: ID of the memory to delete.
        current_user: UserContext from authentication.

    Returns:
        Dict with status and memory_id.

    Raises:
        HTTPException 404: If memory not found or deletion failed.
    """
    success = await delete_user_memory(
        user_id=current_user.id,
        memory_id=memory_id,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Memory not found or already deleted",
        )

    return {"status": "deleted", "memory_id": memory_id}


@router.post("/shared", response_model=dict)
async def add_shared_memory_endpoint(
    request: MemoryAddRequest,
    current_user: UserContext = Depends(require_admin),
):
    """Add a fact to shared company memory (MEM-05).

    ADMIN ONLY. All authenticated users can query this memory.
    Anonymous users cannot access shared memory.

    Args:
        request: MemoryAddRequest with content and optional metadata.
        current_user: UserContext (must be admin).

    Returns:
        Dict with status, memory_id, and scope.
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
