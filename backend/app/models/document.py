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
                .chunk_count
            } AS document
            """,
            document_id=document_id,
            user_id=user_id,
        )
        record = result.single()
        if record:
            doc = dict(record["document"])
            # Convert Neo4j datetime to ISO string if present
            if doc.get("upload_date"):
                doc["upload_date"] = doc["upload_date"].isoformat()
            return doc
        return None


def get_user_documents(user_id: str) -> List[Dict]:
    """Get all documents for a user.

    Args:
        user_id: ID of the user.

    Returns:
        List of document dicts with id, filename, upload_date, chunk_count.
    """
    with neo4j_driver.session(database=settings.NEO4J_DATABASE) as session:
        result = session.run(
            """
            MATCH (u:User {id: $user_id})-[:OWNS]->(d:Document)
            RETURN d {
                .id,
                .filename,
                .upload_date,
                .chunk_count
            } AS document
            ORDER BY d.upload_date DESC
            """,
            user_id=user_id,
        )
        documents = []
        for record in result:
            doc = dict(record["document"])
            # Convert Neo4j datetime to ISO string if present
            if doc.get("upload_date"):
                doc["upload_date"] = doc["upload_date"].isoformat()
            documents.append(doc)
        return documents
