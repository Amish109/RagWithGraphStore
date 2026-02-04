"""Document summarization service using LangChain.

Generates concise summaries for uploaded documents using map_reduce
chain for scalability with large documents (Pitfall #4).
"""

import logging
from typing import List

from langchain.chains.summarize import load_summarize_chain
from langchain_core.documents import Document as LCDocument
from langchain_openai import ChatOpenAI

from app.config import settings

logger = logging.getLogger(__name__)


async def generate_document_summary(chunks: List[str], max_length: int = 500) -> str:
    """Generate a summary of a document from its chunks.

    Uses map_reduce chain for large documents to avoid token limits.
    For small documents (<=4 chunks), uses stuff chain for efficiency.

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
        # Convert to LangChain Document format
        lc_docs = [LCDocument(page_content=chunk) for chunk in chunks]

        # Initialize LLM for summarization
        llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            temperature=0,
            openai_api_key=settings.OPENAI_API_KEY,
        )

        # Choose chain type based on document size
        # map_reduce handles large docs by summarizing chunks first, then combining
        if len(lc_docs) <= 4:
            chain = load_summarize_chain(llm, chain_type="stuff")
        else:
            chain = load_summarize_chain(llm, chain_type="map_reduce")

        # Generate summary
        result = await chain.ainvoke({"input_documents": lc_docs})
        summary = result.get("output_text", "")

        # Truncate if needed
        if len(summary) > max_length:
            summary = summary[:max_length - 3] + "..."

        logger.info(f"Generated summary: {len(summary)} chars from {len(chunks)} chunks")
        return summary

    except Exception as e:
        logger.error(f"Summarization failed: {e}")
        return ""
