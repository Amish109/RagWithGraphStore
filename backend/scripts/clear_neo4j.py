"""Wipe all data from Neo4j: nodes, relationships, constraints, and indexes."""

from app.config import settings
from neo4j import GraphDatabase


def clear_neo4j():
    driver = GraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD),
    )

    with driver.session(database=settings.NEO4J_DATABASE) as session:
        # 1. Delete all nodes and relationships (batched to avoid timeout)
        print("Deleting all nodes and relationships...")
        while True:
            result = session.run(
                "MATCH (n) WITH n LIMIT 10000 DETACH DELETE n RETURN count(*) AS deleted"
            )
            deleted = result.single()["deleted"]
            print(f"  Deleted {deleted} nodes")
            if deleted == 0:
                break

        # 2. Drop all constraints
        print("Dropping constraints...")
        constraints = session.run("SHOW CONSTRAINTS").data()
        for c in constraints:
            name = c["name"]
            session.run(f"DROP CONSTRAINT {name}")
            print(f"  Dropped constraint: {name}")

        # 3. Drop all indexes
        print("Dropping indexes...")
        indexes = session.run("SHOW INDEXES").data()
        for idx in indexes:
            name = idx["name"]
            # Skip lookup indexes (internal, can't be dropped)
            if idx.get("type") == "LOOKUP":
                continue
            session.run(f"DROP INDEX {name}")
            print(f"  Dropped index: {name}")

    driver.close()
    print("\nNeo4j wiped clean!")


if __name__ == "__main__":
    clear_neo4j()
