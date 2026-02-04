"""Migration service for anonymous-to-authenticated data transfer.

Provides atomic data migration when anonymous users register:
- migrate_anonymous_to_user: Transfer all data to permanent account
- check_anonymous_has_data: Check if anonymous session has data worth migrating

CRITICAL: Migration order is by importance - Neo4j first (document metadata),
then Qdrant (vectors), then Mem0 (memories). If later steps fail, earlier
changes remain but are still usable.

Requirement references:
- AUTH-04: Anonymous users can register and data migrates to permanent account
"""

from typing import Dict

from qdrant_client.models import FieldCondition, Filter, MatchValue

from app.config import settings
from app.db.mem0_client import get_mem0
from app.db.neo4j_client import neo4j_driver
from app.db.qdrant_client import qdrant_client


async def migrate_anonymous_to_user(
    anonymous_id: str,
    new_user_id: str
) -> Dict[str, int]:
    """Migrate all anonymous user data to authenticated account.

    Steps:
    1. Update Neo4j: Change user_id on all Documents and Chunks
    2. Update Qdrant: Change user_id payload on all vectors
    3. Update Mem0: Transfer memories to new user_id

    CRITICAL: This should be as atomic as possible. If later step fails,
    earlier changes remain (Neo4j/Qdrant don't have cross-service transactions).
    We proceed in order of importance: documents first, then vectors, then memories.

    Args:
        anonymous_id: The anonymous session ID (anon_xxx).
        new_user_id: The new authenticated user's UUID.

    Returns:
        Migration stats dict with keys: documents, chunks, vectors, memories
    """
    stats = {"documents": 0, "chunks": 0, "vectors": 0, "memories": 0}

    # Step 1: Migrate Neo4j data (Documents and Chunks)
    try:
        with neo4j_driver.session(database=settings.NEO4J_DATABASE) as session:
            # Update documents and count
            result = session.run("""
                MATCH (d:Document {user_id: $old_id})
                SET d.user_id = $new_id
                RETURN count(d) as doc_count
            """, old_id=anonymous_id, new_id=new_user_id)

            record = result.single()
            if record:
                stats["documents"] = record["doc_count"]

            # Update chunks (they have user_id for query filtering)
            result = session.run("""
                MATCH (c:Chunk {user_id: $old_id})
                SET c.user_id = $new_id
                RETURN count(c) as chunk_count
            """, old_id=anonymous_id, new_id=new_user_id)

            record = result.single()
            if record:
                stats["chunks"] = record["chunk_count"]
    except Exception as e:
        # Neo4j failure is critical - log but continue to try other migrations
        print(f"Neo4j migration error: {e}")

    # Step 2: Migrate Qdrant vectors (update payload)
    # Qdrant doesn't have bulk payload update - scroll and update
    try:
        scroll_result = qdrant_client.scroll(
            collection_name=settings.QDRANT_COLLECTION,
            scroll_filter=Filter(
                must=[FieldCondition(key="user_id", match=MatchValue(value=anonymous_id))]
            ),
            limit=1000,  # Process in batches if needed
            with_payload=False,
            with_vectors=False
        )

        point_ids = [point.id for point in scroll_result[0]]
        stats["vectors"] = len(point_ids)

        if point_ids:
            # Update payload for all points
            qdrant_client.set_payload(
                collection_name=settings.QDRANT_COLLECTION,
                payload={"user_id": new_user_id},
                points=point_ids
            )
    except Exception as e:
        # Log but don't fail - documents in Neo4j are more critical
        print(f"Qdrant migration warning: {e}")

    # Step 3: Migrate Mem0 memories
    # Mem0 doesn't support user_id update - must copy and delete
    try:
        memory = get_mem0()

        # Get all memories for anonymous user
        old_memories = memory.get_all(user_id=anonymous_id)
        if isinstance(old_memories, dict):
            old_memories = old_memories.get("results", [])

        if old_memories:
            for mem in old_memories:
                try:
                    # Re-add with new user_id
                    memory.add(
                        messages=mem.get("memory", ""),
                        user_id=new_user_id,
                        metadata=mem.get("metadata", {})
                    )
                    # Delete old memory
                    memory.delete(mem.get("id"))
                    stats["memories"] += 1
                except Exception:
                    # Continue with other memories if one fails
                    pass
    except Exception as e:
        # Log but don't fail migration
        print(f"Mem0 migration warning: {e}")

    return stats


async def check_anonymous_has_data(anonymous_id: str) -> bool:
    """Check if anonymous session has any data worth migrating.

    Checks both Neo4j (documents) and Mem0 (memories) for user data.

    Args:
        anonymous_id: The anonymous session ID to check.

    Returns:
        True if the anonymous session has documents or memories.
    """
    # Check Neo4j for documents
    try:
        with neo4j_driver.session(database=settings.NEO4J_DATABASE) as session:
            result = session.run("""
                MATCH (d:Document {user_id: $user_id})
                RETURN count(d) as count
            """, user_id=anonymous_id)

            record = result.single()
            if record and record["count"] > 0:
                return True
    except Exception:
        pass

    # Also check memories
    try:
        memory = get_mem0()
        memories = memory.get_all(user_id=anonymous_id, limit=1)
        if isinstance(memories, dict):
            memories = memories.get("results", [])
        if memories:
            return True
    except Exception:
        pass

    return False
