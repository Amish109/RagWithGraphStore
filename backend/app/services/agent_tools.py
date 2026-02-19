"""Agent tool definitions for the LLM tool-orchestrated chat system.

Each tool is a thin wrapper around existing services. Tools are created via
factory functions that capture user_id in a closure, ensuring multi-tenant
safety — the LLM never sees or controls user_id.

Usage:
    tools = create_agent_tools(user_id="abc-123", document_ids=["doc-1"])
    llm_with_tools = get_llm().bind_tools(tools)
"""

import json
import logging
from typing import List, Optional

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


def create_search_documents_tool(user_id: str):
    """Create a document search tool with user_id bound."""

    @tool
    async def search_documents(
        query: str,
        max_results: int = 5,
        document_ids: Optional[List[str]] = None,
    ) -> str:
        """Search across the user's uploaded documents using semantic vector search
        combined with knowledge graph entity matching.

        Use this tool to find specific information, answer factual questions about
        document content, or retrieve relevant passages. Returns the most relevant
        text chunks with source filenames and relevance scores.

        Args:
            query: The search query describing what information to find.
            max_results: Maximum number of results to return (default 5).
            document_ids: Optional list of specific document IDs to search within.
        """
        from app.services.retrieval_service import (
            retrieve_for_documents,
            retrieve_relevant_context,
        )

        try:
            if document_ids:
                result = await retrieve_for_documents(
                    query=query,
                    user_id=user_id,
                    document_ids=document_ids,
                    max_results=max_results,
                )
            else:
                result = await retrieve_relevant_context(
                    query=query,
                    user_id=user_id,
                    max_results=max_results,
                )

            chunks = result.get("chunks", [])
            formatted = [
                {
                    "text": c["text"][:500],
                    "filename": c.get("filename", "Unknown"),
                    "document_id": c.get("document_id", ""),
                    "score": round(c.get("score", 0), 3),
                }
                for c in chunks
            ]
            return json.dumps(formatted, indent=2)
        except Exception as e:
            logger.warning(f"search_documents tool failed: {e}")
            return json.dumps({"error": str(e)})

    return search_documents


def create_list_user_documents_tool(user_id: str):
    """Create a tool to list all user documents."""

    @tool
    async def list_user_documents() -> str:
        """List all documents the user has uploaded.

        Returns document names, types, sizes, and chunk counts.
        Use this when the user asks about their documents, how many they have,
        or wants an overview of their document collection.
        """
        from app.models.document import get_user_documents

        try:
            documents = get_user_documents(user_id)
            formatted = [
                {
                    "id": d.get("id", ""),
                    "filename": d.get("filename", "Unknown"),
                    "file_type": d.get("file_type"),
                    "file_size": d.get("file_size"),
                    "chunk_count": d.get("chunk_count"),
                    "created_at": d.get("created_at"),
                }
                for d in documents
            ]
            return json.dumps(
                {"documents": formatted, "total_count": len(formatted)},
                indent=2,
            )
        except Exception as e:
            logger.warning(f"list_user_documents tool failed: {e}")
            return json.dumps({"error": str(e)})

    return list_user_documents


def create_get_document_info_tool(user_id: str):
    """Create a tool to get metadata for a specific document."""

    @tool
    async def get_document_info(document_id: str) -> str:
        """Get detailed metadata for a specific document.

        Returns filename, file type, size, chunk count, and creation date.
        Use this when the user asks about a specific document's properties.

        Args:
            document_id: The UUID of the document to look up.
        """
        from app.models.document import get_document_by_id

        try:
            doc = get_document_by_id(document_id, user_id)
            if not doc:
                return json.dumps({"error": "Document not found or access denied"})
            return json.dumps(doc, indent=2, default=str)
        except Exception as e:
            logger.warning(f"get_document_info tool failed: {e}")
            return json.dumps({"error": str(e)})

    return get_document_info


def create_get_document_summary_tool(user_id: str):
    """Create a tool to get a pre-generated document summary."""

    @tool
    async def get_document_summary(
        document_id: str,
        summary_type: str = "brief",
    ) -> str:
        """Get a pre-generated summary of a document.

        Available summary types: brief, detailed, executive, bullet.
        Use this when the user asks for a summary or overview of a document.

        Args:
            document_id: The UUID of the document.
            summary_type: Type of summary — one of "brief", "detailed", "executive", "bullet".
        """
        from app.services.summary_storage import get_summary

        try:
            summary = get_summary(document_id, summary_type)
            if summary:
                return json.dumps({
                    "document_id": document_id,
                    "summary_type": summary_type,
                    "summary": summary,
                })
            return json.dumps({
                "document_id": document_id,
                "summary_type": summary_type,
                "summary": None,
                "message": "No pre-generated summary available for this document.",
            })
        except Exception as e:
            logger.warning(f"get_document_summary tool failed: {e}")
            return json.dumps({"error": str(e)})

    return get_document_summary


def create_get_document_entities_tool(user_id: str):
    """Create a tool to get entities extracted from a document."""

    @tool
    async def get_document_entities(
        document_id: str,
        limit: int = 20,
    ) -> str:
        """Get entities (people, organizations, concepts, etc.) extracted from a document.

        Returns a list of named entities found in the document along with their types.
        Use this when the user asks about entities, people, organizations, or concepts
        mentioned in a specific document.

        Args:
            document_id: The UUID of the document.
            limit: Maximum number of entities to return (default 20).
        """
        from app.services.graphrag_service import get_document_entities as _get_entities

        try:
            entities = await _get_entities(document_id, user_id, limit)
            return json.dumps(
                {"document_id": document_id, "entities": entities, "count": len(entities)},
                indent=2,
            )
        except Exception as e:
            logger.warning(f"get_document_entities tool failed: {e}")
            return json.dumps({"error": str(e)})

    return get_document_entities


def create_get_cross_document_entities_tool(user_id: str):
    """Create a tool to find entities shared across multiple documents."""

    @tool
    async def get_cross_document_entities(limit: int = 20) -> str:
        """Find entities that appear across multiple documents (bridge entities).

        These are concepts, people, or organizations that connect different documents.
        Use this when the user asks about themes across documents, shared concepts,
        or wants to understand how their documents relate to each other.

        Args:
            limit: Maximum number of entities to return (default 20).
        """
        from app.services.graphrag_service import get_entity_co_occurrences

        try:
            co_occurrences = await get_entity_co_occurrences(
                user_id=user_id, limit=limit,
            )
            return json.dumps(
                {"entities": co_occurrences, "count": len(co_occurrences)},
                indent=2,
            )
        except Exception as e:
            logger.warning(f"get_cross_document_entities tool failed: {e}")
            return json.dumps({"error": str(e)})

    return get_cross_document_entities


def create_search_memories_tool(user_id: str, include_shared: bool = True):
    """Create a tool to search the user's memory store."""

    @tool
    async def search_memories(query: str, limit: int = 5) -> str:
        """Search the user's personal and shared memory for relevant information.

        Memories include previously stored facts, preferences, and shared knowledge.
        Use this when the user asks about something they've told you before,
        or when looking for shared organizational knowledge.

        Args:
            query: The search query.
            limit: Maximum number of memories to return (default 5).
        """
        from app.services.memory_service import search_with_shared

        try:
            memories = await search_with_shared(
                user_id=user_id,
                query=query,
                limit=limit,
                include_shared=include_shared,
            )
            formatted = [
                {
                    "memory": m.get("memory", ""),
                    "score": round(m.get("score", 0), 3),
                    "is_shared": m.get("is_shared", False),
                }
                for m in memories
                if m.get("memory")
            ]
            return json.dumps(
                {"memories": formatted, "count": len(formatted)},
                indent=2,
            )
        except Exception as e:
            logger.warning(f"search_memories tool failed: {e}")
            return json.dumps({"error": str(e)})

    return search_memories


def create_get_entity_relationships_tool(user_id: str):
    """Create a tool to explore entity relationships in the knowledge graph."""

    @tool
    async def get_entity_relationships(
        entity_name: str,
        limit: int = 20,
    ) -> str:
        """Get relationships for a specific entity in the knowledge graph.

        Shows how an entity connects to other entities (e.g., a person works for
        an organization, a concept relates to another concept).
        Use this when the user asks about relationships, connections, or how
        entities are linked.

        Args:
            entity_name: The name of the entity to look up.
            limit: Maximum number of relationships to return (default 20).
        """
        from app.services.graphrag_service import get_entity_relationships as _get_rels

        try:
            relationships = await _get_rels(entity_name, user_id, limit)
            return json.dumps(
                {
                    "entity": entity_name,
                    "relationships": relationships,
                    "count": len(relationships),
                },
                indent=2,
            )
        except Exception as e:
            logger.warning(f"get_entity_relationships tool failed: {e}")
            return json.dumps({"error": str(e)})

    return get_entity_relationships


def create_agent_tools(
    user_id: str,
    document_ids: Optional[List[str]] = None,
    include_shared_memory: bool = True,
) -> list:
    """Create all agent tools with user_id bound via closure.

    Args:
        user_id: ID of the current user (captured in closures for multi-tenant safety).
        document_ids: Optional document IDs for document-scoped chat context.
        include_shared_memory: Whether to include shared memories in search.

    Returns:
        List of LangChain tool instances ready for bind_tools().
    """
    tools = [
        create_search_documents_tool(user_id),
        create_list_user_documents_tool(user_id),
        create_get_document_info_tool(user_id),
        create_get_document_summary_tool(user_id),
        create_get_document_entities_tool(user_id),
        create_get_cross_document_entities_tool(user_id),
        create_search_memories_tool(user_id, include_shared=include_shared_memory),
        create_get_entity_relationships_tool(user_id),
    ]
    return tools
