"""Celery application configuration.

Uses Redis as both broker and result backend.
Celery worker handles document processing in a separate process,
so server restarts don't kill running tasks.
"""

from celery import Celery

from app.config import settings

celery = Celery(
    "rag_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,  # Acknowledge after task completes (retry on worker crash)
    worker_prefetch_multiplier=1,  # Don't grab extra tasks
    result_expires=3600,  # Results expire after 1 hour
    task_routes={
        "generate_summaries": {"queue": "summaries"},
        "generate_single_summary": {"queue": "summaries"},
    },
)

# Auto-discover tasks from app.tasks module
celery.autodiscover_tasks(["app"])
