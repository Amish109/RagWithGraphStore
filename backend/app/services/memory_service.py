"""Memory service for Mem0-based user memory management.

Provides user-isolated memory operations:
- add_user_memory: Add arbitrary facts to private memory
- search_user_memories: Semantic search over memories
- get_user_memories: List all memories for a user
- delete_user_memory: Remove a specific memory
- add_conversation_turn: Track conversation history within sessions
- get_conversation_history: Retrieve session conversation history
- get_user_preferences: Get preference/fact memories for personalization

Following research Pattern 7 for Mem0 memory operations with user isolation.

CRITICAL: All operations use user_id parameter for multi-tenant isolation.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.db.mem0_client import get_mem0
from app.config import settings


async def add_user_memory(
    user_id: str,
    content: str,
    metadata: Optional[dict] = None
) -> dict:
    """Add a memory for a specific user (MEM-04).

    User can add arbitrary facts to their private memory.
    These influence future query responses through personalization.

    Args:
        user_id: User identifier for isolation (UUID or anon_xxx).
        content: The fact or information to store.
        metadata: Optional additional metadata.

    Returns:
        Dict containing the memory result from Mem0.
    """
    memory = get_mem0()

    result = memory.add(
        messages=content,
        user_id=user_id,
        metadata={
            **(metadata or {}),
            "type": "fact",
            "added_at": datetime.now(timezone.utc).isoformat()
        }
    )

    return result


async def search_user_memories(
    user_id: str,
    query: str,
    limit: int = 5
) -> List[dict]:
    """Search memories for a user.

    Returns relevant memories based on semantic search.
    Only searches within the user's private memory space.

    Args:
        user_id: User identifier for isolation.
        query: Natural language query to search for.
        limit: Maximum number of results to return.

    Returns:
        List of matching memories with relevance scores.
    """
    memory = get_mem0()

    results = memory.search(
        query=query,
        user_id=user_id,
        limit=limit
    )

    # Handle both list and dict responses from Mem0
    if isinstance(results, dict):
        return results.get("results", [])
    return results if isinstance(results, list) else []


async def get_user_memories(
    user_id: str,
    limit: int = 50
) -> List[dict]:
    """Get all memories for a user.

    Retrieves all stored memories for the specified user.

    Args:
        user_id: User identifier for isolation.
        limit: Maximum number of memories to return.

    Returns:
        List of all user memories.
    """
    memory = get_mem0()

    results = memory.get_all(user_id=user_id, limit=limit)

    # Handle both list and dict responses from Mem0
    if isinstance(results, dict):
        return results.get("results", [])
    return results if isinstance(results, list) else []


async def delete_user_memory(
    user_id: str,
    memory_id: str
) -> bool:
    """Delete a specific memory.

    NOTE: Mem0 has a known bug where deletion doesn't clean Neo4j
    (GitHub issue #3245). Orphan cleanup is handled by scheduled
    job in Plan 02-06.

    Args:
        user_id: User identifier (not currently enforced by Mem0).
        memory_id: ID of the memory to delete.

    Returns:
        True if deletion succeeded, False otherwise.
    """
    memory = get_mem0()

    try:
        memory.delete(memory_id)
        return True
    except Exception:
        return False


async def add_conversation_turn(
    user_id: str,
    session_id: str,
    role: str,  # "user" or "assistant"
    content: str
) -> dict:
    """Add a conversation turn to session history (MEM-01).

    Tracks conversation within a session for context.
    Used to maintain conversation history across browser refreshes.

    Args:
        user_id: User identifier for isolation.
        session_id: Session identifier (from cookie or auth).
        role: Who said this - "user" or "assistant".
        content: The message content.

    Returns:
        Dict containing the memory result from Mem0.
    """
    memory = get_mem0()

    result = memory.add(
        messages=content,
        user_id=user_id,
        metadata={
            "type": "conversation",
            "session_id": session_id,
            "role": role,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )

    return result


async def get_conversation_history(
    user_id: str,
    session_id: str,
    limit: int = 20
) -> List[dict]:
    """Get conversation history for a session (MEM-01).

    Returns recent conversation turns in chronological order.
    Used to provide context for follow-up questions.

    Args:
        user_id: User identifier for isolation.
        session_id: Session identifier to filter by.
        limit: Maximum number of turns to return.

    Returns:
        List of conversation turns sorted by timestamp.
    """
    memory = get_mem0()

    # Get all user memories
    all_memories = memory.get_all(user_id=user_id, limit=100)

    # Handle both list and dict responses
    if isinstance(all_memories, dict):
        memories = all_memories.get("results", [])
    else:
        memories = all_memories if isinstance(all_memories, list) else []

    # Filter by session_id and type=conversation
    session_memories = [
        m for m in memories
        if m.get("metadata", {}).get("session_id") == session_id
        and m.get("metadata", {}).get("type") == "conversation"
    ]

    # Sort by timestamp and limit
    session_memories.sort(key=lambda m: m.get("metadata", {}).get("timestamp", ""))

    return session_memories[-limit:]


async def get_user_preferences(user_id: str) -> List[dict]:
    """Get user preferences from memory (MEM-03).

    Returns memories marked as preferences or facts for
    cross-session personalization.

    Args:
        user_id: User identifier for isolation.

    Returns:
        List of preference/fact memories.
    """
    memory = get_mem0()

    all_memories = memory.get_all(user_id=user_id, limit=100)

    # Handle both list and dict responses
    if isinstance(all_memories, dict):
        memories = all_memories.get("results", [])
    else:
        memories = all_memories if isinstance(all_memories, list) else []

    # Filter for preference-type memories
    preferences = [
        m for m in memories
        if m.get("metadata", {}).get("type") in ["preference", "fact"]
    ]

    return preferences


async def add_shared_memory(
    content: str,
    metadata: Optional[dict] = None
) -> dict:
    """Add company-wide shared memory (MEM-05).

    ADMIN ONLY. All authenticated users can query but not modify.
    Uses sentinel user_id to mark as shared.

    Args:
        content: The fact or information to store.
        metadata: Optional additional metadata.

    Returns:
        Dict containing the memory result from Mem0.
    """
    memory = get_mem0()

    result = memory.add(
        messages=content,
        user_id=settings.SHARED_MEMORY_USER_ID,
        metadata={
            **(metadata or {}),
            "type": "shared",
            "scope": "company",
            "added_at": datetime.now(timezone.utc).isoformat()
        }
    )

    return result


async def search_with_shared(
    user_id: str,
    query: str,
    limit: int = 5,
    include_shared: bool = True
) -> List[dict]:
    """Search memories including shared company memory.

    Searches user's private memories first, then optionally
    includes shared company memory.

    Args:
        user_id: User identifier for private memory.
        query: Natural language query to search for.
        limit: Maximum number of results to return.
        include_shared: Whether to include shared memory results.

    Returns:
        List of matching memories, user memories prioritized.
    """
    memory = get_mem0()

    # Search user's private memories
    user_results = memory.search(
        query=query,
        user_id=user_id,
        limit=limit
    )

    # Handle response format
    if isinstance(user_results, dict):
        results = user_results.get("results", [])
    else:
        results = user_results if isinstance(user_results, list) else []

    # Mark personal memories
    for r in results:
        r["is_shared"] = False

    if include_shared:
        # Also search shared company memory
        shared_results = memory.search(
            query=query,
            user_id=settings.SHARED_MEMORY_USER_ID,
            limit=limit
        )

        # Handle response format
        if isinstance(shared_results, dict):
            shared_memories = shared_results.get("results", [])
        else:
            shared_memories = shared_results if isinstance(shared_results, list) else []

        # Append shared results (lower priority)
        for mem in shared_memories:
            mem["is_shared"] = True
            results.append(mem)

    # Return more results when including shared (up to double the limit)
    return results[:limit * 2] if include_shared else results[:limit]


async def get_shared_memories(limit: int = 50) -> List[dict]:
    """Get all shared company memories.

    ADMIN ONLY - used for listing shared memories in admin panel.

    Args:
        limit: Maximum number of memories to return.

    Returns:
        List of all shared company memories.
    """
    memory = get_mem0()

    results = memory.get_all(user_id=settings.SHARED_MEMORY_USER_ID, limit=limit)

    # Handle both list and dict responses from Mem0
    if isinstance(results, dict):
        return results.get("results", [])
    return results if isinstance(results, list) else []


async def delete_shared_memory(memory_id: str) -> bool:
    """Delete a shared memory.

    ADMIN ONLY - removes a fact from company-wide memory.

    NOTE: Mem0 has a known bug where deletion doesn't clean Neo4j
    (GitHub issue #3245). Orphan cleanup is handled by scheduled job.

    Args:
        memory_id: ID of the shared memory to delete.

    Returns:
        True if deletion succeeded, False otherwise.
    """
    memory = get_mem0()

    try:
        memory.delete(memory_id)
        return True
    except Exception:
        return False
