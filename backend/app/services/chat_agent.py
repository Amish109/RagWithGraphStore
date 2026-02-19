"""LLM tool-orchestrated chat agent built on LangGraph.

Uses LangGraph's create_react_agent to build a ReAct agent graph:

    START → agent (LLM) → tools → agent → ... → END

The agent streams events via astream_events(), giving us token-level
streaming for the final response AND visibility into tool calls as they happen.

Works with OpenAI, Anthropic, and OpenRouter. Ollama falls back to the
direct pipeline in queries.py.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import AsyncGenerator, List, Optional, Union

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
)

from app.models.document import get_document_by_id
from app.services.agent_tools import create_agent_tools
from app.services.llm_provider import get_llm

from langchain.agents import create_agent

logger = logging.getLogger(__name__)


# --- Event types yielded by the agent ---


@dataclass
class ToolCallEvent:
    """Agent is calling a tool."""

    name: str
    args: dict = field(default_factory=dict)


@dataclass
class TokenEvent:
    """A token from the final streamed response."""

    token: str


@dataclass
class StatusEvent:
    """Processing stage update."""

    stage: str


@dataclass
class DoneEvent:
    """Stream is complete."""

    pass


AgentEvent = Union[ToolCallEvent, TokenEvent, StatusEvent, DoneEvent]


# --- System prompt ---

AGENT_SYSTEM_PROMPT = """You are an intelligent RAG assistant with access to a user's document knowledge base.
You help users explore, understand, and query their uploaded documents.

You have access to these tools:
- search_documents: Semantic + knowledge graph search across documents
- list_user_documents: List all uploaded documents with metadata
- get_document_info: Get metadata for a specific document
- get_document_summary: Get a pre-generated summary of a document
- get_document_entities: Get entities (people, orgs, concepts) from a document
- get_cross_document_entities: Find entities shared across multiple documents
- search_memories: Search personal and shared memory
- get_entity_relationships: Explore how entities relate to each other

GUIDELINES:
1. For factual questions about document content, ALWAYS use search_documents first.
2. For questions about what documents exist or document counts, use list_user_documents.
3. For high-level overviews, use get_document_summary.
4. For entity/relationship exploration, use get_document_entities or get_entity_relationships.
5. For cross-document themes, use get_cross_document_entities.
6. You may call multiple tools in sequence to build a comprehensive answer.
7. When citing information, always reference the source document filename.
8. If tools return no relevant results, say so honestly. Never fabricate information.
9. For simple greetings or general knowledge questions that don't require document data, answer directly without calling tools.

{document_context}"""


# --- Chat history helpers ---

MAX_HISTORY_TOKENS = 4000


def _build_chat_history(raw_history: Optional[List[dict]]) -> List[BaseMessage]:
    """Convert raw chat history from frontend to LangChain messages."""
    if not raw_history:
        return []

    messages = []
    for entry in raw_history:
        role = entry.get("role", "")
        content = entry.get("content", "")
        if not content:
            continue
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))

    return _truncate_history(messages)


def _truncate_history(
    messages: List[BaseMessage],
    max_tokens: int = MAX_HISTORY_TOKENS,
) -> List[BaseMessage]:
    """Keep most recent messages that fit within token budget (~4 chars/token)."""
    max_chars = max_tokens * 4
    total_chars = sum(len(m.content) for m in messages)

    if total_chars <= max_chars:
        return messages

    truncated = []
    chars_used = 0
    for msg in reversed(messages):
        chars_used += len(msg.content)
        if chars_used > max_chars:
            break
        truncated.insert(0, msg)
    return truncated


def _build_document_context(
    document_ids: Optional[List[str]],
    user_id: str,
) -> str:
    """Build document context section for the system prompt."""
    if not document_ids:
        return ""

    parts = ["You are currently chatting about specific document(s):"]
    for doc_id in document_ids:
        doc = get_document_by_id(doc_id, user_id)
        if doc:
            fname = doc.get("filename", "Unknown")
            parts.append(f"- Document: {fname} (ID: {doc_id})")
        else:
            parts.append(f"- Document ID: {doc_id}")

    parts.append(
        "\nWhen searching, prioritize these documents. "
        "Pass their document IDs to the search_documents tool's document_ids parameter."
    )
    return "\n".join(parts)


# --- LangGraph agent ---


def _create_agent_graph(
    user_id: str,
    document_ids: Optional[List[str]] = None,
    include_shared_memory: bool = True,
):
    """Create a LangGraph ReAct agent graph with tools bound.

    Returns a compiled StateGraph that handles the full
    agent → tool → agent → ... → response cycle.
    """
    tools = create_agent_tools(
        user_id=user_id,
        document_ids=document_ids,
        include_shared_memory=include_shared_memory,
    )

    llm = get_llm(temperature=0, streaming=True)

    document_context = _build_document_context(document_ids, user_id)
    system_prompt = AGENT_SYSTEM_PROMPT.format(document_context=document_context)

    graph = create_agent(
        model=llm,
        tools=tools,
        system_prompt=system_prompt,
    )

    return graph


async def run_agent(
    query: str,
    user_id: str,
    document_ids: Optional[List[str]] = None,
    chat_history: Optional[List[dict]] = None,
    include_shared_memory: bool = True,
) -> AsyncGenerator[AgentEvent, None]:
    """Run the LangGraph agent, yielding events for SSE streaming.

    Uses astream_events() to get granular streaming:
    - on_chat_model_stream → TokenEvent (final response tokens)
    - on_tool_start → ToolCallEvent (tool being called)

    Args:
        query: User's question.
        user_id: Current user ID (for multi-tenant tool access).
        document_ids: Optional document IDs for scoped chat.
        chat_history: Previous conversation messages [{role, content}].
        include_shared_memory: Whether to include shared memories.

    Yields:
        AgentEvent instances (ToolCallEvent, TokenEvent, DoneEvent).
    """
    graph = _create_agent_graph(
        user_id=user_id,
        document_ids=document_ids,
        include_shared_memory=include_shared_memory,
    )

    # Build input messages
    input_messages: List[BaseMessage] = []
    history = _build_chat_history(chat_history)
    input_messages.extend(history)
    input_messages.append(HumanMessage(content=query))

    # Track whether we've seen tool calls to know when
    # the final response tokens are streaming
    seen_tool_calls = False
    is_final_response = False
    t_start = time.perf_counter()
    t_last = t_start

    try:
        async for event in graph.astream_events(
            {"messages": input_messages},
            version="v2",
        ):
            kind = event["event"]

            # Tool start → emit ToolCallEvent
            if kind == "on_tool_start":
                tool_name = event.get("name", "")
                tool_input = event.get("data", {}).get("input", {})
                if tool_name:
                    now = time.perf_counter()
                    logger.info(f"[{now - t_start:.1f}s] Agent calling tool: {tool_name} (+{now - t_last:.1f}s)")
                    t_last = now
                    seen_tool_calls = True
                    is_final_response = False
                    yield ToolCallEvent(name=tool_name, args=tool_input)

            elif kind == "on_tool_end":
                now = time.perf_counter()
                tool_name = event.get("name", "")
                tool_output = event.get("data", {}).get("output", "")
                logger.info(f"[{now - t_start:.1f}s] Tool finished: {tool_name} (+{now - t_last:.1f}s) | output={str(tool_output)[:300]}")
                t_last = now

            # Chat model stream → emit TokenEvent for final response
            elif kind == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                if chunk is None:
                    continue

                content = getattr(chunk, "content", "")
                tool_calls = getattr(chunk, "tool_calls", None)

                # If the chunk has tool_calls, this is a tool-calling turn, not final
                if tool_calls:
                    continue

                # If the model is producing content AND we've seen tool calls before,
                # this is the final response after tool execution
                if content:
                    if seen_tool_calls and not is_final_response:
                        is_final_response = True
                        now = time.perf_counter()
                        logger.info(f"[{now - t_start:.1f}s] First response token (+{now - t_last:.1f}s)")
                        t_last = now
                        yield StatusEvent(stage="generating")

                    # Only stream tokens from the last LLM turn (the final answer)
                    # For the first turn without tools, stream immediately
                    # For turns after tools, stream once we enter final response mode
                    if is_final_response or not seen_tool_calls:
                        yield TokenEvent(token=content)

        now = time.perf_counter()
        logger.info(f"[{now - t_start:.1f}s] Agent complete (total)")
        yield DoneEvent()

    except Exception as e:
        logger.exception(f"Agent execution failed: {e}")
        yield TokenEvent(
            token=f"I encountered an error while processing your request: {e}"
        )
        yield DoneEvent()
