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

    Creates required tables for state persistence. Uses manual SQL to avoid
    the CREATE INDEX CONCURRENTLY issue that AsyncPostgresSaver.setup() has
    when running inside a transaction block.

    Tables created:
    - checkpoints: Stores workflow state snapshots
    - checkpoint_blobs: Stores serialized state data
    - checkpoint_writes: Stores pending writes
    - checkpoint_migrations: Tracks applied migrations
    """
    pool = await get_postgres_pool()

    # Check if tables already exist
    async with pool.connection() as conn:
        result = await conn.execute(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'checkpoints')"
        )
        row = await result.fetchone()
        if row and row[0]:
            logger.info("LangGraph checkpoint tables already exist")
            # Ensure checkpointer instance is created
            await get_checkpointer()
            return

    # Create tables manually (avoids CREATE INDEX CONCURRENTLY issue)
    async with pool.connection() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS checkpoint_migrations (
                v INTEGER PRIMARY KEY
            );
            CREATE TABLE IF NOT EXISTS checkpoints (
                thread_id TEXT NOT NULL,
                checkpoint_ns TEXT NOT NULL DEFAULT '',
                checkpoint_id TEXT NOT NULL,
                parent_checkpoint_id TEXT,
                type TEXT,
                checkpoint JSONB NOT NULL,
                metadata JSONB NOT NULL DEFAULT '{}',
                PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
            );
            CREATE TABLE IF NOT EXISTS checkpoint_blobs (
                thread_id TEXT NOT NULL,
                checkpoint_ns TEXT NOT NULL DEFAULT '',
                channel TEXT NOT NULL,
                version TEXT NOT NULL,
                type TEXT NOT NULL,
                blob BYTEA,
                PRIMARY KEY (thread_id, checkpoint_ns, channel, version)
            );
            CREATE TABLE IF NOT EXISTS checkpoint_writes (
                thread_id TEXT NOT NULL,
                checkpoint_ns TEXT NOT NULL DEFAULT '',
                checkpoint_id TEXT NOT NULL,
                task_id TEXT NOT NULL,
                idx INTEGER NOT NULL,
                channel TEXT NOT NULL,
                type TEXT,
                blob BYTEA NOT NULL,
                task_path TEXT NOT NULL DEFAULT '',
                PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
            );
            CREATE INDEX IF NOT EXISTS checkpoints_thread_id_idx ON checkpoints(thread_id);
            CREATE INDEX IF NOT EXISTS checkpoint_blobs_thread_id_idx ON checkpoint_blobs(thread_id);
            CREATE INDEX IF NOT EXISTS checkpoint_writes_thread_id_idx ON checkpoint_writes(thread_id);
        """)
        # Mark all migrations as applied so AsyncPostgresSaver.setup() won't re-run them
        for v in range(10):
            await conn.execute(
                "INSERT INTO checkpoint_migrations (v) VALUES (%s) ON CONFLICT DO NOTHING",
                (v,),
            )

    logger.info("LangGraph checkpoint tables created in PostgreSQL")
    await get_checkpointer()
