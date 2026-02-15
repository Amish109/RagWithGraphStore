"""Redis-backed storage for document summaries with streaming support.

Key formats:
- summary:{document_id}:{summary_type}         — Completed summary text
- summary_stream:{document_id}:{summary_type}  — In-progress streaming text (appended to)
- summary_status:{document_id}:{summary_type}  — Per-type status: "generating" | "completed" | "failed"
- summary_status:{document_id}                 — Overall generation status (legacy, for bulk generation)

Flow:
1. Celery task starts → sets status to "generating", appends tokens to stream key
2. Celery task finishes → copies stream key to summary key, sets status to "completed"
3. Frontend polls stream key for partial content, falls back to summary key for completed
"""

import json
import logging
from typing import Optional

import redis

from app.config import settings

logger = logging.getLogger(__name__)

SUMMARY_TYPES = ["brief", "detailed", "executive", "bullet"]

_SUMMARY_KEY_PREFIX = "summary:"
_STREAM_KEY_PREFIX = "summary_stream:"
_TYPE_STATUS_PREFIX = "summary_type_status:"
_STATUS_KEY_PREFIX = "summary_status:"
_SUMMARY_TTL = 604800  # 7 days
_STREAM_TTL = 3600  # 1 hour (in-progress data)


def _redis_client() -> redis.Redis:
    return redis.from_url(settings.REDIS_URL, decode_responses=True)


# --- Completed summaries ---

def store_summary(document_id: str, summary_type: str, summary_text: str) -> None:
    """Store a completed summary in Redis."""
    r = _redis_client()
    key = f"{_SUMMARY_KEY_PREFIX}{document_id}:{summary_type}"
    r.setex(key, _SUMMARY_TTL, summary_text)


def get_summary(document_id: str, summary_type: str) -> Optional[str]:
    """Retrieve a completed summary from Redis. Returns None if not found."""
    r = _redis_client()
    key = f"{_SUMMARY_KEY_PREFIX}{document_id}:{summary_type}"
    return r.get(key)


# --- Streaming / in-progress summaries ---

def append_stream_chunk(document_id: str, summary_type: str, chunk: str) -> None:
    """Append a token/chunk to the in-progress streaming summary."""
    r = _redis_client()
    key = f"{_STREAM_KEY_PREFIX}{document_id}:{summary_type}"
    r.append(key, chunk)
    r.expire(key, _STREAM_TTL)


def get_stream_content(document_id: str, summary_type: str) -> Optional[str]:
    """Get all content written so far for an in-progress summary."""
    r = _redis_client()
    key = f"{_STREAM_KEY_PREFIX}{document_id}:{summary_type}"
    return r.get(key)


def get_stream_length(document_id: str, summary_type: str) -> int:
    """Get length of content written so far (for offset-based polling)."""
    r = _redis_client()
    key = f"{_STREAM_KEY_PREFIX}{document_id}:{summary_type}"
    return r.strlen(key)


def get_stream_content_from(document_id: str, summary_type: str, offset: int) -> str:
    """Get content from a specific offset (new content since last read)."""
    r = _redis_client()
    key = f"{_STREAM_KEY_PREFIX}{document_id}:{summary_type}"
    content = r.getrange(key, offset, -1)
    return content or ""


def clear_stream(document_id: str, summary_type: str) -> None:
    """Clear the in-progress stream data."""
    r = _redis_client()
    r.delete(f"{_STREAM_KEY_PREFIX}{document_id}:{summary_type}")


# --- Per-type status ---

def set_type_status(document_id: str, summary_type: str, status: str) -> None:
    """Set generation status for a specific summary type."""
    r = _redis_client()
    key = f"{_TYPE_STATUS_PREFIX}{document_id}:{summary_type}"
    r.setex(key, _STREAM_TTL, status)


def get_type_status(document_id: str, summary_type: str) -> Optional[str]:
    """Get generation status for a specific summary type. Returns 'generating', 'completed', 'failed', or None."""
    r = _redis_client()
    key = f"{_TYPE_STATUS_PREFIX}{document_id}:{summary_type}"
    return r.get(key)


# --- Bulk status (legacy, used by generate_summaries_task) ---

def set_summary_status(
    document_id: str,
    status: str,
    message: str = "",
    progress: int = 0,
) -> None:
    """Track overall summary generation status in Redis."""
    r = _redis_client()
    key = f"{_STATUS_KEY_PREFIX}{document_id}"
    data = {"status": status, "message": message, "progress": progress}
    r.setex(key, 3600, json.dumps(data))


def get_summary_status(document_id: str) -> Optional[dict]:
    """Get overall summary generation status."""
    r = _redis_client()
    key = f"{_STATUS_KEY_PREFIX}{document_id}"
    raw = r.get(key)
    if raw:
        return json.loads(raw)
    return None


# --- Cleanup ---

def delete_summaries(document_id: str) -> None:
    """Delete all summaries, streams, and status for a document."""
    r = _redis_client()
    for st in SUMMARY_TYPES:
        r.delete(f"{_SUMMARY_KEY_PREFIX}{document_id}:{st}")
        r.delete(f"{_STREAM_KEY_PREFIX}{document_id}:{st}")
        r.delete(f"{_TYPE_STATUS_PREFIX}{document_id}:{st}")
    r.delete(f"{_STATUS_KEY_PREFIX}{document_id}")
