"""Document summarization service using LangChain.

Generates concise summaries for uploaded documents using map_reduce
chain for scalability with large documents (Pitfall #4).

Phase 3: Generate summaries during document upload.
Phase 5: On-demand summarization with multiple summary types (QRY-06).

Summary Types:
- brief: 2-3 sentence overview
- detailed: Comprehensive coverage of all key points
- executive: Business-focused with recommendations
- bullet: Key points as bulleted list
"""

import hashlib
import logging
from typing import Dict, List, Optional

from langchain_core.prompts import ChatPromptTemplate

from app.config import settings
from app.db.neo4j_client import neo4j_driver
from app.services.llm_provider import get_llm

logger = logging.getLogger(__name__)


# Summary types with different prompts for on-demand summarization
SUMMARY_PROMPTS: Dict[str, str] = {
    "brief": "Summarize this document in 2-3 sentences. Focus on the main point.",
    "detailed": "Provide a comprehensive summary covering all key points, organized by topic.",
    "executive": "Create an executive summary suitable for busy stakeholders. Include key findings, recommendations, and action items.",
    "bullet": "Summarize the document as a bulleted list of key points.",
}


def _cache_key(document_id: str, summary_type: str) -> str:
    """Generate cache key for summary.

    Args:
        document_id: ID of the document being summarized.
        summary_type: Type of summary (brief, detailed, executive, bullet).

    Returns:
        SHA-256 hash of document_id:summary_type.
    """
    return hashlib.sha256(f"{document_id}:{summary_type}".encode()).hexdigest()


async def get_document_text(document_id: str, user_id: str) -> Optional[str]:
    """Retrieve full document text from stored chunks.

    CRITICAL: Filter by user_id for multi-tenant isolation.

    Args:
        document_id: ID of the document to retrieve.
        user_id: ID of the user (for access control).

    Returns:
        Concatenated chunk texts ordered by position, or None if not found.
    """
    with neo4j_driver.session(database=settings.NEO4J_DATABASE) as session:
        result = session.run(
            """
            MATCH (d:Document {id: $doc_id, user_id: $user_id})-[:CONTAINS]->(c:Chunk)
            RETURN c.text AS text, c.position AS position
            ORDER BY c.position
            """,
            doc_id=document_id,
            user_id=user_id,
        )

        chunks = list(result)
        if not chunks:
            return None

        return "\n\n".join(record["text"] for record in chunks)


async def summarize_document(
    document_id: str,
    user_id: str,
    summary_type: str = "brief",
    max_chunks: int = 50,
    use_cache: bool = True,
    cache_dict: Optional[Dict] = None,
) -> Optional[dict]:
    """Generate on-demand summary for a document (QRY-06).

    Uses map-reduce pattern for long documents:
    1. For short documents (<10000 chars): direct "stuff" method
    2. For long documents: map each chunk, reduce to final summary

    Args:
        document_id: ID of the document to summarize.
        user_id: ID of the user (for access control).
        summary_type: Type of summary (brief, detailed, executive, bullet).
        max_chunks: Maximum number of chunks to process in map-reduce.
        use_cache: Whether to check/store in cache.
        cache_dict: In-memory cache dictionary (simple dict for now).

    Returns:
        Dict with document_id, summary_type, summary, method, and optional chunks_processed.
        Returns None if document not found or user doesn't have access.
    """
    cache_key = _cache_key(document_id, summary_type)

    # Check cache first
    if use_cache and cache_dict is not None:
        cached = cache_dict.get(f"summary:{cache_key}")
        if cached:
            logger.info(f"Cache hit for summary: {document_id}:{summary_type}")
            return cached

    # Get document text
    document_text = await get_document_text(document_id, user_id)
    if not document_text:
        logger.warning(f"Document not found or no access: {document_id}")
        return None

    # Get summary prompt
    summary_prompt = SUMMARY_PROMPTS.get(summary_type, SUMMARY_PROMPTS["brief"])

    llm = get_llm(temperature=0.3)

    # For short documents, use "stuff" method (single prompt)
    if len(document_text) < 10000:
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a document summarization expert. Create clear, accurate summaries."),
            ("user", "{instruction}\n\nDocument:\n{document}")
        ])

        messages = prompt.format_messages(
            instruction=summary_prompt,
            document=document_text
        )
        response = await llm.ainvoke(messages)

        result = {
            "document_id": document_id,
            "summary_type": summary_type,
            "summary": response.content,
            "method": "stuff"
        }
        logger.info(f"Generated stuff summary for {document_id}: {len(response.content)} chars")
    else:
        # For long documents, use map-reduce
        # Split into chunks and summarize each
        chunk_size = 4000
        text_chunks = [
            document_text[i:i + chunk_size]
            for i in range(0, len(document_text), chunk_size)
        ]

        # Map: Summarize each chunk
        map_prompt = ChatPromptTemplate.from_messages([
            ("system", "Summarize this text section concisely, preserving key information."),
            ("user", "{text}")
        ])

        chunk_summaries = []
        for chunk in text_chunks[:max_chunks]:
            messages = map_prompt.format_messages(text=chunk)
            response = await llm.ainvoke(messages)
            chunk_summaries.append(response.content)

        # Reduce: Combine chunk summaries
        combined = "\n\n".join(chunk_summaries)
        reduce_prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a document summarization expert. Create clear, accurate summaries."),
            ("user", "{instruction}\n\nSection summaries:\n{summaries}")
        ])

        messages = reduce_prompt.format_messages(
            instruction=summary_prompt,
            summaries=combined
        )
        response = await llm.ainvoke(messages)

        result = {
            "document_id": document_id,
            "summary_type": summary_type,
            "summary": response.content,
            "method": "map_reduce",
            "chunks_processed": len(text_chunks[:max_chunks])
        }
        logger.info(
            f"Generated map_reduce summary for {document_id}: "
            f"{len(response.content)} chars from {len(text_chunks[:max_chunks])} chunks"
        )

    # Cache result
    if use_cache and cache_dict is not None:
        cache_dict[f"summary:{cache_key}"] = result

    return result


async def generate_document_summary(chunks: List[str], max_length: int = 500) -> str:
    """Generate a summary of a document from its chunks.

    Uses map_reduce pattern for large documents to avoid token limits.
    For small documents (<=4 chunks), uses direct "stuff" method.

    CRITICAL: Uses map_reduce for >4 chunks to prevent context overflow (Pitfall #4).

    Args:
        chunks: List of text chunks from the document.
        max_length: Maximum summary length in characters (approximate).

    Returns:
        Summary string, or empty string if summarization fails.
    """
    if not chunks:
        return ""

    try:
        llm = get_llm(temperature=0)

        # For small documents, use direct "stuff" method
        if len(chunks) <= 4:
            combined_text = "\n\n".join(chunks)
            prompt = ChatPromptTemplate.from_messages([
                ("system", "You are a document summarization expert. Create clear, accurate summaries."),
                ("user", "Provide a brief summary of this document in 2-3 sentences:\n\n{document}")
            ])
            messages = prompt.format_messages(document=combined_text)
            response = await llm.ainvoke(messages)
            summary = response.content
        else:
            # For large documents, use map-reduce pattern
            # Map: Summarize each chunk
            map_prompt = ChatPromptTemplate.from_messages([
                ("system", "Summarize this text section concisely, preserving key information."),
                ("user", "{text}")
            ])

            chunk_summaries = []
            for chunk in chunks:
                messages = map_prompt.format_messages(text=chunk)
                response = await llm.ainvoke(messages)
                chunk_summaries.append(response.content)

            # Reduce: Combine chunk summaries
            combined = "\n\n".join(chunk_summaries)
            reduce_prompt = ChatPromptTemplate.from_messages([
                ("system", "You are a document summarization expert. Create clear, accurate summaries."),
                ("user", "Combine these section summaries into a brief 2-3 sentence summary:\n\n{summaries}")
            ])
            messages = reduce_prompt.format_messages(summaries=combined)
            response = await llm.ainvoke(messages)
            summary = response.content

        # Truncate if needed
        if len(summary) > max_length:
            summary = summary[:max_length - 3] + "..."

        logger.info(f"Generated summary: {len(summary)} chars from {len(chunks)} chunks")
        return summary

    except Exception as e:
        logger.error(f"Summarization failed: {e}")
        return ""
