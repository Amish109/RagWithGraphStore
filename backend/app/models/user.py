"""User model operations for Neo4j database.

Provides functions for creating and retrieving user records.
User nodes are stored with: id, email, hashed_password, created_at
"""

from typing import Optional

from app.config import settings
from app.db.neo4j_client import neo4j_driver


def create_user(email: str, hashed_password: str, user_id: str, role: str = "user") -> dict:
    """Create a new user in Neo4j.

    Args:
        email: User's email address (must be unique)
        hashed_password: Pre-hashed password (never pass plain text)
        user_id: UUID string for the user
        role: User role ("user" or "admin"), defaults to "user"

    Returns:
        Dict containing the created user's properties
    """
    with neo4j_driver.session(database=settings.NEO4J_DATABASE) as session:
        result = session.run(
            """
            CREATE (u:User {
                id: $id,
                email: $email,
                hashed_password: $hashed_password,
                role: $role,
                created_at: datetime()
            })
            RETURN u
            """,
            id=user_id,
            email=email,
            hashed_password=hashed_password,
            role=role,
        )
        record = result.single()
        return dict(record["u"])


def get_user_by_email(email: str) -> Optional[dict]:
    """Retrieve a user by their email address.

    Args:
        email: Email address to search for

    Returns:
        Dict containing user properties if found, None otherwise
    """
    with neo4j_driver.session(database=settings.NEO4J_DATABASE) as session:
        result = session.run(
            """
            MATCH (u:User {email: $email})
            RETURN u
            """,
            email=email,
        )
        record = result.single()
        if record:
            return dict(record["u"])
        return None


def get_user_by_id(user_id: str) -> Optional[dict]:
    """Retrieve a user by their ID.

    Args:
        user_id: UUID string to search for

    Returns:
        Dict containing user properties if found, None otherwise
    """
    with neo4j_driver.session(database=settings.NEO4J_DATABASE) as session:
        result = session.run(
            """
            MATCH (u:User {id: $user_id})
            RETURN u
            """,
            user_id=user_id,
        )
        record = result.single()
        if record:
            return dict(record["u"])
        return None
