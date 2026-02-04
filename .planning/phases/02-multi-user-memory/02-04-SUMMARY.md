---
phase: 02-multi-user-memory
plan: 04
subsystem: memory
tags: [mem0, memory, api, user-isolation, conversation-history]
dependency-graph:
  requires:
    - 01-05 (Mem0 client configured)
    - 02-01 (refresh tokens for session management)
    - 02-02 (anonymous session management)
    - 02-03 (RBAC for admin shared memory)
  provides:
    - Memory service with user-isolated operations
    - Memory CRUD API endpoints
    - Conversation history tracking
    - Shared company memory (admin-only write)
  affects:
    - 02-05 (data migration uses memory service)
    - 02-06 (TTL cleanup deletes anonymous memories)
    - 03+ (query endpoints can use conversation context)
tech-stack:
  added: []
  patterns:
    - User isolation via user_id parameter
    - Sentinel user_id for shared memory (__shared__)
    - Metadata typing for memory categorization
key-files:
  created:
    - backend/app/services/memory_service.py
    - backend/app/api/memory.py
  modified:
    - backend/app/config.py
    - backend/app/models/schemas.py
    - backend/app/main.py
decisions:
  - decision: "SHARED_MEMORY_USER_ID = '__shared__' sentinel value"
    rationale: "Allows single-table design while isolating shared memory"
    tradeoff: "Must ensure no user ID collides with sentinel"
  - decision: "Anonymous users can use memory API"
    rationale: "Enables try-before-signup UX with personalization"
    tradeoff: "Anonymous memories expire with session TTL"
  - decision: "search_with_shared includes shared only for authenticated"
    rationale: "Anonymous users shouldn't access company knowledge"
    tradeoff: "Different behavior based on auth status"
metrics:
  duration: 4 min
  completed: 2026-02-04
---

# Phase 2 Plan 04: Memory Service and API Endpoints Summary

**One-liner:** Mem0-based memory service with user isolation and REST API for facts, preferences, and conversation history.

## What Was Built

Created a memory service that wraps Mem0 operations with user isolation via user_id parameter. The service provides functions for adding facts, searching memories, managing conversation history, and accessing shared company memory.

The REST API exposes memory operations:
- POST /api/v1/memory - Add facts to private memory
- POST /api/v1/memory/search - Semantic search over memories
- GET /api/v1/memory - List all user memories
- DELETE /api/v1/memory/{id} - Delete specific memory
- POST /api/v1/memory/shared - Add to shared memory (admin only)

Both authenticated and anonymous users can use the memory API. Anonymous users' memories are tied to their session ID and will expire with the session TTL.

## Key Technical Details

### Memory Service Functions
```python
# Private memory operations
add_user_memory(user_id, content, metadata)
search_user_memories(user_id, query, limit)
get_user_memories(user_id, limit)
delete_user_memory(user_id, memory_id)

# Conversation tracking
add_conversation_turn(user_id, session_id, role, content)
get_conversation_history(user_id, session_id, limit)
get_user_preferences(user_id)

# Shared memory (admin)
add_shared_memory(content, metadata)
search_with_shared(user_id, query, limit, include_shared)
```

### Memory Metadata Structure
```python
{
    "type": "fact" | "conversation" | "preference" | "shared",
    "added_at": "2026-02-04T14:00:00Z",
    "session_id": "optional-for-conversation",
    "role": "user|assistant-for-conversation"
}
```

### API Response Schemas
```python
MemoryResponse(id, memory, metadata, score, is_shared)
MemoryListResponse(memories: List[MemoryResponse], count: int)
```

### User Isolation Pattern
All memory operations require user_id parameter. For authenticated users, this is their UUID. For anonymous users, this is their session ID (anon_xxx format). Shared memory uses sentinel value `__shared__`.

## Deviations from Plan

None - plan executed exactly as written.

## Files Changed

| File | Change |
|------|--------|
| backend/app/config.py | Added SHARED_MEMORY_USER_ID setting |
| backend/app/services/memory_service.py | Created - All memory operations |
| backend/app/models/schemas.py | Added Memory* schemas |
| backend/app/api/memory.py | Created - Memory REST endpoints |
| backend/app/main.py | Added memory router to app |

## Verification Results

All verification commands passed:
- Memory service functions import successfully
- All schemas available
- Memory router has 5 routes
- Router registered in main.py

## Next Phase Readiness

- Plan 02-05 can use memory service for anonymous-to-authenticated data migration
- Plan 02-06 can use delete operations for TTL cleanup of expired memories
- Future query endpoints can use get_conversation_history for context
