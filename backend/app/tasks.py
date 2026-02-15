"""Celery tasks for document processing.

Runs in a separate Celery worker process, so:
- Server restarts don't kill processing
- Tasks survive page refreshes
- Status is tracked in Redis (persistent)

Start worker: celery -A app.celery_app:celery worker --loglevel=info
"""

import asyncio
import logging

from app.celery_app import celery

logger = logging.getLogger(__name__)


@celery.task(bind=True, name="process_document")
def process_document_task(
    self,
    file_path: str,
    document_id: str,
    user_id: str,
    filename: str,
    file_size: int = 0,
):
    """Celery task wrapping the async document processing pipeline.

    This runs in the Celery worker process. Since the pipeline is async,
    we create a fresh event loop per task to avoid "Event loop is closed"
    errors from asyncio.run() closing the loop and leaving cached HTTP
    clients (Ollama/LangChain) with stale loop references.
    """
    from app.services.document_processor import process_document_pipeline

    logger.info(f"Celery task started: {filename} (id: {document_id})")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(
            process_document_pipeline(
                file_path=file_path,
                document_id=document_id,
                user_id=user_id,
                filename=filename,
                file_size=file_size,
            )
        )
        logger.info(f"Celery task completed: {filename} (id: {document_id})")
    except Exception as e:
        logger.error(f"Celery task failed: {filename} (id: {document_id}): {e}")
        # task_tracker.fail() is already called in process_document_pipeline
        raise
    finally:
        try:
            # Cancel any remaining tasks and shut down gracefully
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            loop.run_until_complete(loop.shutdown_asyncgens())
        finally:
            loop.close()
