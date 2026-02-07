"""Indexing service for dual-write to Neo4j and Qdrant.

This module provides functions to store document metadata and chunks
in both Neo4j (graph store) and Qdrant (vector store) with shared IDs
for cross-referencing between stores.

CRITICAL: Ensures multi-tenant isolation by always including user_id.
"""

from typing import Dict, List

from app.config import settings
from app.db.neo4j_client import neo4j_driver
from app.db.qdrant_client import upsert_chunks


def store_document_in_neo4j(
    document_id: str,
    user_id: str,
    filename: str,
    chunks: List[Dict],
    summary: str = "",
) -> None:
    """Store document metadata and chunks in Neo4j with relationships.

    Creates:
    - Document node with metadata (including summary)
    - OWNS relationship from User to Document
    - Chunk nodes for each text chunk
    - CONTAINS relationships from Document to Chunks

    Args:
        document_id: UUID string for the document.
        user_id: ID of the user who uploaded the document.
        filename: Original filename.
        chunks: List of chunk dicts with id, text, position keys.
        summary: Auto-generated document summary (optional).
    """
    with neo4j_driver.session(database=settings.NEO4J_DATABASE) as session:
        # Create Document node with OWNS relationship to User
        # MERGE ensures anonymous users get auto-created as User nodes
        session.run(
            """
            MERGE (u:User {id: $user_id})
            CREATE (d:Document {
                id: $document_id,
                filename: $filename,
                user_id: $user_id,
                upload_date: datetime(),
                chunk_count: $chunk_count,
                summary: $summary
            })
            CREATE (u)-[:OWNS]->(d)
            """,
            document_id=document_id,
            user_id=user_id,
            filename=filename,
            chunk_count=len(chunks),
            summary=summary,
        )

        # Create Chunk nodes with CONTAINS relationship to Document
        # Using UNWIND for batch insert efficiency
        session.run(
            """
            MATCH (d:Document {id: $document_id})
            UNWIND $chunks AS chunk
            CREATE (c:Chunk {
                id: chunk.id,
                document_id: $document_id,
                text: chunk.text,
                position: chunk.position,
                embedding_id: chunk.id
            })
            CREATE (d)-[:CONTAINS]->(c)
            """,
            document_id=document_id,
            chunks=[
                {
                    "id": chunk["id"],
                    "text": chunk["text"],
                    "position": chunk["position"],
                }
                for chunk in chunks
            ],
        )


def store_chunks_in_qdrant(chunks: List[Dict]) -> None:
    """Store chunk embeddings in Qdrant.

    Wrapper around qdrant_client.upsert_chunks for consistency.

    Args:
        chunks: List of chunk dicts with id, vector, text, document_id,
                user_id, and position keys.
    """
    upsert_chunks(chunks)
