"""Response generation workflow nodes.

Provides nodes for generating final responses with citations
from document comparison analysis.
"""

import logging
from typing import Dict, List

from app.workflows.state import DocumentComparisonState

logger = logging.getLogger(__name__)


def format_list(items: List[str], bullet: str = "-") -> str:
    """Format list items as bullet points.

    Args:
        items: List of string items.
        bullet: Bullet character to use.

    Returns:
        Formatted string with bullet points.
    """
    if not items:
        return f"{bullet} No items identified.\n"
    return "\n".join([f"{bullet} {item}" for item in items]) + "\n"


def extract_citations(retrieved_chunks: dict) -> List[dict]:
    """Extract citations from retrieved chunks.

    Creates a list of citation references from all chunks used
    in the comparison analysis.

    Args:
        retrieved_chunks: Dict mapping doc_id to list of chunks.

    Returns:
        List of citation dicts with doc_id, chunk_id, text snippet, filename.
    """
    citations = []

    for doc_id, chunks in retrieved_chunks.items():
        for chunk in chunks:
            citation = {
                "doc_id": doc_id,
                "chunk_id": chunk.get("id", "unknown"),
                "text": chunk.get("text", "")[:200],  # Snippet for citation
                "filename": chunk.get("filename", "Unknown"),
                "position": chunk.get("position", 0),
                "score": chunk.get("score", 0.0),
            }
            citations.append(citation)

    # Sort by score (highest first) then by document
    citations.sort(key=lambda c: (-c.get("score", 0), c.get("doc_id", "")))

    logger.debug(f"Extracted {len(citations)} citations")
    return citations


async def generate_response_node(state: DocumentComparisonState) -> Dict:
    """Generate final comparison response with citations.

    Assembles the final response from analysis results and
    extracts citations from retrieved chunks for attribution.

    Args:
        state: Current workflow state with analysis results and retrieved_chunks.

    Returns:
        Dict with response, citations, and status.
    """
    logger.info("Generating comparison response")

    # Check for analysis failure
    if state.get("error"):
        return {
            "response": f"Unable to complete comparison: {state['error']}",
            "citations": [],
            "status": "complete_with_error",
        }

    # Build response from analysis
    response_parts = [
        "## Document Comparison Analysis\n",
    ]

    # Add query context
    response_parts.append(f"**Query:** {state['query']}\n")

    # Add documents compared
    doc_count = len(state["document_ids"])
    response_parts.append(f"**Documents compared:** {doc_count}\n")

    # Add similarities section
    response_parts.append("\n### Similarities\n")
    if state["similarities"]:
        response_parts.append(format_list(state["similarities"]))
    else:
        response_parts.append("- No clear similarities identified.\n")

    # Add differences section
    response_parts.append("\n### Differences\n")
    if state["differences"]:
        response_parts.append(format_list(state["differences"]))
    else:
        response_parts.append("- No notable differences identified.\n")

    # Add cross-document insights
    response_parts.append("\n### Cross-Document Insights\n")
    if state["cross_document_insights"]:
        response_parts.append(format_list(state["cross_document_insights"]))
    else:
        response_parts.append("- No cross-document insights identified.\n")

    # Extract citations for attribution
    citations = extract_citations(state["retrieved_chunks"])

    # Add citations reference section
    if citations:
        response_parts.append("\n### Sources\n")
        seen_docs = set()
        for citation in citations:
            filename = citation.get("filename", "Unknown")
            if filename not in seen_docs:
                seen_docs.add(filename)
                response_parts.append(f"- {filename}\n")

    response = "\n".join(response_parts)

    logger.info(
        f"Generated response with {len(response)} chars and {len(citations)} citations"
    )

    return {
        "response": response,
        "citations": citations,
        "status": "complete",
    }
