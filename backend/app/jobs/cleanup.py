"""Scheduled cleanup jobs for expired anonymous data.

Provides:
- cleanup_expired_anonymous_data: Delete anonymous user data older than TTL
- setup_cleanup_scheduler: Initialize APScheduler for daily cleanup
- shutdown_cleanup_scheduler: Graceful shutdown of scheduler

Requirement references:
- AUTH-05: Temporary anonymous data expires after configured time period
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from qdrant_client.models import FieldCondition, Filter, Range

from app.config import settings
from app.db.neo4j_client import neo4j_driver
from app.db.qdrant_client import qdrant_client

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler: Optional[AsyncIOScheduler] = None


async def cleanup_expired_anonymous_data() -> Dict[str, int]:
    """Delete anonymous user data older than TTL.

    Runs on schedule (e.g., daily at 3 AM). Cleans:
    1. Neo4j: Documents and Chunks with anon_ user_id older than TTL
    2. Qdrant: Vectors with anon_ user_id older than TTL

    NOTE: Mem0 memories are harder to clean by timestamp - rely on session
    expiration and migration to handle memory cleanup.

    CRITICAL: Use upload_date/created_at for TTL queries (indexed in Phase 1).

    Returns:
        Dict with cleanup stats: documents, chunks, vectors deleted.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.ANONYMOUS_DATA_TTL_DAYS)
    cutoff_str = cutoff.isoformat()

    stats = {"documents": 0, "chunks": 0, "vectors": 0}

    # Step 1: Delete expired Neo4j data
    try:
        with neo4j_driver.session(database=settings.NEO4J_DATABASE) as session:
            # Delete chunks first (they reference documents via relationship)
            result = session.run("""
                MATCH (d:Document)-[:CONTAINS]->(c:Chunk)
                WHERE d.user_id STARTS WITH $prefix
                AND d.upload_date < datetime($cutoff)
                DETACH DELETE c
                RETURN count(c) as count
            """, prefix=settings.ANONYMOUS_PREFIX, cutoff=cutoff_str)

            record = result.single()
            if record:
                stats["chunks"] = record["count"]

            # Delete documents
            result = session.run("""
                MATCH (d:Document)
                WHERE d.user_id STARTS WITH $prefix
                AND d.upload_date < datetime($cutoff)
                DETACH DELETE d
                RETURN count(d) as count
            """, prefix=settings.ANONYMOUS_PREFIX, cutoff=cutoff_str)

            record = result.single()
            if record:
                stats["documents"] = record["count"]

        logger.info(f"Neo4j cleanup: {stats['documents']} docs, {stats['chunks']} chunks")
    except Exception as e:
        logger.error(f"Neo4j cleanup error: {e}")

    # Step 2: Delete expired Qdrant vectors
    try:
        # Get cutoff timestamp for Qdrant (uses Unix timestamp in payload)
        cutoff_ts = cutoff.timestamp()

        # Scroll to find expired vectors with anonymous user_id
        # Qdrant doesn't support STARTS WITH directly, so we filter in Python
        scroll_result = qdrant_client.scroll(
            collection_name=settings.QDRANT_COLLECTION,
            scroll_filter=Filter(
                must=[
                    FieldCondition(
                        key="created_at",
                        range=Range(lt=cutoff_ts)
                    )
                ]
            ),
            limit=1000,
            with_payload=["user_id"],
            with_vectors=False
        )

        # Filter to only anonymous users (starts with anon_ prefix)
        anon_points = [
            p.id for p in scroll_result[0]
            if p.payload.get("user_id", "").startswith(settings.ANONYMOUS_PREFIX)
        ]

        if anon_points:
            qdrant_client.delete(
                collection_name=settings.QDRANT_COLLECTION,
                points_selector=anon_points
            )
            stats["vectors"] = len(anon_points)

        logger.info(f"Qdrant cleanup: {stats['vectors']} vectors")
    except Exception as e:
        logger.error(f"Qdrant cleanup error: {e}")

    logger.info(f"Cleanup complete: {stats}")
    return stats


def setup_cleanup_scheduler() -> AsyncIOScheduler:
    """Initialize cleanup job scheduler.

    Creates an AsyncIOScheduler that runs the cleanup job daily at
    the configured hour (default: 3 AM).

    Returns:
        The configured and started AsyncIOScheduler instance.
    """
    global scheduler

    scheduler = AsyncIOScheduler()

    # Run daily at configured hour (default 3 AM)
    scheduler.add_job(
        cleanup_expired_anonymous_data,
        'cron',
        hour=settings.CLEANUP_SCHEDULE_HOUR,
        minute=0,
        id='cleanup_anonymous_data',
        replace_existing=True
    )

    scheduler.start()
    logger.info(f"Cleanup scheduler started, runs daily at {settings.CLEANUP_SCHEDULE_HOUR}:00")

    return scheduler


def shutdown_cleanup_scheduler() -> None:
    """Shutdown the scheduler gracefully.

    Called during application shutdown to stop pending jobs.
    """
    global scheduler
    if scheduler:
        scheduler.shutdown(wait=False)
        logger.info("Cleanup scheduler shutdown")
