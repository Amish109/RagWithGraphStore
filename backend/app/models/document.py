"""Document model functions for Neo4j operations.

Provides document retrieval functions with multi-tenant isolation.
CRITICAL: Always filters by user_id to prevent cross-tenant access.
"""

from typing import Dict, List, Optional

from app.config import settings
from app.db.neo4j_client import neo4j_driver


def get_document_by_id(document_id: str, user_id: str) -> Optional[Dict]:
    """Get a document by ID, scoped to user.

    CRITICAL: Always filters by user_id for multi-tenant isolation.
    Prevents Pitfall #6 (no multi-tenant filtering).

    Args:
        document_id: UUID of the document.
        user_id: ID of the requesting user.

    Returns:
        Document dict if found and owned by user, None otherwise.
    """
    with neo4j_driver.session(database=settings.NEO4J_DATABASE) as session:
        result = session.run(
            """
            MATCH (u:User {id: $user_id})-[:OWNS]->(d:Document {id: $document_id})
            RETURN d {
                .id,
                .filename,
                .upload_date,
                .chunk_count,
                .summary,
                .file_type,
                .file_size
            } AS document
            """,
            document_id=document_id,
            user_id=user_id,
        )
        record = result.single()
        if record:
            doc = dict(record["document"])
            # Convert Neo4j datetime to ISO string and rename to created_at
            if doc.get("upload_date"):
                doc["created_at"] = doc.pop("upload_date").isoformat()
            else:
                doc.pop("upload_date", None)
            return doc
        return None


def get_user_documents(user_id: str) -> List[Dict]:
    """Get all documents for a user.

    Args:
        user_id: ID of the user.

    Returns:
        List of document dicts with id, filename, upload_date, chunk_count, summary.
    """
    with neo4j_driver.session(database=settings.NEO4J_DATABASE) as session:
        result = session.run(
            """
            MATCH (u:User {id: $user_id})-[:OWNS]->(d:Document)
            RETURN d {
                .id,
                .filename,
                .upload_date,
                .chunk_count,
                .summary,
                .file_type,
                .file_size
            } AS document
            ORDER BY d.upload_date DESC
            """,
            user_id=user_id,
        )
        documents = []
        for record in result:
            doc = dict(record["document"])
            # Convert Neo4j datetime to ISO string and rename to created_at
            if doc.get("upload_date"):
                doc["created_at"] = doc.pop("upload_date").isoformat()
            else:
                doc.pop("upload_date", None)
            documents.append(doc)
        return documents


def delete_document(document_id: str, user_id: str) -> bool:
    """Delete a document, its chunks, and orphaned entities from Neo4j.

    Uses DETACH DELETE to cascade deletion to all chunks.
    Also cleans up Entity nodes that no longer appear in any remaining chunks.
    CRITICAL: Always filter by user_id for multi-tenant isolation.

    Args:
        document_id: UUID of the document.
        user_id: ID of the requesting user (for ownership verification).

    Returns:
        True if document was deleted, False if not found/not owned.
    """
    with neo4j_driver.session(database=settings.NEO4J_DATABASE) as session:
        # First collect entity IDs linked to this document's chunks
        # so we can check for orphans after deletion
        entity_result = session.run(
            """
            MATCH (u:User {id: $user_id})-[:OWNS]->(d:Document {id: $document_id})
            OPTIONAL MATCH (d)-[:CONTAINS]->(c:Chunk)<-[:APPEARS_IN]-(e:Entity)
            RETURN collect(DISTINCT id(e)) AS entity_internal_ids
            """,
            document_id=document_id,
            user_id=user_id,
        )
        entity_record = entity_result.single()
        entity_ids = entity_record["entity_internal_ids"] if entity_record else []

        # Delete document and chunks
        result = session.run(
            """
            MATCH (u:User {id: $user_id})-[:OWNS]->(d:Document {id: $document_id})
            OPTIONAL MATCH (d)-[:CONTAINS]->(c:Chunk)
            WITH d, collect(c) as chunks
            DETACH DELETE d
            FOREACH (chunk IN chunks | DETACH DELETE chunk)
            RETURN count(d) as deleted
            """,
            document_id=document_id,
            user_id=user_id,
        )
        record = result.single()
        deleted = record and record["deleted"] > 0

        # Clean up orphaned entities (no remaining APPEARS_IN relationships)
        if deleted and entity_ids:
            session.run(
                """
                UNWIND $entity_ids AS eid
                MATCH (e:Entity) WHERE id(e) = eid
                    AND NOT (e)-[:APPEARS_IN]->()
                DETACH DELETE e
                """,
                entity_ids=entity_ids,
            )

        return deleted
