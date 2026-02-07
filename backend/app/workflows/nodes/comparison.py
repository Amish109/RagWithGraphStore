"""Comparison analysis workflow nodes.

Provides nodes for analyzing similarities and differences
between documents using LLM-powered analysis.
"""

import json
import logging
from typing import Dict, List

from app.services.llm_provider import get_llm
from app.workflows.state import DocumentComparisonState

logger = logging.getLogger(__name__)


def format_comparison_context(state: DocumentComparisonState) -> str:
    """Format retrieved chunks and graph context for LLM analysis.

    Args:
        state: Current workflow state with retrieved_chunks and graph_context.

    Returns:
        Formatted string for LLM input.
    """
    sections = []

    for doc_id in state["document_ids"]:
        chunks = state["retrieved_chunks"].get(doc_id, [])
        graph_ctx = state["graph_context"].get(doc_id, {})
        filename = graph_ctx.get("filename") or "Unknown Document"

        section = f"\n=== Document: {filename} (ID: {doc_id}) ===\n"

        # Add chunk content
        if chunks:
            section += "\nKey Content:\n"
            for i, chunk in enumerate(chunks, 1):
                text = chunk.get("text", "")[:500]  # Truncate for token efficiency
                section += f"\n[Chunk {i}] {text}\n"
        else:
            section += "\nNo relevant chunks found.\n"

        # Add entity relationships if available
        entity_rels = graph_ctx.get("entity_relations", [])
        if entity_rels:
            section += "\nEntity Relationships:\n"
            for rel in entity_rels[:10]:  # Limit for token efficiency
                entity = rel.get("entity", "Unknown")
                related = rel.get("related_entity", "")
                relation = rel.get("relation", "")
                if related and relation:
                    section += f"- {entity} --[{relation}]--> {related}\n"
                elif entity:
                    section += f"- {entity}\n"

        sections.append(section)

    return "\n".join(sections)


def parse_analysis_response(response_text: str) -> Dict[str, List[str]]:
    """Parse LLM analysis response into structured format.

    Attempts to parse JSON response, falls back to text extraction.

    Args:
        response_text: Raw LLM response text.

    Returns:
        Dict with similarities, differences, and insights lists.
    """
    # Try JSON parsing first
    try:
        # Look for JSON block in response
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            json_str = response_text[json_start:json_end].strip()
        elif "{" in response_text:
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            json_str = response_text[json_start:json_end]
        else:
            raise ValueError("No JSON found")

        parsed = json.loads(json_str)
        return {
            "similarities": parsed.get("similarities", []),
            "differences": parsed.get("differences", []),
            "insights": parsed.get("insights", parsed.get("cross_document_insights", [])),
        }
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning(f"Failed to parse JSON response, using fallback: {e}")

    # Fallback: Extract lists from text
    result = {
        "similarities": [],
        "differences": [],
        "insights": [],
    }

    current_section = None
    for line in response_text.split("\n"):
        line = line.strip()
        lower_line = line.lower()

        if "similarit" in lower_line:
            current_section = "similarities"
        elif "difference" in lower_line:
            current_section = "differences"
        elif "insight" in lower_line or "cross-document" in lower_line:
            current_section = "insights"
        elif line.startswith(("-", "*", "1", "2", "3", "4", "5")) and current_section:
            # Clean the bullet point
            cleaned = line.lstrip("-*0123456789. ")
            if cleaned:
                result[current_section].append(cleaned)

    return result


async def analyze_comparison_node(state: DocumentComparisonState) -> Dict:
    """Analyze similarities and differences using LLM.

    Takes retrieved chunks and graph context, asks LLM to identify:
    - Key similarities between documents
    - Notable differences
    - Cross-document insights

    Args:
        state: Current workflow state with retrieved_chunks and graph_context.

    Returns:
        Dict with similarities, differences, cross_document_insights, and status.
    """
    logger.info(f"Analyzing comparison for query: {state['query'][:50]}...")

    # Format context for LLM
    context = format_comparison_context(state)

    # Build analysis prompt
    prompt = f"""Analyze and compare the following documents based on their content and entity relationships.

{context}

User's comparison query: {state['query']}

Provide a detailed analysis with:
1. **Similarities** (3-5 key points where the documents agree or overlap)
2. **Differences** (3-5 notable points where the documents differ)
3. **Cross-Document Insights** (2-3 connections or insights that emerge from comparing both documents together)

Return your analysis as JSON with the following structure:
```json
{{
    "similarities": ["point 1", "point 2", ...],
    "differences": ["point 1", "point 2", ...],
    "insights": ["insight 1", "insight 2", ...]
}}
```

If documents don't contain enough information to compare, provide what you can and note the limitation."""

    try:
        # Create LLM instance for analysis
        llm = get_llm(temperature=0.3)

        response = await llm.ainvoke([{"role": "user", "content": prompt}])
        analysis = parse_analysis_response(response.content)

        logger.info(
            f"Analysis complete: {len(analysis['similarities'])} similarities, "
            f"{len(analysis['differences'])} differences, "
            f"{len(analysis['insights'])} insights"
        )

        return {
            "similarities": analysis.get("similarities", []),
            "differences": analysis.get("differences", []),
            "cross_document_insights": analysis.get("insights", []),
            "status": "analysis_complete",
        }

    except Exception as e:
        logger.error(f"Failed to analyze comparison: {e}")
        return {
            "similarities": [],
            "differences": [],
            "cross_document_insights": [],
            "status": "analysis_failed",
            "error": str(e),
        }
