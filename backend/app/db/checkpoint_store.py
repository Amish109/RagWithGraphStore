"""LangGraph checkpoint store configuration using PostgreSQL.

Provides:
- get_checkpointer(): Get the AsyncPostgresSaver instance
- setup_checkpointer(): Initialize checkpoint tables (MUST call at startup)

CRITICAL: setup_checkpointer() MUST be called during application startup
before any workflow execution. This creates the required database tables.
"""

import logging
from typing import Optional

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.config import settings
from app.db.postgres_client import get_postgres_pool

logger = logging.getLogger(__name__)

# Module-level checkpointer instance (lazy initialized)
_checkpointer: Optional[AsyncPostgresSaver] = None


async def get_checkpointer() -> AsyncPostgresSaver:
    """Get LangGraph AsyncPostgresSaver for workflow checkpointing.

    Lazy initialization pattern - creates checkpointer on first call.

    Returns:
        AsyncPostgresSaver instance configured with PostgreSQL connection.
    """
    global _checkpointer
    if _checkpointer is None:
        pool = await get_postgres_pool()
        _checkpointer = AsyncPostgresSaver(pool)
    return _checkpointer


async def setup_checkpointer() -> None:
    """Initialize LangGraph checkpoint tables in PostgreSQL.

    CRITICAL: This MUST be called during application startup before
    any workflow execution. Creates required tables for state persistence.

    Tables created:
    - checkpoint: Stores workflow state snapshots
    - checkpoint_writes: Stores pending writes
    - checkpoint_blobs: Stores serialized state data
    """
    try:
        checkpointer = await get_checkpointer()
        await checkpointer.setup()
        logger.info("LangGraph checkpoint tables initialized in PostgreSQL")
    except Exception as e:
        logger.error(f"Failed to setup LangGraph checkpointer: {e}")
        # Re-raise to prevent app startup with broken checkpointing
        raise
