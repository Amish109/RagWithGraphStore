"""Redis-backed task tracking for document processing.

Persists task status in Redis so it survives:
- Server restarts
- Page refreshes
- Worker crashes

Key format: task:{document_id}
TTL: 1 hour (auto-cleanup)

Status stages:
- PENDING → EXTRACTING → CHUNKING → EMBEDDING → SUMMARIZING
  → INDEXING → EXTRACTING_ENTITIES → COMPLETED
- Any stage can transition to FAILED
"""

import json
import logging
from enum import Enum
from typing import Dict, List, Optional

import redis

from app.config import settings

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """Document processing status stages."""

    PENDING = "pending"
    EXTRACTING = "extracting"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    INDEXING = "indexing"
    SUMMARIZING = "summarizing"
    EXTRACTING_ENTITIES = "extracting_entities"
    COMPLETED = "completed"
    FAILED = "failed"


# Progress percentages for each stage
STAGE_PROGRESS = {
    TaskStatus.PENDING: 0,
    TaskStatus.EXTRACTING: 10,
    TaskStatus.CHUNKING: 25,
    TaskStatus.EMBEDDING: 40,
    TaskStatus.INDEXING: 60,
    TaskStatus.SUMMARIZING: 70,  # Kept for on-demand summary tracking
    TaskStatus.EXTRACTING_ENTITIES: 75,
    TaskStatus.COMPLETED: 100,
    TaskStatus.FAILED: 0,
}

# Redis key prefix and TTL
_KEY_PREFIX = "task:"
_TTL_SECONDS = 3600  # 1 hour


def _redis_client() -> redis.Redis:
    """Get a synchronous Redis client (Celery workers are sync)."""
    return redis.from_url(settings.REDIS_URL, decode_responses=True)


class TaskTracker:
    """Redis-backed task tracker.

    All state is stored in Redis, so it persists across server restarts,
    page refreshes, and is accessible from both the FastAPI app and
    Celery workers.

    Usage:
        task_tracker.create(doc_id, user_id, filename)
        task_tracker.update(doc_id, TaskStatus.EXTRACTING, "Extracting text...")
        info = task_tracker.get(doc_id)
        task_tracker.fail(doc_id, "Error message")
    """

    def _key(self, document_id: str) -> str:
        return f"{_KEY_PREFIX}{document_id}"

    def create(self, document_id: str, user_id: str, filename: str) -> dict:
        """Create a new task in PENDING state."""
        r = _redis_client()
        data = {
            "document_id": document_id,
            "user_id": user_id,
            "filename": filename,
            "status": TaskStatus.PENDING.value,
            "progress": 0,
            "message": "Queued for processing",
            "error": None,
        }
        r.setex(self._key(document_id), _TTL_SECONDS, json.dumps(data))
        return data

    def update(
        self, document_id: str, status: TaskStatus, message: str,
        progress: Optional[int] = None,
    ) -> Optional[dict]:
        """Update task status and progress.

        Args:
            document_id: Document ID.
            status: New task status.
            message: Human-readable status message.
            progress: Optional custom progress (0-100). If None, uses STAGE_PROGRESS default.
        """
        r = _redis_client()
        raw = r.get(self._key(document_id))
        if not raw:
            return None
        data = json.loads(raw)
        data["status"] = status.value
        data["progress"] = progress if progress is not None else STAGE_PROGRESS.get(status, 0)
        data["message"] = message
        r.setex(self._key(document_id), _TTL_SECONDS, json.dumps(data))
        logger.debug(f"Task {document_id}: {status.value} ({data['progress']}%) - {message}")
        return data

    def complete(
        self, document_id: str, message: str = "Processing complete"
    ) -> Optional[dict]:
        """Mark task as completed."""
        return self.update(document_id, TaskStatus.COMPLETED, message)

    def fail(self, document_id: str, error: str) -> Optional[dict]:
        """Mark task as failed with error message."""
        r = _redis_client()
        raw = r.get(self._key(document_id))
        if not raw:
            return None
        data = json.loads(raw)
        data["status"] = TaskStatus.FAILED.value
        data["progress"] = 0
        data["message"] = "Processing failed"
        data["error"] = error
        r.setex(self._key(document_id), _TTL_SECONDS, json.dumps(data))
        logger.error(f"Task {document_id} failed: {error}")
        return data

    def get(self, document_id: str) -> Optional[dict]:
        """Get task info by document ID. Returns dict or None."""
        r = _redis_client()
        raw = r.get(self._key(document_id))
        if not raw:
            return None
        return json.loads(raw)

    def get_user_tasks(self, user_id: str) -> List[dict]:
        """Get all active tasks for a user."""
        r = _redis_client()
        tasks = []
        for key in r.scan_iter(f"{_KEY_PREFIX}*"):
            raw = r.get(key)
            if raw:
                data = json.loads(raw)
                if data.get("user_id") == user_id:
                    tasks.append(data)
        return tasks

    def remove(self, document_id: str) -> None:
        """Remove a task from tracking."""
        r = _redis_client()
        r.delete(self._key(document_id))


# Global task tracker instance
task_tracker = TaskTracker()
