"""LLM-based entity and relationship extraction for GraphRAG.

Provides:
- extract_entities_from_chunk(): Extract entities and relationships from chunk text
- extract_entities_batch(): Batch extraction for multiple chunks
- normalize_entity_name(): Normalize entity names for deduplication

Entity types: PERSON, ORGANIZATION, LOCATION, CONCEPT, EVENT, TECHNOLOGY, PRODUCT
Relationship types: WORKS_FOR, LOCATED_IN, PART_OF, RELATED_TO, CREATED_BY, USES, PRODUCES
"""

import json
import logging
import re
import uuid
from typing import Dict, List

from langchain_core.prompts import ChatPromptTemplate

from app.services.llm_provider import get_llm

logger = logging.getLogger(__name__)

ENTITY_EXTRACTION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert entity and relationship extractor.
Analyze the text and extract all notable entities and their relationships.

Return ONLY a valid JSON object with this exact structure:
{{
  "entities": [
    {{"name": "Entity Name", "type": "ENTITY_TYPE"}}
  ],
  "relationships": [
    {{"source": "Entity1", "target": "Entity2", "type": "RELATIONSHIP_TYPE", "description": "brief description"}}
  ]
}}

Entity types: PERSON, ORGANIZATION, LOCATION, CONCEPT, EVENT, TECHNOLOGY, PRODUCT
Relationship types: WORKS_FOR, LOCATED_IN, PART_OF, RELATED_TO, CREATED_BY, USES, PRODUCES

Rules:
- Extract only clearly mentioned entities, do not infer
- Use the most specific entity type that applies
- Relationships must reference entities in the entities list
- If no entities found, return {{"entities": [], "relationships": []}}
- Return ONLY valid JSON, no other text"""),
    ("user", "{text}")
])

# Common suffixes to strip for normalization
_SUFFIXES = re.compile(
    r"\s*\b(inc\.?|corp\.?|ltd\.?|llc\.?|co\.?|plc\.?|gmbh|s\.a\.?|n\.v\.?)\s*$",
    re.IGNORECASE,
)


def normalize_entity_name(name: str) -> str:
    """Normalize entity name for deduplication.

    Lowercases, strips whitespace/punctuation, removes corporate suffixes.
    """
    normalized = name.strip().lower()
    normalized = _SUFFIXES.sub("", normalized)
    normalized = normalized.rstrip(".,;:!?")
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _parse_json_response(text: str) -> Dict:
    """Parse JSON from LLM response, handling markdown code blocks."""
    text = text.strip()

    # Strip markdown code block if present
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first line (```json or ```) and last line (```)
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()

    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find JSON object in the text
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    return {"entities": [], "relationships": []}


async def extract_entities_from_chunk(chunk_text: str) -> Dict:
    """Extract entities and relationships from a single chunk.

    Args:
        chunk_text: The text content of the chunk.

    Returns:
        Dict with 'entities' (list of {name, type}) and
        'relationships' (list of {source, target, type, description}).
    """
    llm = get_llm(temperature=0)

    try:
        messages = ENTITY_EXTRACTION_PROMPT.format_messages(text=chunk_text)
        response = await llm.ainvoke(messages)
        result = _parse_json_response(response.content)

        # Validate and normalize entities
        entities = []
        seen = set()
        for entity in result.get("entities", []):
            name = entity.get("name", "").strip()
            etype = entity.get("type", "CONCEPT").strip().upper()
            if not name:
                continue
            normalized = normalize_entity_name(name)
            key = (normalized, etype)
            if key not in seen:
                seen.add(key)
                entities.append({
                    "id": str(uuid.uuid4()),
                    "name": name,
                    "type": etype,
                    "normalized_name": normalized,
                })

        # Validate relationships — only keep those referencing extracted entities
        entity_names_normalized = {e["normalized_name"] for e in entities}
        relationships = []
        for rel in result.get("relationships", []):
            source = rel.get("source", "").strip()
            target = rel.get("target", "").strip()
            rtype = rel.get("type", "RELATED_TO").strip().upper()
            desc = rel.get("description", "")

            source_norm = normalize_entity_name(source)
            target_norm = normalize_entity_name(target)

            if source_norm in entity_names_normalized and target_norm in entity_names_normalized:
                relationships.append({
                    "source": source,
                    "target": target,
                    "source_normalized": source_norm,
                    "target_normalized": target_norm,
                    "type": rtype,
                    "description": desc,
                })

        return {"entities": entities, "relationships": relationships}

    except Exception as e:
        logger.warning(f"Entity extraction failed for chunk: {e}")
        return {"entities": [], "relationships": []}


async def extract_entities_batch(chunks: List[Dict]) -> List[Dict]:
    """Extract entities from multiple chunks.

    Processes each chunk independently. If extraction fails for a chunk,
    returns empty result for that chunk and continues.

    Args:
        chunks: List of chunk dicts (must have 'text' key).

    Returns:
        List of extraction results aligned with input chunks.
    """
    results = []
    for i, chunk in enumerate(chunks):
        text = chunk.get("text", "")
        if not text.strip():
            results.append({"entities": [], "relationships": []})
            continue

        result = await extract_entities_from_chunk(text)
        entity_count = len(result.get("entities", []))
        rel_count = len(result.get("relationships", []))
        if entity_count > 0:
            logger.debug(
                f"Chunk {i}: extracted {entity_count} entities, {rel_count} relationships"
            )
        results.append(result)

    total_entities = sum(len(r.get("entities", [])) for r in results)
    total_rels = sum(len(r.get("relationships", [])) for r in results)
    logger.info(
        f"Batch extraction complete: {total_entities} entities, "
        f"{total_rels} relationships from {len(chunks)} chunks"
    )
    return results
