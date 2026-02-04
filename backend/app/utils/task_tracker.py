"""Task tracking for document processing with TTL cleanup.

Provides in-memory tracking of document processing stages:
- PENDING: Queued for processing
- EXTRACTING: Extracting text from PDF/DOCX
- CHUNKING: Splitting into semantic chunks
- EMBEDDING: Generating embeddings
- INDEXING: Storing in Neo4j and Qdrant
- SUMMARIZING: Generating document summary
- COMPLETED: Processing finished successfully
- FAILED: Processing failed with error

CRITICAL: Implements TTL cleanup to prevent memory exhaustion (Pitfall #3).
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from threading import Lock
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """Document processing status stages."""

    PENDING = "pending"
    EXTRACTING = "extracting"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    INDEXING = "indexing"
    SUMMARIZING = "summarizing"
    COMPLETED = "completed"
    FAILED = "failed"


# Progress percentages for each stage
STAGE_PROGRESS = {
    TaskStatus.PENDING: 0,
    TaskStatus.EXTRACTING: 10,
    TaskStatus.CHUNKING: 25,
    TaskStatus.EMBEDDING: 40,
    TaskStatus.INDEXING: 70,
    TaskStatus.SUMMARIZING: 85,
    TaskStatus.COMPLETED: 100,
    TaskStatus.FAILED: 0,
}


@dataclass
class TaskInfo:
    """Information about a document processing task."""

    document_id: str
    user_id: str
    filename: str
    status: TaskStatus
    progress: int
    message: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    error: Optional[str] = None


class TaskTracker:
    """Thread-safe task tracker with TTL cleanup.

    Usage:
        task_tracker.create(doc_id, user_id, filename)
        task_tracker.update(doc_id, TaskStatus.EXTRACTING, "Extracting text...")
        info = task_tracker.get(doc_id)
        task_tracker.fail(doc_id, "Error message")
    """

    def __init__(self, ttl_hours: int = 1):
        self._tasks: Dict[str, TaskInfo] = {}
        self._lock = Lock()
        self._ttl = timedelta(hours=ttl_hours)

    def create(self, document_id: str, user_id: str, filename: str) -> TaskInfo:
        """Create a new task in PENDING state."""
        with self._lock:
            self._cleanup_old_tasks()
            task = TaskInfo(
                document_id=document_id,
                user_id=user_id,
                filename=filename,
                status=TaskStatus.PENDING,
                progress=0,
                message="Queued for processing",
            )
            self._tasks[document_id] = task
            return task

    def update(
        self, document_id: str, status: TaskStatus, message: str
    ) -> Optional[TaskInfo]:
        """Update task status and progress."""
        with self._lock:
            task = self._tasks.get(document_id)
            if task:
                task.status = status
                task.progress = STAGE_PROGRESS.get(status, 0)
                task.message = message
                task.updated_at = datetime.utcnow()
                logger.debug(f"Task {document_id}: {status.value} - {message}")
            return task

    def complete(
        self, document_id: str, message: str = "Processing complete"
    ) -> Optional[TaskInfo]:
        """Mark task as completed."""
        return self.update(document_id, TaskStatus.COMPLETED, message)

    def fail(self, document_id: str, error: str) -> Optional[TaskInfo]:
        """Mark task as failed with error message."""
        with self._lock:
            task = self._tasks.get(document_id)
            if task:
                task.status = TaskStatus.FAILED
                task.progress = 0
                task.message = "Processing failed"
                task.error = error
                task.updated_at = datetime.utcnow()
                logger.error(f"Task {document_id} failed: {error}")
            return task

    def get(self, document_id: str) -> Optional[TaskInfo]:
        """Get task info by document ID."""
        with self._lock:
            return self._tasks.get(document_id)

    def get_user_tasks(self, user_id: str) -> List[TaskInfo]:
        """Get all tasks for a user."""
        with self._lock:
            return [t for t in self._tasks.values() if t.user_id == user_id]

    def remove(self, document_id: str) -> None:
        """Remove a task from tracking."""
        with self._lock:
            self._tasks.pop(document_id, None)

    def _cleanup_old_tasks(self) -> None:
        """Remove tasks older than TTL. Called within lock."""
        cutoff = datetime.utcnow() - self._ttl
        to_remove = [
            doc_id
            for doc_id, task in self._tasks.items()
            if task.updated_at < cutoff
        ]
        for doc_id in to_remove:
            del self._tasks[doc_id]
        if to_remove:
            logger.debug(f"Cleaned up {len(to_remove)} old tasks")


# Global task tracker instance
task_tracker = TaskTracker(ttl_hours=1)
