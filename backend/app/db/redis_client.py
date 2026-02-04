"""Redis client for token management.

Provides:
- Connection pool for efficient reuse
- Token blocklist operations with TTL
- Refresh token storage

CRITICAL: Uses redis.asyncio (NOT deprecated aioredis).
CRITICAL: All blocklist entries use TTL to prevent unbounded growth.
"""

import redis.asyncio as redis
from typing import AsyncGenerator

from app.config import settings

# Connection pool for efficient reuse
redis_pool = redis.ConnectionPool.from_url(
    settings.REDIS_URL,
    max_connections=settings.REDIS_MAX_CONNECTIONS,
    decode_responses=True,
)


async def get_redis() -> AsyncGenerator[redis.Redis, None]:
    """Get Redis client from connection pool.

    Use as FastAPI dependency:
        async def endpoint(redis_client: redis.Redis = Depends(get_redis)):
            ...

    Yields:
        Redis client instance from connection pool.
    """
    client = redis.Redis(connection_pool=redis_pool)
    try:
        yield client
    finally:
        # Connection returns to pool automatically
        pass


async def close_redis() -> None:
    """Close Redis connection pool on shutdown."""
    await redis_pool.disconnect()


async def add_token_to_blocklist(jti: str, redis_client: redis.Redis) -> None:
    """Add JWT ID to blocklist (for logout/revocation).

    CRITICAL: Use TTL to auto-expire entries. Without TTL, blocklist grows unbounded.

    Args:
        jti: JWT ID (unique token identifier).
        redis_client: Redis client instance.
    """
    await redis_client.setex(
        f"blocklist:{jti}",
        settings.JTI_BLOCKLIST_EXPIRE_SECONDS,
        "1",
    )


async def is_token_blocklisted(jti: str, redis_client: redis.Redis) -> bool:
    """Check if token is blocklisted (revoked).

    Args:
        jti: JWT ID to check.
        redis_client: Redis client instance.

    Returns:
        True if token is blocklisted, False otherwise.
    """
    return await redis_client.exists(f"blocklist:{jti}") > 0


async def store_refresh_token(
    user_id: str,
    jti: str,
    token_hash: str,
    redis_client: redis.Redis,
) -> None:
    """Store hashed refresh token in Redis.

    Key format: refresh:{user_id}:{jti}
    Value: token_hash (SHA-256)
    TTL: REFRESH_TOKEN_EXPIRE_DAYS

    Args:
        user_id: User's unique identifier.
        jti: JWT ID for this refresh token.
        token_hash: SHA-256 hash of the refresh token.
        redis_client: Redis client instance.
    """
    await redis_client.setex(
        f"refresh:{user_id}:{jti}",
        settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
        token_hash,
    )


async def get_stored_refresh_token(
    user_id: str,
    jti: str,
    redis_client: redis.Redis,
) -> str | None:
    """Get stored refresh token hash from Redis.

    Args:
        user_id: User's unique identifier.
        jti: JWT ID for the refresh token.
        redis_client: Redis client instance.

    Returns:
        Token hash if found, None otherwise.
    """
    return await redis_client.get(f"refresh:{user_id}:{jti}")


async def delete_refresh_token(
    user_id: str,
    jti: str,
    redis_client: redis.Redis,
) -> None:
    """Delete refresh token from Redis (single-use enforcement).

    Args:
        user_id: User's unique identifier.
        jti: JWT ID for the refresh token.
        redis_client: Redis client instance.
    """
    await redis_client.delete(f"refresh:{user_id}:{jti}")
