"""Async PostgreSQL connection management for LangGraph checkpointing.

Provides:
- get_postgres_pool(): Get the async connection pool (lazy initialization)
- close_postgres_pool(): Close the pool connection
"""

from typing import Optional

from psycopg_pool import AsyncConnectionPool

from app.config import settings

# Module-level connection pool (lazy initialized)
_pool: Optional[AsyncConnectionPool] = None


async def get_postgres_pool() -> AsyncConnectionPool:
    """Get PostgreSQL async connection pool.

    Lazy initialization pattern - creates pool on first call.
    Pool is reused for subsequent calls.

    Returns:
        AsyncConnectionPool instance.
    """
    global _pool
    if _pool is None:
        _pool = AsyncConnectionPool(
            conninfo=settings.POSTGRES_URI,
            min_size=1,
            max_size=settings.POSTGRES_POOL_SIZE,
            open=False,  # Don't open immediately
        )
        await _pool.open()
    return _pool


async def close_postgres_pool() -> None:
    """Close PostgreSQL connection pool.

    Should be called during application shutdown.
    """
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
