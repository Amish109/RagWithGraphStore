"""Backfill pre-generated summaries for all existing documents.

Dispatches Celery tasks to the 'summaries' queue for each document
that doesn't already have summaries in Redis.

Usage:
    cd backend && uv run python scripts/backfill_summaries.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.db.neo4j_client import neo4j_driver
from app.services.summary_storage import get_summary
from app.tasks import generate_summaries_task


def get_all_documents():
    """Get all documents from Neo4j."""
    with neo4j_driver.session(database=settings.NEO4J_DATABASE) as session:
        result = session.run(
            """
            MATCH (u:User)-[:OWNS]->(d:Document)
            RETURN d.id AS document_id, d.filename AS filename, u.id AS user_id
            """
        )
        return [dict(record) for record in result]


def main():
    docs = get_all_documents()
    print(f"Found {len(docs)} documents in Neo4j")

    dispatched = 0
    skipped = 0

    for doc in docs:
        # Check if brief summary already exists (if so, skip)
        existing = get_summary(doc["document_id"], "brief")
        if existing:
            print(f"  SKIP {doc['filename']} — already has summaries")
            skipped += 1
            continue

        # Dispatch to summaries queue
        generate_summaries_task.apply_async(
            kwargs={
                "document_id": doc["document_id"],
                "user_id": doc["user_id"],
                "filename": doc["filename"],
            },
            queue="summaries",
        )
        print(f"  DISPATCHED {doc['filename']} (id: {doc['document_id']})")
        dispatched += 1

    print(f"\nDone: {dispatched} dispatched, {skipped} skipped")
    print("Make sure the summaries worker is running:")
    print("  cd backend && uv run celery -A app.celery_app:celery worker --loglevel=info --pool=solo -Q summaries")


if __name__ == "__main__":
    main()
