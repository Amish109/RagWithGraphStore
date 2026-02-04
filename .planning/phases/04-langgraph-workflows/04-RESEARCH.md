# Phase 4: LangGraph & Advanced Workflows - Research

**Researched:** 2026-02-04
**Domain:** LangGraph workflow orchestration, GraphRAG multi-hop reasoning, memory summarization
**Confidence:** MEDIUM-HIGH

## Summary

Phase 4 introduces LangGraph for orchestrating complex multi-step workflows, specifically document comparison using GraphRAG multi-hop reasoning and automatic memory summarization. The research reveals that LangGraph 1.0 (GA) provides robust state management with checkpointing, the Neo4j GraphRAG Python package offers production-ready retrievers for multi-hop traversal, and Mem0's built-in memory consolidation combined with LangChain's ConversationSummaryBufferMemory patterns can prevent context overflow.

The key architectural insight is that LangGraph workflows should be designed with explicit state schemas (TypedDict), nodes that perform single tasks, and conditional routing based on computed values. For document comparison, the workflow retrieves chunks from multiple documents via vector search, expands context via Neo4j graph traversal, and synthesizes comparative analysis through an LLM generation step.

**Primary recommendation:** Use LangGraph with PostgresSaver checkpointing for durable workflow state, Neo4j's VectorCypherRetriever for multi-hop graph traversal, and implement memory summarization using Mem0's automatic consolidation with token-limit-triggered summarization as a fallback.

## Standard Stack

The established libraries/tools for this domain:

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| **langgraph** | >=1.0 | Workflow orchestration | LangGraph 1.0 GA provides durable execution, checkpointing, state persistence across interruptions. Industry standard for complex agentic workflows in 2026 |
| **langgraph-checkpoint-postgres** | 3.0.4 | Production checkpointing | Official PostgresSaver for production deployments. LangSmith uses this internally |
| **neo4j-graphrag-python** | latest | GraphRAG retrievers | Official Neo4j package with VectorCypherRetriever and HybridRetriever for multi-hop reasoning |
| **langchain** | >=1.0 | LLM orchestration base | LangGraph is built on LangChain; provides memory classes and LLM integrations |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **psycopg** | 3.x | PostgreSQL driver | Required by langgraph-checkpoint-postgres for async checkpoint storage |
| **langchain-openai** | >=1.1.7 | OpenAI LLM integration | For LLM calls within LangGraph nodes |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| PostgresSaver | SqliteSaver | SQLite is simpler but not production-grade for concurrent multi-user workflows |
| PostgresSaver | InMemorySaver | InMemory loses state on restart; only for development/testing |
| VectorCypherRetriever | Custom Cypher queries | Custom gives more control but VectorCypherRetriever handles common patterns efficiently |

**Installation:**
```bash
pip install langgraph>=1.0 langgraph-checkpoint-postgres psycopg[binary]
pip install neo4j-graphrag-python
```

## Architecture Patterns

### Recommended Project Structure
```
backend/app/
├── workflows/                 # LangGraph workflow definitions
│   ├── __init__.py
│   ├── document_comparison.py # Document comparison workflow
│   ├── state.py              # TypedDict state schemas
│   └── nodes/                # Workflow node functions
│       ├── retrieval.py      # Vector + graph retrieval nodes
│       ├── comparison.py     # Document comparison analysis nodes
│       └── generation.py     # LLM generation nodes
├── services/
│   ├── memory_summarizer.py  # Memory summarization service
│   └── graphrag_service.py   # GraphRAG multi-hop retrieval
└── db/
    └── checkpoint_store.py   # LangGraph checkpointer configuration
```

### Pattern 1: TypedDict State Schema for Document Comparison

**What:** Define explicit state schema using TypedDict with reducer annotations for workflow state.

**When to use:** All LangGraph workflows. Required for document comparison workflow.

**Example:**
```python
# Source: LangGraph official documentation
from typing import TypedDict, Annotated, List
from langgraph.graph.message import add_messages

class DocumentComparisonState(TypedDict):
    """State for document comparison workflow."""
    # User query
    query: str
    user_id: str

    # Documents to compare (document IDs)
    document_ids: List[str]

    # Retrieved chunks per document
    # dict[doc_id, list[chunk_dict]]
    retrieved_chunks: dict

    # Graph-expanded context per document
    graph_context: dict

    # Comparison analysis results
    similarities: List[str]
    differences: List[str]
    cross_document_insights: List[str]

    # Final generated response
    response: str

    # Citations for attribution
    citations: List[dict]

    # Workflow status
    status: str
    error: str | None
```

### Pattern 2: LangGraph Workflow with Checkpointing

**What:** Compile LangGraph with PostgresSaver for durable state persistence across requests.

**When to use:** Any workflow that needs to persist state across multiple API requests.

**Example:**
```python
# Source: LangGraph persistence documentation
from langgraph.graph import StateGraph
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

async def create_document_comparison_workflow():
    # Define graph
    workflow = StateGraph(DocumentComparisonState)

    # Add nodes
    workflow.add_node("retrieve_documents", retrieve_documents_node)
    workflow.add_node("expand_graph_context", expand_graph_context_node)
    workflow.add_node("analyze_comparison", analyze_comparison_node)
    workflow.add_node("generate_response", generate_response_node)

    # Add edges
    workflow.set_entry_point("retrieve_documents")
    workflow.add_edge("retrieve_documents", "expand_graph_context")
    workflow.add_edge("expand_graph_context", "analyze_comparison")
    workflow.add_edge("analyze_comparison", "generate_response")
    workflow.set_finish_point("generate_response")

    # Compile with checkpointer for persistence
    async with AsyncPostgresSaver.from_conn_string(DB_URI) as checkpointer:
        await checkpointer.setup()  # CRITICAL: Call on first use
        app = workflow.compile(checkpointer=checkpointer)
        return app
```

### Pattern 3: Neo4j VectorCypherRetriever for Multi-Hop Reasoning

**What:** Use VectorCypherRetriever to combine vector similarity search with graph traversal in a single operation.

**When to use:** When retrieving document chunks and need to expand context through entity relationships.

**Example:**
```python
# Source: Neo4j GraphRAG Python documentation
from neo4j_graphrag.retrievers import VectorCypherRetriever
from neo4j_graphrag.embeddings import OpenAIEmbeddings

# Multi-hop retrieval query: get chunks and their related entities
retrieval_query = """
MATCH (chunk:Chunk)-[:PART_OF]->(doc:Document)
WHERE doc.id IN $document_ids
OPTIONAL MATCH (entity:Entity)-[:APPEARS_IN]->(chunk)
OPTIONAL MATCH (entity)-[r:RELATES_TO]-(related:Entity)
RETURN chunk.text AS text,
       chunk.id AS chunk_id,
       doc.id AS document_id,
       doc.filename AS filename,
       collect(DISTINCT {
           entity: entity.name,
           type: entity.type,
           related: related.name,
           relation: type(r)
       }) AS entities
"""

retriever = VectorCypherRetriever(
    driver=neo4j_driver,
    index_name="chunk_embeddings",
    retrieval_query=retrieval_query,
    embedder=OpenAIEmbeddings(model="text-embedding-3-small")
)

# Search with document filtering
results = retriever.search(
    query_text="Compare the main themes",
    top_k=10,
    filters={"document_ids": ["doc1", "doc2"]}
)
```

### Pattern 4: Memory Summarization to Prevent Context Overflow

**What:** Implement automatic memory summarization when conversation context exceeds token limits.

**When to use:** When conversation memory grows large; triggers at configurable token threshold.

**Example:**
```python
# Source: Mem0 documentation + LangChain ConversationSummaryBufferMemory pattern
from mem0 import Memory
from langchain_openai import ChatOpenAI

class MemorySummarizer:
    """Summarizes memory when context exceeds threshold."""

    def __init__(
        self,
        mem0_client: Memory,
        llm: ChatOpenAI,
        max_token_limit: int = 4000,
        summarization_threshold: float = 0.75  # Trigger at 75% of limit
    ):
        self.mem0 = mem0_client
        self.llm = llm
        self.max_token_limit = max_token_limit
        self.threshold = int(max_token_limit * summarization_threshold)

    async def get_memory_with_summarization(
        self,
        user_id: str,
        query: str
    ) -> dict:
        """Retrieve memory, summarizing if needed."""
        # Get all memories for user
        memories = self.mem0.search(query, user_id=user_id, limit=50)

        # Estimate token count (rough: 4 chars = 1 token)
        total_tokens = sum(len(m["memory"]) // 4 for m in memories)

        if total_tokens > self.threshold:
            # Trigger summarization
            summary = await self._summarize_memories(memories)

            # Store summary as consolidated memory
            self.mem0.add(
                f"[Consolidated Memory Summary]: {summary}",
                user_id=user_id,
                metadata={"type": "summary", "consolidated_at": datetime.now().isoformat()}
            )

            return {"summary": summary, "was_summarized": True}

        return {"memories": memories, "was_summarized": False}

    async def _summarize_memories(self, memories: list) -> str:
        """Use LLM to create concise summary of memories."""
        memory_text = "\n".join([m["memory"] for m in memories])

        response = await self.llm.ainvoke([
            {"role": "system", "content": "Summarize the following user memories into key facts and preferences. Be concise but preserve critical information."},
            {"role": "user", "content": memory_text}
        ])

        return response.content
```

### Pattern 5: Document Comparison Workflow Node Design

**What:** Design workflow nodes following LangGraph best practices: single responsibility, clear inputs/outputs.

**When to use:** Building the document comparison workflow.

**Example:**
```python
# Source: LangGraph "Thinking in LangGraph" documentation
from typing import Literal
from langgraph.types import Command

async def retrieve_documents_node(state: DocumentComparisonState) -> dict:
    """Retrieve chunks from all specified documents."""
    retrieved = {}

    for doc_id in state["document_ids"]:
        chunks = await retriever.search(
            query_text=state["query"],
            top_k=5,
            filters={"document_id": doc_id}
        )
        retrieved[doc_id] = chunks

    return {"retrieved_chunks": retrieved, "status": "chunks_retrieved"}

async def expand_graph_context_node(state: DocumentComparisonState) -> dict:
    """Expand context via Neo4j graph traversal (multi-hop reasoning)."""
    graph_context = {}

    for doc_id, chunks in state["retrieved_chunks"].items():
        # Extract entity IDs from chunks
        entity_ids = [eid for c in chunks for eid in c.get("entity_ids", [])]

        # Multi-hop graph expansion
        with neo4j_driver.session() as session:
            result = session.run("""
                MATCH (e:Entity)-[r1]-(n1)-[r2]-(n2)
                WHERE e.id IN $entity_ids
                RETURN e.name AS entity, type(r1) AS rel1,
                       n1.name AS hop1, type(r2) AS rel2, n2.name AS hop2
                LIMIT 50
            """, entity_ids=entity_ids)

            graph_context[doc_id] = [dict(record) for record in result]

    return {"graph_context": graph_context, "status": "graph_expanded"}

async def analyze_comparison_node(state: DocumentComparisonState) -> dict:
    """Analyze similarities and differences between documents."""
    prompt = f"""
    Compare the following documents based on their content and relationships:

    {format_documents_for_comparison(state)}

    Identify:
    1. Key similarities between documents
    2. Notable differences
    3. Cross-document insights (connections that span multiple documents)
    """

    response = await llm.ainvoke([{"role": "user", "content": prompt}])
    analysis = parse_comparison_response(response.content)

    return {
        "similarities": analysis["similarities"],
        "differences": analysis["differences"],
        "cross_document_insights": analysis["insights"],
        "status": "analysis_complete"
    }
```

### Anti-Patterns to Avoid

- **Storing formatted prompts in state:** Store raw data; format in nodes when needed. This enables different nodes to use same data differently.
- **Large monolithic nodes:** Break nodes into smaller units for better checkpointing granularity. Each node boundary is a checkpoint opportunity.
- **Not calling checkpointer.setup():** CRITICAL: PostgresSaver requires `.setup()` on first use to create database tables.
- **Missing autocommit=True:** When creating manual Postgres connections, must include `autocommit=True` and `row_factory=dict_row`.
- **Infinite loops without exit conditions:** Always include retry_count or max_iterations in state to prevent runaway workflows.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Workflow state persistence | Custom database schema | LangGraph PostgresSaver | Handles serialization, threading, fault recovery automatically |
| Multi-hop graph traversal | Custom Neo4j queries for each case | VectorCypherRetriever | Combines vector search + graph traversal in optimized pattern |
| Memory token counting | Custom tokenizer | tiktoken or rough estimate | Token counting is complex; use standard library or 4-char approximation |
| Conversation summarization | Custom summarization logic | Mem0's auto-consolidation + LangChain patterns | Mem0 handles memory consolidation; LangChain's ConversationSummaryBufferMemory is battle-tested |
| Thread management | Custom session-to-thread mapping | LangGraph's native thread_id | Built-in thread isolation and state accumulation |

**Key insight:** LangGraph's checkpointing and Neo4j GraphRAG's retrievers handle the most complex parts of this phase. Focus implementation effort on workflow logic, not infrastructure.

## Common Pitfalls

### Pitfall 1: Not Calling checkpointer.setup()

**What goes wrong:** PostgresSaver silently fails or throws cryptic database errors because required tables don't exist.

**Why it happens:** Developers assume tables are auto-created or forget during deployment.

**How to avoid:** Always call `await checkpointer.setup()` after creating the checkpointer, before compiling the graph. Make this part of application startup.

**Warning signs:** "relation does not exist" PostgreSQL errors; checkpoints not persisting.

### Pitfall 2: State Schema Mismatch After Updates

**What goes wrong:** Existing checkpoints become incompatible when state schema changes (adding/removing fields).

**Why it happens:** LangGraph checkpoints serialize the entire state; schema changes break deserialization.

**How to avoid:**
- Use Optional types for new fields with defaults
- Version your state schemas
- Clear old checkpoints when making breaking changes
- Add migration logic if needed

**Warning signs:** Deserialization errors when resuming old workflows.

### Pitfall 3: Graph Traversal Query Explosion

**What goes wrong:** Multi-hop Neo4j queries return massive result sets, causing memory issues and slow responses.

**Why it happens:** Unbounded graph traversals (no LIMIT, no depth restriction) in knowledge graphs with many relationships.

**How to avoid:**
- Always use LIMIT in Cypher queries
- Restrict traversal depth (e.g., 2-3 hops maximum)
- Filter by relationship types
- Use query timeout settings

**Warning signs:** Neo4j queries taking >2 seconds; memory usage spikes during retrieval.

### Pitfall 4: Memory Summarization Losing Critical Information

**What goes wrong:** Important facts are lost when memory is summarized, leading to degraded response quality.

**Why it happens:** Aggressive summarization without preserving key entities like names, dates, decisions.

**How to avoid:**
- Use structured extraction before summarization
- Maintain separate "critical facts" store that's never summarized
- Test summarization quality with representative conversations
- Keep recent interactions verbatim (ConversationSummaryBufferMemory pattern)

**Warning signs:** User reports of "you forgot about X"; quality degradation in long conversations.

### Pitfall 5: Thread ID Collisions in Multi-User System

**What goes wrong:** Different users' workflow states get mixed up because of thread_id reuse.

**Why it happens:** Using simple sequential IDs or not including user_id in thread naming.

**How to avoid:**
- Thread ID format: `{user_id}:{workflow_type}:{session_id}`
- Never reuse thread IDs across users
- Include user validation in all workflow invocations

**Warning signs:** User seeing another user's workflow state; security audit failures.

## Code Examples

Verified patterns from official sources:

### Complete Document Comparison Workflow Setup

```python
# Source: LangGraph documentation + Neo4j GraphRAG docs
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from neo4j_graphrag.retrievers import VectorCypherRetriever
from neo4j import GraphDatabase
from typing import TypedDict, List

# State schema
class DocumentComparisonState(TypedDict):
    query: str
    user_id: str
    document_ids: List[str]
    retrieved_chunks: dict
    graph_context: dict
    comparison_result: dict
    response: str
    citations: List[dict]
    status: str

# Workflow definition
async def build_comparison_workflow(db_uri: str, neo4j_driver):
    workflow = StateGraph(DocumentComparisonState)

    # Nodes (implementations shown in Pattern 5)
    workflow.add_node("retrieve", retrieve_documents_node)
    workflow.add_node("expand_graph", expand_graph_context_node)
    workflow.add_node("compare", analyze_comparison_node)
    workflow.add_node("generate", generate_response_node)

    # Linear flow for document comparison
    workflow.set_entry_point("retrieve")
    workflow.add_edge("retrieve", "expand_graph")
    workflow.add_edge("expand_graph", "compare")
    workflow.add_edge("compare", "generate")
    workflow.add_edge("generate", END)

    # Compile with production checkpointer
    async with AsyncPostgresSaver.from_conn_string(db_uri) as checkpointer:
        await checkpointer.setup()
        return workflow.compile(checkpointer=checkpointer)
```

### Invoking Workflow with Thread Persistence

```python
# Source: LangGraph persistence documentation
async def compare_documents(
    workflow,
    user_id: str,
    query: str,
    document_ids: List[str],
    session_id: str
):
    """Invoke document comparison workflow with persistent state."""
    # Thread ID includes user for isolation
    thread_id = f"{user_id}:doc_compare:{session_id}"

    config = {
        "configurable": {
            "thread_id": thread_id,
            "user_id": user_id  # Available in nodes via config
        }
    }

    initial_state = {
        "query": query,
        "user_id": user_id,
        "document_ids": document_ids,
        "retrieved_chunks": {},
        "graph_context": {},
        "comparison_result": {},
        "response": "",
        "citations": [],
        "status": "started"
    }

    # Invoke (resumes from checkpoint if exists)
    result = await workflow.ainvoke(initial_state, config)
    return result
```

### Memory Summarization Integration

```python
# Source: Mem0 documentation + research
from mem0 import Memory
from app.config import settings

class ConversationMemoryManager:
    """Manages conversation memory with automatic summarization."""

    MAX_CONTEXT_TOKENS = 4000
    SUMMARIZATION_TRIGGER = 3000  # 75% threshold

    def __init__(self, mem0_client: Memory, llm):
        self.mem0 = mem0_client
        self.llm = llm

    async def add_interaction(
        self,
        user_id: str,
        query: str,
        response: str,
        session_id: str
    ):
        """Add interaction to memory, triggering summarization if needed."""
        # Add to Mem0 (handles automatic consolidation)
        self.mem0.add(
            messages=[
                {"role": "user", "content": query},
                {"role": "assistant", "content": response}
            ],
            user_id=user_id,
            metadata={"session_id": session_id}
        )

        # Check if manual summarization needed
        await self._check_and_summarize(user_id)

    async def _check_and_summarize(self, user_id: str):
        """Check memory size and summarize if exceeding threshold."""
        memories = self.mem0.get_all(user_id=user_id)

        # Estimate tokens (rough: 4 chars = 1 token)
        total_chars = sum(len(str(m.get("memory", ""))) for m in memories)
        estimated_tokens = total_chars // 4

        if estimated_tokens > self.SUMMARIZATION_TRIGGER:
            await self._perform_summarization(user_id, memories)

    async def _perform_summarization(self, user_id: str, memories: list):
        """Summarize older memories, keeping recent ones intact."""
        # Keep last 5 interactions verbatim
        recent = memories[-5:]
        to_summarize = memories[:-5]

        if not to_summarize:
            return

        # Create summary
        memory_text = "\n".join([str(m.get("memory", "")) for m in to_summarize])
        summary = await self.llm.ainvoke([
            {"role": "system", "content": "Create a concise summary of the user's key preferences, facts, and conversation history. Preserve specific names, dates, and decisions."},
            {"role": "user", "content": memory_text}
        ])

        # Delete old memories and add summary
        for m in to_summarize:
            self.mem0.delete(m["id"])

        self.mem0.add(
            f"[Historical Summary]: {summary.content}",
            user_id=user_id,
            metadata={"type": "summary", "summarized_count": len(to_summarize)}
        )
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| LangChain Memory classes | LangGraph checkpointing + Store | LangGraph 1.0 (2026) | Proper state persistence; cross-thread memory via Store interface |
| Custom graph traversal | Neo4j GraphRAG VectorCypherRetriever | neo4j-graphrag-python GA | Standardized multi-hop retrieval patterns |
| Manual token counting | Automatic memory consolidation (Mem0) | Mem0 v1.1 | 90% token savings with auto-pruning |
| In-memory checkpoints | PostgresSaver for production | langgraph-checkpoint-postgres 3.0 | Durable state across restarts |

**Deprecated/outdated:**
- **ConversationBufferMemory**: Use LangGraph state with checkpointing instead
- **LangChain's legacy Memory classes**: Deprecated in v0.3.1, removed in 1.0
- **Custom checkpoint implementations**: Use official checkpointer libraries

## Open Questions

Things that couldn't be fully resolved:

1. **Optimal Graph Traversal Depth**
   - What we know: 2-3 hops is common; more increases latency exponentially
   - What's unclear: Optimal depth varies by knowledge graph density; no universal rule
   - Recommendation: Start with 2 hops, measure accuracy and latency, increase if needed

2. **Memory Summarization Quality Metrics**
   - What we know: Summarization can lose critical facts; no standard evaluation
   - What's unclear: How to objectively measure summarization quality
   - Recommendation: A/B test with user satisfaction metrics; keep critical entities in separate store

3. **PostgresSaver Connection Pooling in FastAPI**
   - What we know: PostgresSaver works with connection strings and async contexts
   - What's unclear: Best practice for integrating with FastAPI's lifecycle and connection pooling
   - Recommendation: Create checkpointer per request in endpoint or use app-level async context manager

4. **Store Interface for Cross-Thread Memory**
   - What we know: LangGraph's Store interface enables cross-thread memory sharing
   - What's unclear: How this interacts with Mem0's memory management
   - Recommendation: Use Store for workflow-specific memory; Mem0 for long-term user memory

## Sources

### Primary (HIGH confidence)
- [LangGraph Persistence Documentation](https://docs.langchain.com/oss/python/langgraph/persistence) - Checkpointing, threads, Store interface
- [Neo4j GraphRAG Python Documentation](https://neo4j.com/docs/neo4j-graphrag-python/current/user_guide_rag.html) - VectorCypherRetriever, multi-hop patterns
- [langgraph-checkpoint-postgres PyPI](https://pypi.org/project/langgraph-checkpoint-postgres/) - v3.0.4, PostgresSaver configuration
- [Qdrant GraphRAG with Neo4j](https://qdrant.tech/documentation/examples/graphrag-qdrant-neo4j/) - Integration architecture

### Secondary (MEDIUM confidence)
- [Thinking in LangGraph](https://docs.langchain.com/oss/python/langgraph/thinking-in-langgraph) - Node design, state management best practices
- [Mem0 Research Paper](https://arxiv.org/abs/2504.19413) - Memory consolidation, 26% accuracy improvement
- [Neo4j Multi-Hop Reasoning Blog](https://neo4j.com/blog/genai/knowledge-graph-llm-multi-hop-reasoning/) - GraphRAG patterns
- [LangGraph Explained 2026](https://medium.com/@dewasheesh.rana/langgraph-explained-2026-edition-ea8f725abff3) - State management overview
- [Mastering LangGraph Checkpointing 2025](https://sparkco.ai/blog/mastering-langgraph-checkpointing-best-practices-for-2025) - Production checkpointing patterns

### Tertiary (LOW confidence - needs validation)
- [Context Window Management Strategies](https://apxml.com/courses/langchain-production-llm/chapter-3-advanced-memory-management/context-window-management) - Summarization patterns
- [Preventing Context Window Overflows](https://aiq.hu/en/preventing-context-window-overflows-memory-protection-strategies-for-llms/) - Memory protection strategies

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - LangGraph 1.0 and Neo4j GraphRAG Python are GA with official documentation
- Architecture: MEDIUM-HIGH - Patterns from official docs but document comparison workflow is application-specific
- Pitfalls: MEDIUM - Compiled from multiple sources; some require validation in this specific codebase

**Research date:** 2026-02-04
**Valid until:** 2026-03-04 (30 days - LangGraph ecosystem moving fast)

**Dependencies from existing codebase:**
- Neo4j client already configured in `/backend/app/db/neo4j_client.py`
- Qdrant client in `/backend/app/db/qdrant_client.py`
- Mem0 configured in `/backend/app/db/mem0_client.py`
- Retrieval service in `/backend/app/services/retrieval_service.py` needs extension for multi-hop
- Requires PostgreSQL database for LangGraph checkpointing (new dependency)

**New dependencies to add:**
```bash
# requirements.txt additions
langgraph>=1.0
langgraph-checkpoint-postgres>=3.0.4
psycopg[binary]>=3.0
neo4j-graphrag-python
```
