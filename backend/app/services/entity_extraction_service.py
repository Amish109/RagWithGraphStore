"""LLM-based entity and relationship extraction for GraphRAG.

Uses LangChain's LLMGraphTransformer instead of manual prompts — handles
structured extraction, JSON parsing, and schema enforcement automatically.

Provides:
- extract_entities_from_chunk(): Extract entities and relationships from chunk text
- extract_entities_batch(): Batch extraction for multiple chunks
- normalize_entity_name(): Normalize entity names for deduplication

Entity types: Person, Organization, Location, Concept, Event, Technology, Product
Relationship types: WORKS_FOR, LOCATED_IN, PART_OF, RELATED_TO, CREATED_BY, USES, PRODUCES
"""

import asyncio
import logging
import re
import uuid
from typing import Dict, List, Optional

from langchain_core.documents import Document
from langchain_experimental.graph_transformers import LLMGraphTransformer

from app.services.llm_provider import get_llm

logger = logging.getLogger(__name__)

# Allowed entity and relationship types — same schema as before
ALLOWED_NODES = ["Person", "Organization", "Location", "Concept", "Event", "Technology", "Product"]
ALLOWED_RELATIONSHIPS = ["WORKS_FOR", "LOCATED_IN", "PART_OF", "RELATED_TO", "CREATED_BY", "USES", "PRODUCES"]

# Common suffixes to strip for normalization
_SUFFIXES = re.compile(
    r"\s*\b(inc\.?|corp\.?|ltd\.?|llc\.?|co\.?|plc\.?|gmbh|s\.a\.?|n\.v\.?)\s*$",
    re.IGNORECASE,
)


def _create_transformer() -> LLMGraphTransformer:
    """Create a configured LLMGraphTransformer instance.

    Uses GRAPHRAG_LLM_PROVIDER / GRAPHRAG_LLM_MODEL if set, otherwise
    falls back to the default LLM_PROVIDER. This allows using a faster
    provider (e.g. OpenAI) for entity extraction while keeping Ollama
    for everything else.
    """
    from app.config import settings

    llm = get_llm(
        temperature=0,
        provider=settings.GRAPHRAG_LLM_PROVIDER,
        model=settings.GRAPHRAG_LLM_MODEL,
    )
    return LLMGraphTransformer(
        llm=llm,
        allowed_nodes=ALLOWED_NODES,
        allowed_relationships=ALLOWED_RELATIONSHIPS,
        node_properties=["description"],
        relationship_properties=["description"],
        strict_mode=True,
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


def _graph_document_to_dict(graph_doc) -> Dict:
    """Convert LangChain GraphDocument to our internal format.

    Maps GraphDocument nodes/relationships to the dict format expected
    by indexing_service.store_entities_in_neo4j().
    """
    entities = []
    seen = set()

    for node in graph_doc.nodes:
        name = node.id
        etype = node.type.upper()
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

    # Build lookup for relationship validation
    entity_names_normalized = {e["normalized_name"] for e in entities}

    relationships = []
    for rel in graph_doc.relationships:
        source = rel.source.id
        target = rel.target.id
        rtype = rel.type.upper()
        desc = rel.properties.get("description", "") if rel.properties else ""

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


async def extract_entities_from_chunk(
    chunk_text: str,
    transformer: Optional[LLMGraphTransformer] = None,
) -> Dict:
    """Extract entities and relationships from a single chunk.

    Args:
        chunk_text: The text content of the chunk.
        transformer: Pre-built LLMGraphTransformer to reuse. If None, creates
            a new one (convenience for single-chunk calls outside a batch).

    Returns:
        Dict with 'entities' (list of {name, type, id, normalized_name}) and
        'relationships' (list of {source, target, type, description}).
    """
    try:
        if transformer is None:
            transformer = _create_transformer()
        doc = Document(page_content=chunk_text)
        # LLMGraphTransformer.aconvert_to_graph_documents is safe to call
        # concurrently — each call builds its own prompt/response chain,
        # so sharing one transformer across concurrent tasks is fine.
        graph_docs = await transformer.aconvert_to_graph_documents([doc])

        if not graph_docs:
            return {"entities": [], "relationships": []}

        return _graph_document_to_dict(graph_docs[0])

    except Exception as e:
        logger.warning(f"Entity extraction failed for chunk: {e}")
        return {"entities": [], "relationships": []}


async def extract_entities_batch(
    chunks: List[Dict],
    document_id: Optional[str] = None,
    concurrency: Optional[int] = None,
    progress_callback: Optional[callable] = None,
) -> List[Dict]:
    """Extract entities from multiple chunks with concurrency and progress tracking.

    Args:
        chunks: List of chunk dicts (must have 'text' key).
        document_id: Optional document ID for progress reporting.
        concurrency: Max concurrent LLM calls. If None, uses settings.GRAPHRAG_CONCURRENCY.
        progress_callback: Optional callback(completed, total, entities_so_far) for progress.

    Returns:
        List of extraction results aligned with input chunks.
    """
    from app.config import settings

    if concurrency is None:
        concurrency = settings.GRAPHRAG_CONCURRENCY

    total = len(chunks)
    results: List[Optional[Dict]] = [None] * total
    completed_count = 0
    semaphore = asyncio.Semaphore(concurrency)

    transformer = _create_transformer()

    async def process_chunk(index: int, chunk: Dict) -> None:
        nonlocal completed_count
        text = chunk.get("text", "")
        if not text.strip():
            results[index] = {"entities": [], "relationships": []}
            completed_count += 1
            return

        async with semaphore:
            result = await extract_entities_from_chunk(text, transformer=transformer)
            results[index] = result
            completed_count += 1

            entity_count = len(result.get("entities", []))
            rel_count = len(result.get("relationships", []))
            if entity_count > 0:
                logger.info(
                    f"Chunk {index + 1}/{total}: {entity_count} entities, {rel_count} relationships"
                )

            if progress_callback:
                entities_so_far = sum(len(r.get("entities", [])) for r in results if r)
                progress_callback(completed_count, total, entities_so_far)

    tasks = [process_chunk(i, chunk) for i, chunk in enumerate(chunks)]
    await asyncio.gather(*tasks)

    total_entities = sum(len(r.get("entities", [])) for r in results if r)
    total_rels = sum(len(r.get("relationships", [])) for r in results if r)
    logger.info(
        f"Batch extraction complete: {total_entities} entities, "
        f"{total_rels} relationships from {total} chunks"
    )
    return [r or {"entities": [], "relationships": []} for r in results]





"""



"""