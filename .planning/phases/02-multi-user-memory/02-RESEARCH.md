# Phase 2: Multi-User Core & Memory Integration - Research

**Researched:** 2026-02-04
**Domain:** Multi-tenant isolation, Mem0 memory integration, anonymous/authenticated session management, RBAC
**Confidence:** HIGH

## Summary

Phase 2 transforms the single-user RAG foundation into a secure multi-tenant system with persistent memory. This phase is security-critical: multi-tenant isolation failures cause data breaches (Pitfall #4), memory deletion bugs leave orphaned data (Pitfall #2), and JWT vulnerabilities enable account takeover (Pitfall #5). The research identified that Mem0's `user_id`, `agent_id`, and `app_id` parameters provide the isolation primitives needed, but query-time filtering must be enforced at every access point - not just in application code.

The standard approach for Phase 2 is: Redis for refresh token storage and token blocklist, Mem0 with separate "memory" collection (distinct from "documents"), RBAC via FastAPI dependency injection with role checking, anonymous sessions using temporary UUIDs with cookie-based tracking, and data migration on registration via atomic transaction (update user_id across Neo4j and Qdrant). The critical insight is that authentication is NOT isolation - every database query must include tenant filtering regardless of authentication status.

**Primary recommendation:** Implement defense-in-depth for multi-tenant isolation: (1) JWT contains user_id, (2) middleware validates and injects user context, (3) every database query includes user_id filter, (4) cross-tenant access tests run in CI. For memory integration, use Mem0's `user_id` parameter consistently and create a separate "memory" Qdrant collection. For admin shared memory, use a sentinel value (e.g., `user_id="__shared__"`) that all authenticated users can query but only admins can write.

## Standard Stack

The established libraries/tools for Phase 2:

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| redis (redis-py) | >=5.0.0 | Async Redis client | Official Redis client with native async support. For token blocklist, refresh token storage, session management. |
| mem0ai | >=1.0.3 | Memory management | Handles user_id, agent_id scoping. v1.0+ has improved vector store support. Use v2 API (v1 deprecated). |
| aioredis | n/a | DEPRECATED | Use `redis.asyncio` from redis-py instead. aioredis merged into redis-py. |
| pyjwt | latest | JWT with refresh tokens | Extend Phase 1 auth. Add refresh token rotation, token blocklist support. |
| apscheduler | >=3.10.0 | Background job scheduling | For TTL cleanup jobs (anonymous data expiration). Lightweight, integrates with FastAPI. |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| uuid | stdlib | UUID generation | Generate anonymous session IDs, refresh token IDs (jti). |
| hashlib | stdlib | Token hashing | SHA-256 hash refresh tokens before Redis storage (security). |
| croniter | latest | Cron expression parsing | If using cron-style scheduling for cleanup jobs. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Redis (token blocklist) | PostgreSQL | PostgreSQL slower for high-frequency lookups. Redis designed for this use case. |
| Redis (token blocklist) | In-memory dict | Lost on restart. Unacceptable for production token revocation. |
| APScheduler | Celery | Celery is heavyweight for simple scheduled jobs. APScheduler sufficient for cleanup. |
| Custom RBAC | fastapi-user-auth | External library adds dependency. Custom RBAC simpler for 2-role system (user/admin). |
| Session cookies | localStorage | Cookies with httpOnly flag prevent XSS token theft. localStorage vulnerable. |

**Installation:**
```bash
# Token management
pip install "redis>=5.0.0"

# Memory (already from Phase 1, verify version)
pip install "mem0ai>=1.0.3"

# Scheduling
pip install "apscheduler>=3.10.0"

# Phase 1 (verify installed)
# pyjwt, neo4j, qdrant-client already installed
```

## Architecture Patterns

### Recommended Additional Structure (Phase 2)
```
backend/app/
├── core/
│   ├── auth.py              # EXTEND: refresh tokens, blocklist
│   ├── security.py          # EXTEND: get_current_user_optional, require_role
│   ├── rbac.py              # NEW: role checking dependencies
│   └── session.py           # NEW: anonymous session management
├── db/
│   ├── redis_client.py      # NEW: Redis connection, blocklist ops
│   └── mem0_client.py       # EXTEND: full memory operations
├── services/
│   ├── memory_service.py    # NEW: user memory CRUD
│   ├── session_service.py   # NEW: anonymous session handling
│   └── migration_service.py # NEW: anon-to-user data migration
├── api/
│   ├── auth.py              # EXTEND: refresh, logout with blocklist
│   ├── memory.py            # NEW: memory endpoints
│   └── admin.py             # NEW: admin-only endpoints
└── jobs/
    └── cleanup.py           # NEW: scheduled cleanup tasks
```

### Pattern 1: Redis Connection with Connection Pool

**What:** Async Redis client with connection pooling for token blocklist and session storage.

**When to use:** Phase 2 initialization, used throughout for token operations.

**Example:**
```python
# app/db/redis_client.py
import redis.asyncio as redis
from app.config import settings

# Connection pool for efficient reuse
redis_pool = redis.ConnectionPool.from_url(
    settings.REDIS_URL,
    max_connections=50,
    decode_responses=True
)

async def get_redis() -> redis.Redis:
    """Get Redis client from connection pool.

    Use as FastAPI dependency:
    async def endpoint(redis: redis.Redis = Depends(get_redis)):
    """
    return redis.Redis(connection_pool=redis_pool)

async def close_redis():
    """Close Redis connection pool on shutdown."""
    await redis_pool.disconnect()

# Token blocklist operations
JTI_EXPIRY_SECONDS = 3600 * 24 * 7  # 7 days (match refresh token lifetime)

async def add_token_to_blocklist(jti: str, redis_client: redis.Redis) -> None:
    """Add JWT ID to blocklist (for logout/revocation).

    CRITICAL: Use TTL to auto-expire entries. Without TTL, blocklist grows unbounded.
    """
    await redis_client.setex(
        f"blocklist:{jti}",
        JTI_EXPIRY_SECONDS,
        "1"
    )

async def is_token_blocklisted(jti: str, redis_client: redis.Redis) -> bool:
    """Check if token is blocklisted (revoked)."""
    return await redis_client.exists(f"blocklist:{jti}") > 0
```

**Critical:**
1. Use `redis.asyncio` (not deprecated aioredis).
2. Always set TTL on blocklist entries to prevent unbounded growth.
3. Use connection pooling for production efficiency.

**Sources:**
- [redis-py async documentation](https://redis-py.readthedocs.io/en/stable/examples/asyncio_examples.html)
- [FastAPI + Redis example](https://medium.com/@geetansh2k1/setting-up-and-using-an-async-redis-client-in-fastapi-the-right-way-0409ad3812e6)

### Pattern 2: Refresh Token Rotation with Secure Storage

**What:** Implement refresh token rotation where each refresh generates new tokens and invalidates old ones.

**When to use:** Phase 2 authentication enhancement (AUTH-06).

**Example:**
```python
# app/core/auth.py (extend from Phase 1)
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
import jwt
from app.config import settings

REFRESH_TOKEN_EXPIRE_DAYS = 7

def create_token_pair(user_email: str, user_id: str) -> Tuple[str, str, str]:
    """Create access token and refresh token pair.

    Returns: (access_token, refresh_token, jti)
    """
    jti = secrets.token_urlsafe(32)  # Unique token ID

    # Access token (short-lived)
    access_token = create_access_token(
        data={"sub": user_email, "user_id": user_id, "jti": jti}
    )

    # Refresh token (long-lived)
    refresh_expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    refresh_payload = {
        "sub": user_email,
        "user_id": user_id,
        "jti": jti,
        "exp": refresh_expire,
        "type": "refresh"
    }
    refresh_token = jwt.encode(refresh_payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    return access_token, refresh_token, jti

def hash_refresh_token(token: str) -> str:
    """Hash refresh token for secure storage.

    SECURITY: Never store raw refresh tokens. Hash with SHA-256.
    """
    return hashlib.sha256(token.encode()).hexdigest()

async def store_refresh_token(
    user_id: str,
    jti: str,
    token_hash: str,
    redis_client
) -> None:
    """Store hashed refresh token in Redis.

    Key: refresh:{user_id}:{jti}
    Value: token_hash
    TTL: REFRESH_TOKEN_EXPIRE_DAYS
    """
    await redis_client.setex(
        f"refresh:{user_id}:{jti}",
        REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
        token_hash
    )

async def validate_and_rotate_refresh_token(
    refresh_token: str,
    redis_client
) -> Optional[Tuple[str, str, str]]:
    """Validate refresh token and issue new pair.

    SECURITY: Each refresh token can only be used once.
    Detects token theft: if attacker uses stolen token, legitimate user's
    next refresh fails, alerting to compromise.

    Returns: (new_access_token, new_refresh_token, new_jti) or None if invalid
    """
    try:
        payload = jwt.decode(
            refresh_token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )

        if payload.get("type") != "refresh":
            return None

        user_email = payload.get("sub")
        user_id = payload.get("user_id")
        jti = payload.get("jti")

        # Check if token was already used (rotation)
        stored_hash = await redis_client.get(f"refresh:{user_id}:{jti}")
        if stored_hash is None:
            # Token already rotated or never existed - possible theft
            return None

        # Verify hash matches
        if stored_hash != hash_refresh_token(refresh_token):
            return None

        # Invalidate old token
        await redis_client.delete(f"refresh:{user_id}:{jti}")

        # Issue new pair
        new_access, new_refresh, new_jti = create_token_pair(user_email, user_id)
        await store_refresh_token(user_id, new_jti, hash_refresh_token(new_refresh), redis_client)

        return new_access, new_refresh, new_jti

    except jwt.InvalidTokenError:
        return None
```

**Critical:**
1. Hash refresh tokens before storage (SHA-256).
2. Delete old token on rotation - single use prevents replay.
3. TTL on Redis keys ensures cleanup.
4. Include "type": "refresh" to distinguish from access tokens.

**Sources:**
- [JWT Refresh Tokens Explained - FastAPI](https://medium.com/@jagan_reddy/jwt-in-fastapi-the-secure-way-refresh-tokens-explained-f7d2d17b1d17)
- [Refresh Token Rotation Best Practices](https://www.serverion.com/uncategorized/refresh-token-rotation-best-practices-for-developers/)

### Pattern 3: Anonymous Session Management

**What:** Generate temporary session IDs for unauthenticated users, track via HTTP-only cookies.

**When to use:** AUTH-03 (anonymous users get temporary session).

**Example:**
```python
# app/core/session.py
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Request, Response

ANONYMOUS_SESSION_EXPIRE_DAYS = 7  # Configurable
ANONYMOUS_PREFIX = "anon_"

def generate_anonymous_session_id() -> str:
    """Generate unique anonymous session ID.

    Format: anon_{random_32_chars}
    Prefix distinguishes from authenticated user UUIDs.
    """
    return f"{ANONYMOUS_PREFIX}{secrets.token_urlsafe(24)}"

def is_anonymous_session(session_id: str) -> bool:
    """Check if session ID is anonymous."""
    return session_id.startswith(ANONYMOUS_PREFIX)

def set_session_cookie(response: Response, session_id: str, max_age_days: int = 7) -> None:
    """Set HTTP-only session cookie.

    SECURITY: httponly prevents XSS, secure requires HTTPS, samesite prevents CSRF.
    """
    response.set_cookie(
        key="session_id",
        value=session_id,
        max_age=max_age_days * 24 * 3600,
        httponly=True,
        secure=True,  # HTTPS only in production
        samesite="lax"
    )

def get_session_from_request(request: Request) -> Optional[str]:
    """Extract session ID from cookie."""
    return request.cookies.get("session_id")

# app/core/security.py (extend)
from fastapi import Depends, Request, Response
from typing import Optional

async def get_current_user_optional(
    request: Request,
    response: Response,
    token: Optional[str] = Depends(oauth2_scheme_optional)
) -> dict:
    """Get current user or create anonymous session.

    Returns user dict with 'id' key. For anonymous users:
    - id: anonymous session ID (anon_xxx)
    - is_anonymous: True
    - session_created: timestamp

    CRITICAL: Anonymous and authenticated users use SAME interface.
    All queries filter by user['id'] regardless of auth status.
    """
    if token:
        # Try to validate JWT
        payload = decode_access_token(token)
        if payload:
            user = get_user_by_email(payload.get("sub"))
            if user:
                user["is_anonymous"] = False
                return user

    # No valid token - use/create anonymous session
    session_id = get_session_from_request(request)

    if not session_id or not is_anonymous_session(session_id):
        # Create new anonymous session
        session_id = generate_anonymous_session_id()
        set_session_cookie(response, session_id)

    return {
        "id": session_id,
        "is_anonymous": True,
        "session_created": datetime.now(timezone.utc).isoformat()
    }
```

**Critical:**
1. Anonymous sessions use same `id` field as authenticated users.
2. All database queries filter by `user_id` - works identically for both.
3. HTTP-only cookies prevent JavaScript access (XSS protection).
4. Session ID format distinguishes anonymous from authenticated.

**Sources:**
- [OWASP Session Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)
- [SuperTokens Anonymous Sessions](https://supertokens.com/docs/post-authentication/session-management/advanced-workflows/anonymous-session)

### Pattern 4: Anonymous to Authenticated Data Migration

**What:** When anonymous user registers, migrate all their documents and memories to permanent account.

**When to use:** AUTH-04 (anonymous data migrates on registration).

**Example:**
```python
# app/services/migration_service.py
from typing import List
from app.db.neo4j_client import neo4j_driver
from app.db.qdrant_client import qdrant_client
from app.db.mem0_client import get_mem0
from app.config import settings

async def migrate_anonymous_to_user(
    anonymous_id: str,
    new_user_id: str
) -> dict:
    """Migrate all anonymous user data to authenticated account.

    Steps:
    1. Update Neo4j: Change user_id on all Documents and Chunks
    2. Update Qdrant: Change user_id payload on all vectors
    3. Update Mem0: Transfer memories to new user_id

    CRITICAL: This must be atomic. If any step fails, rollback.

    Returns: Migration stats (documents_migrated, chunks_migrated, memories_migrated)
    """
    stats = {"documents": 0, "chunks": 0, "memories": 0}

    # Step 1: Migrate Neo4j data
    with neo4j_driver.session(database=settings.NEO4J_DATABASE) as session:
        # Get all documents owned by anonymous user
        result = session.run("""
            MATCH (d:Document {user_id: $old_id})
            SET d.user_id = $new_id
            WITH d
            MATCH (d)-[:CONTAINS]->(c:Chunk)
            RETURN count(DISTINCT d) as doc_count, count(c) as chunk_count
        """, old_id=anonymous_id, new_id=new_user_id)

        record = result.single()
        if record:
            stats["documents"] = record["doc_count"]
            stats["chunks"] = record["chunk_count"]

    # Step 2: Migrate Qdrant vectors (update payload)
    # Qdrant doesn't support bulk payload updates, need to scroll and update
    from qdrant_client.models import Filter, FieldCondition, MatchValue, SetPayload

    # Get all point IDs for anonymous user
    scroll_result = qdrant_client.scroll(
        collection_name=settings.QDRANT_COLLECTION,
        scroll_filter=Filter(
            must=[FieldCondition(key="user_id", match=MatchValue(value=anonymous_id))]
        ),
        limit=1000,
        with_payload=False,
        with_vectors=False
    )

    point_ids = [point.id for point in scroll_result[0]]

    if point_ids:
        # Update payload for all points
        qdrant_client.set_payload(
            collection_name=settings.QDRANT_COLLECTION,
            payload={"user_id": new_user_id},
            points=point_ids
        )

    # Step 3: Migrate Mem0 memories
    # Mem0 stores memories with user_id - need to transfer
    memory = get_mem0()

    # Get all memories for anonymous user
    old_memories = memory.get_all(user_id=anonymous_id)

    if old_memories:
        for mem in old_memories:
            # Re-add with new user_id (Mem0 doesn't support user_id update)
            memory.add(
                messages=mem.get("memory", ""),
                user_id=new_user_id,
                metadata=mem.get("metadata", {})
            )
            # Delete old memory
            memory.delete(mem["id"])

        stats["memories"] = len(old_memories)

    return stats
```

**Critical:**
1. Migration should be transactional - partial migration is worse than none.
2. Qdrant doesn't have bulk payload update - scroll and update.
3. Mem0 doesn't support user_id change - must copy and delete.
4. Run migration immediately after registration, before returning success.

**Sources:**
- [MoEngage Anonymous to Registered User Merge](https://help.moengage.com/hc/en-us/articles/12088416349460-Anonymous-to-Registered-User-Merge)
- [OWASP Session ID Regeneration](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)

### Pattern 5: Automatic Data Expiration (TTL)

**What:** Automatically delete anonymous user data after configured period.

**When to use:** AUTH-05 (temporary data expires after configured time).

**Example:**
```python
# app/jobs/cleanup.py
from datetime import datetime, timedelta, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.db.neo4j_client import neo4j_driver
from app.db.qdrant_client import qdrant_client
from app.db.mem0_client import get_mem0
from app.config import settings

ANONYMOUS_DATA_TTL_DAYS = 7  # Configurable

async def cleanup_expired_anonymous_data():
    """Delete anonymous user data older than TTL.

    Runs on schedule (e.g., daily). Cleans:
    1. Neo4j: Documents, Chunks with anon_ user_id older than TTL
    2. Qdrant: Vectors with anon_ user_id older than TTL
    3. Mem0: Memories for anon_ users (harder - no timestamp filter)

    CRITICAL: Use index on created_at/upload_date for efficient queries.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=ANONYMOUS_DATA_TTL_DAYS)

    # Step 1: Delete expired Neo4j data
    with neo4j_driver.session(database=settings.NEO4J_DATABASE) as session:
        # Delete chunks first (they reference documents)
        session.run("""
            MATCH (d:Document)-[:CONTAINS]->(c:Chunk)
            WHERE d.user_id STARTS WITH 'anon_'
            AND d.upload_date < datetime($cutoff)
            DETACH DELETE c
        """, cutoff=cutoff.isoformat())

        # Delete documents
        result = session.run("""
            MATCH (d:Document)
            WHERE d.user_id STARTS WITH 'anon_'
            AND d.upload_date < datetime($cutoff)
            DETACH DELETE d
            RETURN count(d) as deleted_count
        """, cutoff=cutoff.isoformat())

        deleted_docs = result.single()["deleted_count"]

    # Step 2: Delete expired Qdrant vectors
    # Qdrant: Filter by user_id prefix and timestamp
    from qdrant_client.models import Filter, FieldCondition, MatchValue, Range

    # Delete points matching filter
    qdrant_client.delete(
        collection_name=settings.QDRANT_COLLECTION,
        points_selector=Filter(
            must=[
                FieldCondition(
                    key="user_id",
                    match=MatchValue(value="anon_")  # Prefix match via custom logic
                ),
                FieldCondition(
                    key="created_at",
                    range=Range(lt=cutoff.timestamp())
                )
            ]
        )
    )

    print(f"Cleanup complete: {deleted_docs} documents deleted")

def setup_cleanup_scheduler():
    """Initialize cleanup job scheduler."""
    scheduler = AsyncIOScheduler()

    # Run daily at 3 AM
    scheduler.add_job(
        cleanup_expired_anonymous_data,
        'cron',
        hour=3,
        minute=0
    )

    scheduler.start()
    return scheduler
```

**Critical:**
1. Add `created_at` or `upload_date` to all records for TTL queries.
2. Index timestamp fields in Neo4j for efficient cleanup.
3. Qdrant filter by timestamp requires adding timestamp to payload.
4. Consider batch deletion to avoid long-running transactions.

**Note:** Qdrant doesn't have native TTL. Use scheduled job + filter deletion.

**Sources:**
- [Neo4j APOC TTL](https://neo4j.com/labs/apoc/5/graph-updates/ttl/)
- [Qdrant Cleanup Discussion](https://github.com/orgs/qdrant/discussions/5441)

### Pattern 6: Role-Based Access Control (RBAC)

**What:** Implement admin vs. user role checking via FastAPI dependencies.

**When to use:** AUTH-08 (admin role), MEM-05 (admin shared memory).

**Example:**
```python
# app/core/rbac.py
from enum import Enum
from functools import wraps
from fastapi import Depends, HTTPException, status
from app.core.security import get_current_user

class Role(str, Enum):
    USER = "user"
    ADMIN = "admin"

class RoleChecker:
    """Dependency for role-based access control.

    Usage:
    @router.post("/admin-only")
    async def admin_endpoint(user = Depends(RoleChecker([Role.ADMIN]))):
        ...
    """
    def __init__(self, allowed_roles: list[Role]):
        self.allowed_roles = allowed_roles

    async def __call__(self, user: dict = Depends(get_current_user)):
        user_role = user.get("role", Role.USER)

        if user_role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )

        return user

# Convenience dependencies
require_admin = RoleChecker([Role.ADMIN])
require_user = RoleChecker([Role.USER, Role.ADMIN])  # Admin can do user things

# app/models/user.py (extend)
def create_user(email: str, hashed_password: str, user_id: str, role: str = "user") -> dict:
    """Create user with role."""
    with neo4j_driver.session(database=settings.NEO4J_DATABASE) as session:
        result = session.run("""
            CREATE (u:User {
                id: $id,
                email: $email,
                hashed_password: $hashed_password,
                role: $role,
                created_at: datetime()
            })
            RETURN u
        """, id=user_id, email=email, hashed_password=hashed_password, role=role)

        return dict(result.single()["u"])
```

**Critical:**
1. Store role in User node (Neo4j).
2. Include role in JWT payload for fast checks (optional optimization).
3. Default role is "user" - admin assigned manually or via invite.
4. Anonymous users have no role (implicit "anonymous").

**Sources:**
- [FastAPI RBAC Full Implementation](https://www.permit.io/blog/fastapi-rbac-full-implementation-tutorial)
- [FastAPI Role-Based Access Control](https://medium.com/@abdulwasa.abdulkader/how-to-implement-a-simple-role-based-access-control-rbac-in-fastapi-using-middleware-af07d31efa9f)

### Pattern 7: Mem0 Memory Operations with User Isolation

**What:** Full Mem0 integration with user_id scoping for isolation.

**When to use:** MEM-01 through MEM-05 requirements.

**Example:**
```python
# app/services/memory_service.py
from typing import List, Dict, Optional
from app.db.mem0_client import get_mem0
from app.config import settings

SHARED_MEMORY_USER_ID = "__shared__"  # Sentinel for company-wide memory

async def add_user_memory(
    user_id: str,
    content: str,
    metadata: Optional[dict] = None
) -> dict:
    """Add a memory for a specific user (MEM-04).

    User can add arbitrary facts to their private memory.
    """
    memory = get_mem0()

    result = memory.add(
        messages=content,
        user_id=user_id,
        metadata=metadata or {},
        enable_graph=True  # Enable graph relationships
    )

    return result

async def search_user_memories(
    user_id: str,
    query: str,
    limit: int = 5,
    include_shared: bool = True
) -> List[dict]:
    """Search memories for a user.

    If include_shared=True, also searches company-wide shared memory.
    User memories prioritized over shared.
    """
    memory = get_mem0()

    # Search user's private memories
    user_results = memory.search(
        query=query,
        user_id=user_id,
        limit=limit
    )

    results = user_results.get("results", [])

    if include_shared:
        # Also search shared company memory
        shared_results = memory.search(
            query=query,
            user_id=SHARED_MEMORY_USER_ID,
            limit=limit
        )

        # Append shared results (lower priority)
        for mem in shared_results.get("results", []):
            mem["is_shared"] = True
            results.append(mem)

    return results[:limit]

async def add_shared_memory(content: str, metadata: Optional[dict] = None) -> dict:
    """Add company-wide shared memory (MEM-05).

    ADMIN ONLY. All authenticated users can query but not modify.
    """
    memory = get_mem0()

    result = memory.add(
        messages=content,
        user_id=SHARED_MEMORY_USER_ID,
        metadata={
            **(metadata or {}),
            "type": "shared",
            "scope": "company"
        },
        enable_graph=True
    )

    return result

async def get_conversation_history(
    user_id: str,
    session_id: Optional[str] = None,
    limit: int = 50
) -> List[dict]:
    """Get conversation history for a user (MEM-01).

    If session_id provided, filter to that session.
    """
    memory = get_mem0()

    # Get all memories for user
    memories = memory.get_all(user_id=user_id, limit=limit)

    if session_id:
        # Filter by session
        memories = [
            m for m in memories
            if m.get("metadata", {}).get("session_id") == session_id
        ]

    return memories
```

**Critical:**
1. Use `user_id` parameter consistently for isolation.
2. Shared memory uses sentinel value (`__shared__`) - authenticated users can query.
3. `enable_graph=True` creates entity relationships in Neo4j.
4. Conversation history is per-user, optionally per-session.

**Sources:**
- [Mem0 Graph Memory Documentation](https://docs.mem0.ai/open-source/features/graph-memory)
- [Mem0 Add Memories API](https://docs.mem0.ai/api-reference/memory/add-memories)

### Pattern 8: Multi-Tenant Security Testing

**What:** Automated tests to verify cross-tenant isolation.

**When to use:** CI pipeline, before every deployment.

**Example:**
```python
# tests/test_multi_tenant_isolation.py
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.fixture
async def user_a_token():
    """Create user A and return token."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/register",
            json={"email": "user_a@test.com", "password": "password123"}
        )
        return response.json()["access_token"]

@pytest.fixture
async def user_b_token():
    """Create user B and return token."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/register",
            json={"email": "user_b@test.com", "password": "password123"}
        )
        return response.json()["access_token"]

@pytest.mark.asyncio
async def test_user_cannot_access_other_users_documents(user_a_token, user_b_token):
    """CRITICAL: Verify User A cannot see User B's documents."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # User A uploads document
        with open("test_files/sample.pdf", "rb") as f:
            response = await client.post(
                "/api/v1/documents/upload",
                headers={"Authorization": f"Bearer {user_a_token}"},
                files={"file": ("sample.pdf", f, "application/pdf")}
            )
        doc_id_a = response.json()["document_id"]

        # User B tries to query User A's document
        response = await client.post(
            "/api/v1/query/",
            headers={"Authorization": f"Bearer {user_b_token}"},
            json={"query": "What is in the document?"}
        )

        # User B should NOT see User A's document content
        assert doc_id_a not in str(response.json())
        # Answer should indicate no relevant documents
        assert "don't know" in response.json()["answer"].lower() or \
               "no relevant" in response.json()["answer"].lower()

@pytest.mark.asyncio
async def test_user_cannot_manipulate_other_users_data(user_a_token, user_b_token):
    """CRITICAL: User A cannot delete/modify User B's data."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # User B uploads document
        with open("test_files/sample.pdf", "rb") as f:
            response = await client.post(
                "/api/v1/documents/upload",
                headers={"Authorization": f"Bearer {user_b_token}"},
                files={"file": ("sample.pdf", f, "application/pdf")}
            )
        doc_id_b = response.json()["document_id"]

        # User A tries to delete User B's document
        response = await client.delete(
            f"/api/v1/documents/{doc_id_b}",
            headers={"Authorization": f"Bearer {user_a_token}"}
        )

        # Should be forbidden or not found
        assert response.status_code in [403, 404]

@pytest.mark.asyncio
async def test_missing_tenant_context_rejected():
    """CRITICAL: Requests without user context must fail."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Query without authentication (no anonymous session setup)
        response = await client.post(
            "/api/v1/query/",
            json={"query": "test query"}
        )

        # Should require authentication or return anonymous-scoped response
        # NOT return data from other users

@pytest.mark.asyncio
async def test_token_tampering_rejected(user_a_token):
    """CRITICAL: Modified tokens must be rejected."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Tamper with token (change user_id in payload)
        import jwt

        # Decode without verification
        payload = jwt.decode(user_a_token, options={"verify_signature": False})
        payload["user_id"] = "different_user_id"

        # Re-encode with wrong signature (or no signature)
        tampered_token = jwt.encode(payload, "wrong_secret", algorithm="HS256")

        response = await client.post(
            "/api/v1/query/",
            headers={"Authorization": f"Bearer {tampered_token}"},
            json={"query": "test query"}
        )

        assert response.status_code == 401
```

**Critical Tests:**
1. User A cannot see User B's documents.
2. User A cannot modify/delete User B's data.
3. Requests without tenant context are rejected or isolated.
4. Token tampering is rejected.
5. Cache (if any) respects tenant boundaries.

**Sources:**
- [Authentication Is Not Isolation: Five Tests](https://aliengiraffe.ai/blog/authentication-is-not-isolation-the-five-tests-your-multi-tenant-system-is-probably-failing/)
- [Cross-Tenant Data Leaks](https://danaepp.com/cross-tenant-data-leaks-ctdl-why-api-hackers-should-be-on-the-lookout)

### Anti-Patterns to Avoid

- **Single-layer filtering:** Only filtering in API route, not in database query. If someone bypasses the route (direct DB access, SQL injection), data leaks.
- **User ID from request body:** Never trust client-provided user_id. Always derive from authenticated token.
- **Global cache without tenant key:** Cache keys must include tenant identifier. `cache:query:{hash}` is wrong. `cache:{user_id}:query:{hash}` is correct.
- **Shared collection for documents and memory:** Mem0 memory and RAG documents should use separate collections to prevent confusion and simplify isolation.
- **Forgetting to migrate anonymous data:** Anonymous user registers but their uploaded documents are lost. Must migrate atomically.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Token blocklist | In-memory dict | Redis with TTL | Survives restarts, scales horizontally, auto-expires entries |
| Session storage | File-based sessions | Redis or cookies | Stateless scaling, handles server restarts |
| Refresh token rotation | Custom DB table | Redis with hash verification | Fast lookups, automatic expiration, atomic operations |
| Scheduled cleanup | cron + scripts | APScheduler | Integrated with app, handles missed jobs, timezone-aware |
| Memory isolation | Custom filtering | Mem0 user_id parameter | Built-in, consistent, tested |
| Role checking | if/else in routes | FastAPI Depends + RoleChecker | Reusable, testable, declarative |
| Anonymous ID generation | timestamp + counter | secrets.token_urlsafe | Cryptographically secure, no collisions |

**Key insight:** Security-critical features (token management, session handling, data isolation) have subtle edge cases. Redis handles token blocklist correctly (TTL, persistence, atomic operations). Hand-rolling misses edge cases like server restarts, race conditions, and memory leaks.

## Common Pitfalls

### Pitfall 1: Authentication Is Not Isolation (CRITICAL)

**What goes wrong:** Implementing authentication (JWT validation) but forgetting to filter data by user_id in every database query. Users can see other users' data because queries don't include tenant context.

**Why it happens:** Developers assume "if user is authenticated, they're authorized." But authentication only verifies identity - it doesn't filter data.

**How to avoid:**
- EVERY database query MUST include user_id filter
- Create wrapper functions that require user_id parameter
- Middleware that injects user context into request state
- Automated tests that attempt cross-tenant access

**Warning signs:**
- Database queries without WHERE user_id = ?
- Functions that fetch data without user context
- "I'll add filtering later" in code comments

**Phase to address:** Phase 2 (core multi-tenant architecture)

### Pitfall 2: Memory Deletion Leaves Orphaned Neo4j Data (CRITICAL)

**What goes wrong:** Calling `Mem0.delete(memory_id)` removes vectors from Qdrant but leaves nodes/relationships in Neo4j. Graph data accumulates indefinitely.

**Why it happens:** Known Mem0 bug (GitHub issue #3245). Deletion is incomplete across dual stores.

**How to avoid:**
- Implement custom deletion that explicitly removes Neo4j data
- After Mem0.delete(), run cleanup query in Neo4j
- Monitor graph size vs. vector count for divergence
- Schedule periodic orphan detection and cleanup

**Example cleanup:**
```cypher
// Find orphaned memory nodes (no corresponding vector)
MATCH (m:Memory)
WHERE NOT EXISTS {
    MATCH (m)-[:HAS_VECTOR]->(:Vector)
}
DETACH DELETE m
```

**Warning signs:**
- Neo4j database size grows faster than Qdrant
- Graph queries show deleted entities
- Memory counts don't match between stores

**Phase to address:** Phase 2 (memory integration)

### Pitfall 3: Refresh Token Reuse Vulnerability (CRITICAL)

**What goes wrong:** Refresh tokens can be used multiple times, enabling token theft attacks. Attacker steals token, uses it before victim, victim's refresh fails.

**Why it happens:** Not implementing rotation - same refresh token works repeatedly.

**How to avoid:**
- Single-use refresh tokens (delete after use)
- Hash tokens before storage
- Track token lineage (detect if old token used)
- Alert on suspicious patterns

**Warning signs:**
- Same refresh token working multiple times
- No Redis/DB storage for refresh tokens
- No logging of refresh operations

**Phase to address:** Phase 2 (authentication enhancement)

### Pitfall 4: Anonymous Session ID in URL (MODERATE)

**What goes wrong:** Passing anonymous session ID as URL parameter exposes it in logs, browser history, and referrer headers.

**Why it happens:** Easiest implementation is `?session_id=xxx` in URLs.

**How to avoid:**
- Use HTTP-only cookies for session tracking
- Never include session ID in URLs
- Set secure and samesite cookie attributes
- Regenerate session ID on privilege change

**Warning signs:**
- Session IDs visible in access logs
- Session parameter in URL patterns
- Browser history shows session IDs

**Phase to address:** Phase 2 (anonymous sessions)

### Pitfall 5: Missing Timestamp for TTL Cleanup (MODERATE)

**What goes wrong:** Can't implement TTL cleanup because records don't have creation timestamps. Must add timestamps retroactively or skip cleanup.

**Why it happens:** Phase 1 didn't anticipate cleanup needs.

**How to avoid:**
- Add `created_at` timestamp to ALL records from Phase 1
- Qdrant payload must include timestamp for filter-based deletion
- Neo4j nodes must have datetime() property
- Index timestamp fields for efficient queries

**Warning signs:**
- Records without timestamps
- Cleanup queries do full table scans
- Unable to determine record age

**Phase to address:** Phase 1 design (fix in Phase 2 if missing)

### Pitfall 6: Shared Memory Access Control (MODERATE)

**What goes wrong:** Everyone can write to shared company memory, or no one can read it. Authorization boundaries unclear.

**Why it happens:** "Shared" concept implemented without access rules.

**How to avoid:**
- Shared memory uses sentinel user_id (`__shared__`)
- Admin role required to WRITE to shared memory
- All authenticated users can READ shared memory
- Anonymous users cannot access shared memory
- Audit log for shared memory changes

**Warning signs:**
- No role check on shared memory writes
- Shared memories appearing for anonymous users
- No audit trail for company knowledge changes

**Phase to address:** Phase 2 (RBAC + shared memory)

## Code Examples

Verified patterns from official sources:

### Configuration Extension for Phase 2

```python
# app/config.py (extend from Phase 1)
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # ... Phase 1 settings ...

    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_MAX_CONNECTIONS: int = 50

    # Token Configuration
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15  # Shorter than Phase 1
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Anonymous Sessions
    ANONYMOUS_SESSION_EXPIRE_DAYS: int = 7
    ANONYMOUS_PREFIX: str = "anon_"

    # Cleanup
    CLEANUP_SCHEDULE_HOUR: int = 3  # Run at 3 AM

    # Memory
    MEMORY_COLLECTION: str = "memory"  # Separate from documents
    SHARED_MEMORY_USER_ID: str = "__shared__"
```

### Secure Logout with Token Blocklist

```python
# app/api/auth.py (extend)
from fastapi import APIRouter, Depends
from app.db.redis_client import get_redis, add_token_to_blocklist
from app.core.security import get_current_user
import redis.asyncio as redis

router = APIRouter()

@router.post("/logout")
async def logout(
    current_user: dict = Depends(get_current_user),
    redis_client: redis.Redis = Depends(get_redis)
):
    """Logout and invalidate current token.

    SECURITY: Adds token JTI to blocklist so it can't be reused.
    """
    jti = current_user.get("jti")
    if jti:
        await add_token_to_blocklist(jti, redis_client)

    return {"message": "Successfully logged out"}
```

### Memory Endpoint with Role Protection

```python
# app/api/memory.py
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from app.core.security import get_current_user
from app.core.rbac import require_admin
from app.services.memory_service import (
    add_user_memory,
    search_user_memories,
    add_shared_memory
)

router = APIRouter()

class MemoryRequest(BaseModel):
    content: str
    metadata: dict = {}

@router.post("/")
async def add_memory(
    request: MemoryRequest,
    current_user: dict = Depends(get_current_user)
):
    """Add fact to user's private memory (MEM-04)."""
    if current_user.get("is_anonymous"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Anonymous users cannot add memories. Please register."
        )

    result = await add_user_memory(
        user_id=current_user["id"],
        content=request.content,
        metadata=request.metadata
    )

    return {"status": "added", "memory_id": result.get("id")}

@router.post("/shared")
async def add_shared_memory_endpoint(
    request: MemoryRequest,
    current_user: dict = Depends(require_admin)  # Admin only
):
    """Add fact to shared company memory (MEM-05).

    ADMIN ONLY. All authenticated users can query this memory.
    """
    result = await add_shared_memory(
        content=request.content,
        metadata=request.metadata
    )

    return {"status": "added", "memory_id": result.get("id"), "scope": "shared"}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| aioredis package | redis.asyncio (redis-py) | 2023 | aioredis merged into redis-py. Use `import redis.asyncio`. |
| Mem0 v1 API | Mem0 v2 API | 2025 | v1 deprecated. Use v2 for new applications. |
| Session storage in DB | Redis + cookies | 2020+ | Faster, scales horizontally, automatic TTL. |
| bcrypt for tokens | SHA-256 for token hashing | - | Tokens don't need slow hash. SHA-256 sufficient for hashing. |
| Single collection multi-tenant | Tiered multitenancy | Qdrant 1.16 (Nov 2025) | Large tenants get dedicated shards, small share fallback. |
| Manual token cleanup | Redis TTL | - | Automatic expiration prevents blocklist bloat. |

**Deprecated/outdated:**
- `aioredis` package: Merged into redis-py, use `redis.asyncio`
- Mem0 v1 API: Deprecated, use v2
- File-based sessions: Use Redis or stateless tokens
- Manual orphan cleanup: Should be automated

## Open Questions

Things that couldn't be fully resolved:

1. **Mem0 memory deletion bug fix timeline**
   - What we know: GitHub issue #3245 confirms incomplete deletion
   - What's unclear: When official fix will be released
   - Recommendation: Implement custom deletion wrapper that handles both stores

2. **Qdrant payload update performance at scale**
   - What we know: No bulk payload update - must scroll and update
   - What's unclear: Performance for 100K+ vectors during migration
   - Recommendation: Batch migrations, consider background job for large accounts

3. **Anonymous session cookie vs. localStorage**
   - What we know: Cookies safer (httpOnly), localStorage faster access
   - What's unclear: Impact on UX for frequent session checks
   - Recommendation: Start with cookies, profile if needed

4. **Optimal refresh token lifetime**
   - What we know: 7 days common, balance security vs. UX
   - What's unclear: Whether shorter (1 day) significantly impacts security
   - Recommendation: Start with 7 days, add sliding window renewal

5. **Shared memory query performance**
   - What we know: Querying user + shared memories requires 2 searches
   - What's unclear: Performance impact of dual search at scale
   - Recommendation: Profile, consider caching shared memory results

## Sources

### Primary (HIGH confidence)

**Official Documentation:**
- [Redis-py Async Documentation](https://redis-py.readthedocs.io/en/stable/examples/asyncio_examples.html)
- [Mem0 Graph Memory](https://docs.mem0.ai/open-source/features/graph-memory)
- [Mem0 Add Memories API](https://docs.mem0.ai/api-reference/memory/add-memories)
- [Qdrant Multitenancy Guide](https://qdrant.tech/documentation/guides/multitenancy/)
- [FastAPI Security Tutorial](https://fastapi.tiangolo.com/tutorial/security/)
- [OWASP Session Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)

**GitHub Issues/Discussions:**
- [Mem0 Issue #3245: Memory deletion doesn't clean Neo4j](https://github.com/mem0ai/mem0/issues/3245)
- [Qdrant Discussion #5441: Cleanup/TTL](https://github.com/orgs/qdrant/discussions/5441)
- [FastAPI Discussion #3580: JWT Revocation](https://github.com/fastapi/fastapi/discussions/3580)

### Secondary (MEDIUM confidence)

**Implementation Guides (2026):**
- [JWT in FastAPI, the Secure Way](https://medium.com/@jagan_reddy/jwt-in-fastapi-the-secure-way-refresh-tokens-explained-f7d2d17b1d17)
- [FastAPI RBAC Full Implementation](https://www.permit.io/blog/fastapi-rbac-full-implementation-tutorial)
- [Setting Up Async Redis Client in FastAPI](https://medium.com/@geetansh2k1/setting-up-and-using-an-async-redis-client-in-fastapi-the-right-way-0409ad3812e6)
- [JWT Authentication - Revoke Tokens Using Redis](https://dev.to/jod35/fastapi-beyond-crud-part-12-jwt-authentication-revoke-access-tokens-using-redis-eff)

**Security Research:**
- [Authentication Is Not Isolation: Five Tests](https://aliengiraffe.ai/blog/authentication-is-not-isolation-the-five-tests-your-multi-tenant-system-is-probably-failing/)
- [Cross-Tenant Data Leaks (CTDL)](https://danaepp.com/cross-tenant-data-leaks-ctdl-why-api-hackers-should-be-on-the-lookout)
- [Refresh Token Rotation Best Practices](https://www.serverion.com/uncategorized/refresh-token-rotation-best-practices-for-developers/)

### Tertiary (LOW confidence)

**Referenced from project pitfalls research:**
- Mem0 orphaned data (needs validation in Phase 2)
- Multi-tenant isolation complexity (research confirmed)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Redis-py official, Mem0 docs verified, OWASP guidelines authoritative
- Architecture: HIGH - Patterns from official FastAPI, Redis, Mem0 documentation
- Pitfalls: HIGH - Security concerns verified from OWASP, GitHub issues, security research
- Testing strategies: MEDIUM - Based on security best practices, not project-specific validation

**Research date:** 2026-02-04
**Valid until:** 30 days (stable patterns, but check Mem0 for deletion bug fix)

**Critical Phase 2 Success Criteria:**
- [ ] Every database query includes user_id filter (defense in depth)
- [ ] Refresh token rotation implemented with single-use enforcement
- [ ] Token blocklist in Redis with TTL auto-expiration
- [ ] Anonymous sessions via HTTP-only cookies (not URLs)
- [ ] Anonymous data migrates atomically on registration
- [ ] TTL cleanup job deletes expired anonymous data
- [ ] Admin role can write to shared memory, users can only read
- [ ] Mem0 memories isolated by user_id
- [ ] Cross-tenant access tests pass in CI
- [ ] No cross-tenant data leakage detected in security testing
