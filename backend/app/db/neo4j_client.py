"""Neo4j database client and schema initialization.

Provides:
- neo4j_driver: Singleton driver instance for Neo4j connections
- close_neo4j(): Close the driver connection
- init_neo4j_schema(): Initialize constraints and indexes
"""

from neo4j import GraphDatabase

from app.config import settings

# Initialize Neo4j driver (singleton)
neo4j_driver = GraphDatabase.driver(
    settings.NEO4J_URI,
    auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD),
    max_connection_lifetime=3600,  # 1 hour
    max_connection_pool_size=50,
    connection_acquisition_timeout=60,
)


def close_neo4j() -> None:
    """Close Neo4j driver connection."""
    neo4j_driver.close()


def init_neo4j_schema() -> None:
    """Initialize Neo4j schema with constraints and indexes.

    Run once during deployment or in migration script.
    CRITICAL: Define schema BEFORE data ingestion to prevent performance issues.

    Schema design:
    - User: Stores user accounts (id, email, hashed_password, created_at)
    - Document: Stores document metadata (id, user_id, filename, upload_date)
    - Chunk: Stores document chunks (id, document_id, text, position, embedding_id)

    Relationships:
    - (User)-[:OWNS]->(Document)
    - (Document)-[:CONTAINS]->(Chunk)
    """
    with neo4j_driver.session(database=settings.NEO4J_DATABASE) as session:
        # Constraints (also create implicit indexes on constrained properties)
        session.run(
            """
            CREATE CONSTRAINT user_id_unique IF NOT EXISTS
            FOR (u:User) REQUIRE u.id IS UNIQUE
            """
        )

        session.run(
            """
            CREATE CONSTRAINT document_id_unique IF NOT EXISTS
            FOR (d:Document) REQUIRE d.id IS UNIQUE
            """
        )

        session.run(
            """
            CREATE CONSTRAINT chunk_id_unique IF NOT EXISTS
            FOR (c:Chunk) REQUIRE c.id IS UNIQUE
            """
        )

        # Additional indexes for filtering (multi-tenancy support)
        session.run(
            """
            CREATE INDEX user_email IF NOT EXISTS
            FOR (u:User) ON (u.email)
            """
        )

        session.run(
            """
            CREATE INDEX document_user_id IF NOT EXISTS
            FOR (d:Document) ON (d.user_id)
            """
        )

        session.run(
            """
            CREATE INDEX chunk_document_id IF NOT EXISTS
            FOR (c:Chunk) ON (c.document_id)
            """
        )

        # Entity constraints and indexes (GraphRAG)
        session.run(
            """
            CREATE CONSTRAINT entity_id_unique IF NOT EXISTS
            FOR (e:Entity) REQUIRE e.id IS UNIQUE
            """
        )

        session.run(
            """
            CREATE INDEX entity_normalized_name IF NOT EXISTS
            FOR (e:Entity) ON (e.normalized_name)
            """
        )

        session.run(
            """
            CREATE INDEX entity_type IF NOT EXISTS
            FOR (e:Entity) ON (e.type)
            """
        )

        print("Neo4j schema initialized with constraints and indexes")
