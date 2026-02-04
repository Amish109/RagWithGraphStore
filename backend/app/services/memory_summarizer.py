"""Memory summarization service to prevent context overflow.

Provides:
- MemorySummarizer: Class for managing conversation memory with automatic summarization
- get_memory_summarizer(): Get singleton summarizer instance
- get_memory_with_summarization(): Convenience function for memory retrieval

Implements automatic memory compression when conversation context exceeds token limits,
while preserving recent interactions and critical facts (names, dates, decisions).
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from langchain_openai import ChatOpenAI

from app.config import settings
from app.db.mem0_client import get_mem0

logger = logging.getLogger(__name__)


class MemorySummarizer:
    """Manages conversation memory with automatic summarization.

    Monitors memory size and triggers summarization when context exceeds
    a configurable threshold. Preserves recent interactions verbatim
    and extracts critical facts from older memories.

    Addresses Phase 4 Success Criteria #3: Automatic memory summarization
    to prevent context overflow in long conversations.
    """

    def __init__(
        self,
        max_token_limit: Optional[int] = None,
        summarization_threshold: Optional[float] = None,
        recent_to_keep: int = 5,
    ):
        """Initialize the memory summarizer.

        Args:
            max_token_limit: Maximum tokens before summarization required.
                Defaults to MEMORY_MAX_TOKENS from settings.
            summarization_threshold: Trigger summarization at this percentage
                of max_token_limit. Defaults to MEMORY_SUMMARIZATION_THRESHOLD.
            recent_to_keep: Number of recent interactions to keep verbatim.
                These are never summarized to preserve immediate context.
        """
        self.mem0 = get_mem0()
        self.max_token_limit = max_token_limit or settings.MEMORY_MAX_TOKENS
        self.threshold = summarization_threshold or settings.MEMORY_SUMMARIZATION_THRESHOLD
        self.trigger_tokens = int(self.max_token_limit * self.threshold)
        self.recent_to_keep = recent_to_keep

        # LLM for summarization (slightly creative for good summaries)
        self.llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            temperature=0.3,
            openai_api_key=settings.OPENAI_API_KEY,
        )

        logger.info(
            f"MemorySummarizer initialized: max={self.max_token_limit}, "
            f"threshold={self.threshold}, trigger={self.trigger_tokens} tokens, "
            f"recent_to_keep={self.recent_to_keep}"
        )

    async def add_interaction(
        self,
        user_id: str,
        query: str,
        response: str,
        session_id: Optional[str] = None,
    ) -> None:
        """Add interaction to memory and trigger summarization if needed.

        Args:
            user_id: ID of the user.
            query: User's query/message.
            response: Assistant's response.
            session_id: Optional session ID for metadata.
        """
        metadata = {
            "timestamp": datetime.now().isoformat(),
        }
        if session_id:
            metadata["session_id"] = session_id

        # Add to Mem0
        self.mem0.add(
            messages=[
                {"role": "user", "content": query},
                {"role": "assistant", "content": response},
            ],
            user_id=user_id,
            metadata=metadata,
        )

        logger.debug(f"Added interaction for user {user_id}")

        # Check and summarize if needed
        summarized = await self._check_and_summarize(user_id)
        if summarized:
            logger.info(f"Triggered summarization for user {user_id}")

    async def get_memory_context(
        self,
        user_id: str,
        query: str,
        limit: int = 20,
    ) -> Dict:
        """Get relevant memory context for a query.

        Args:
            user_id: ID of the user.
            query: Query to find relevant memories for.
            limit: Maximum number of memories to return.

        Returns:
            Dict with:
            - memories: List of relevant memory items
            - token_estimate: Estimated token count
        """
        memories = self.mem0.search(query, user_id=user_id, limit=limit)

        return {
            "memories": memories,
            "token_estimate": self._estimate_tokens(memories),
        }

    def get_all_memories(self, user_id: str) -> List[Dict]:
        """Get all memories for a user.

        Args:
            user_id: ID of the user.

        Returns:
            List of all memory items.
        """
        return self.mem0.get_all(user_id=user_id)

    def _estimate_tokens(self, memories: List[Dict]) -> int:
        """Estimate token count for memories.

        Uses rough approximation: 4 characters = 1 token.

        Args:
            memories: List of memory items.

        Returns:
            Estimated token count.
        """
        total_chars = sum(len(str(m.get("memory", ""))) for m in memories)
        return total_chars // 4

    async def _check_and_summarize(self, user_id: str) -> bool:
        """Check memory size and summarize if exceeding threshold.

        Args:
            user_id: ID of the user.

        Returns:
            True if summarization was performed, False otherwise.
        """
        memories = self.mem0.get_all(user_id=user_id)

        if not memories:
            return False

        estimated_tokens = self._estimate_tokens(memories)
        logger.debug(
            f"Memory check for {user_id}: {estimated_tokens} tokens "
            f"(trigger at {self.trigger_tokens})"
        )

        if estimated_tokens > self.trigger_tokens:
            await self._perform_summarization(user_id, memories)
            return True

        return False

    async def _perform_summarization(
        self,
        user_id: str,
        memories: List[Dict],
    ) -> None:
        """Summarize older memories while keeping recent ones verbatim.

        CRITICAL (Pitfall #4): Preserves recent interactions and critical facts.

        Args:
            user_id: ID of the user.
            memories: All memories for the user.
        """
        # Sort by timestamp (most recent first)
        sorted_memories = sorted(
            memories,
            key=lambda m: m.get("metadata", {}).get("timestamp", ""),
            reverse=True,
        )

        # Keep recent interactions verbatim (Pitfall #4)
        recent = sorted_memories[: self.recent_to_keep]
        to_summarize = sorted_memories[self.recent_to_keep :]

        if not to_summarize:
            logger.debug("No memories to summarize after keeping recent ones")
            return

        logger.info(
            f"Summarizing {len(to_summarize)} memories for user {user_id}, "
            f"keeping {len(recent)} recent"
        )

        # Prepare memory text for summarization
        memory_text = "\n".join([str(m.get("memory", "")) for m in to_summarize])

        # Create summary with critical fact preservation
        try:
            response = await self.llm.ainvoke(
                [
                    {
                        "role": "system",
                        "content": """Create a concise summary of the user's conversation history.

CRITICAL: You MUST preserve ALL of the following if present:
- Names of people, places, organizations
- Specific dates, times, deadlines
- Decisions made and their reasoning
- User preferences and requirements
- Key facts and numbers
- Action items and commitments

Format as bullet points. Be concise but comprehensive.
Do NOT omit important details even if the summary becomes longer.""",
                    },
                    {"role": "user", "content": memory_text},
                ]
            )

            summary_content = response.content

            # Delete old memories
            deleted_count = 0
            for m in to_summarize:
                if "id" in m:
                    try:
                        self.mem0.delete(m["id"])
                        deleted_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to delete memory {m['id']}: {e}")

            logger.info(f"Deleted {deleted_count} old memories")

            # Add consolidated summary
            self.mem0.add(
                f"[Historical Summary - {len(to_summarize)} interactions consolidated]:\n{summary_content}",
                user_id=user_id,
                metadata={
                    "type": "summary",
                    "summarized_count": len(to_summarize),
                    "created_at": datetime.now().isoformat(),
                },
            )

            logger.info(
                f"Created summary for user {user_id}: "
                f"consolidated {len(to_summarize)} memories"
            )

        except Exception as e:
            logger.error(f"Failed to summarize memories for user {user_id}: {e}")
            # Don't delete memories if summarization failed
            raise

    async def force_summarization(self, user_id: str) -> bool:
        """Force summarization regardless of token threshold.

        Useful for manually triggering memory compression.

        Args:
            user_id: ID of the user.

        Returns:
            True if summarization was performed, False if no memories to summarize.
        """
        memories = self.mem0.get_all(user_id=user_id)

        if len(memories) <= self.recent_to_keep:
            logger.info(
                f"Not enough memories to summarize for user {user_id}: "
                f"{len(memories)} <= {self.recent_to_keep}"
            )
            return False

        await self._perform_summarization(user_id, memories)
        return True


# Module-level singleton
_summarizer: Optional[MemorySummarizer] = None


def get_memory_summarizer() -> MemorySummarizer:
    """Get or create the singleton MemorySummarizer instance.

    Returns:
        MemorySummarizer instance.
    """
    global _summarizer
    if _summarizer is None:
        _summarizer = MemorySummarizer()
    return _summarizer


async def get_memory_with_summarization(
    user_id: str,
    query: str,
    limit: int = 20,
) -> Dict:
    """Convenience function to get memory context with potential summarization.

    If the user's memory exceeds the token threshold, triggers summarization
    before returning the context.

    Args:
        user_id: ID of the user.
        query: Query to find relevant memories for.
        limit: Maximum number of memories to return.

    Returns:
        Dict with:
        - memories: List of relevant memory items
        - token_estimate: Estimated token count
    """
    summarizer = get_memory_summarizer()

    # Check and summarize if needed (background operation)
    await summarizer._check_and_summarize(user_id)

    # Return memory context
    return await summarizer.get_memory_context(user_id, query, limit)
