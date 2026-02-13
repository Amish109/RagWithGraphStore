# Database Architecture

## Overview

The project uses 5 data stores, each with a distinct responsibility:

| Store | Type | Deployment | Purpose |
|-------|------|-----------|---------|
| Neo4j | Graph DB | Cloud (Aura) | Structured data & relationships |
| Qdrant | Vector DB | Local Docker | Semantic search embeddings |
| Redis | Key-Value | Local Docker | Auth token management |
| PostgreSQL | Relational | Local Docker | LangGraph workflow checkpoints |
| Mem0 SDK | Orchestrator | In-process | Memory management across Neo4j + Qdrant |

---

## Neo4j (Graph Store) — Cloud Aura

Stores structured data and relationships as a graph.

### Node Labels

| Node | Key Properties |
|------|---------------|
| `User` | `id`, `email`, `hashed_password`, `role`, `created_at` |
| `Document` | `id`, `filename`, `user_id`, `upload_date`, `chunk_count`, `summary` |
| `Chunk` | `id`, `document_id`, `text`, `position`, `embedding_id`, `user_id` |
| `Entity` *(future)* | `name`, `type` — for GraphRAG multi-hop traversal |

### Relationships

- `(User)-[:OWNS]->(Document)` — document ownership
- `(Document)-[:CONTAINS]->(Chunk)` — document structure
- `(Entity)-[:APPEARS_IN]->(Chunk)` *(future)*
- `(Entity)-[:RELATES_TO]->(Entity)` *(future)*

### Constraints & Indexes

- Unique constraints on `User.id`, `Document.id`, `Chunk.id`
- Indexes on `User.email`, `Document.user_id`, `Chunk.document_id`
- All queries filter by `user_id` for multi-tenant isolation

---

## Qdrant (Vector Store) — Local Docker

Stores embeddings for semantic search. Uses two separate collections:

### `documents` Collection — RAG Document Chunks

- **Vectors**: 768d (Ollama/nomic-embed-text) or 1536d (OpenAI)
- **Distance**: Cosine
- **Payload fields**:

| Field | Type | Purpose |
|-------|------|---------|
| `text` | string | Chunk text content |
| `document_id` | UUID | Links to parent document |
| `user_id` | string | Multi-tenant isolation; `__shared__` for company-wide docs |
| `position` | integer | Order within document |

- **Indexed fields**: `user_id` (keyword), `document_id` (keyword)

### `memory` Collection — Mem0 Memories

- Same vector config, managed by Mem0 SDK
- Stores user facts, conversation history, shared company knowledge

---

## Redis — Local Docker

Used exclusively for auth token management (not for caching).

| Key Pattern | Data | TTL |
|------------|------|-----|
| `blocklist:{jti}` | `"1"` (revoked JWT marker) | 7 days |
| `refresh:{user_id}:{jti}` | SHA-256 hash of refresh token | 7 days |

All entries auto-expire after their token lifetime to prevent unbounded growth.

---

## PostgreSQL — Local Docker

Used exclusively for LangGraph workflow checkpointing.

### Tables (auto-created by LangGraph)

| Table | Purpose |
|-------|---------|
| `checkpoint` | Workflow state snapshots |
| `checkpoint_writes` | Pending write operations |
| `checkpoint_blobs` | Serialized state data (binary) |

No application tables — all user/document data lives in Neo4j.

---

## Mem0 SDK — Orchestration Layer

Not a database itself — it orchestrates writes to both Qdrant (`memory` collection) and Neo4j.

### Memory Types

| Memory Type | Source | Scope |
|-------------|--------|-------|
| User facts | Manual add via `/memory` API | Private per `user_id` |
| Conversation turns | Auto-captured from chat sessions | Private per session |
| Shared knowledge | Admin-created via `/memory/shared` | All authenticated users (`__shared__`) |

### Lifecycle

1. **Create**: `memory.add()` → embeds content → stores in Qdrant + Neo4j graph
2. **Search**: `memory.search()` → semantic search in Qdrant, filtered by `user_id`
3. **Delete**: `memory.delete()` → removes from Qdrant (Neo4j cleanup pending)
4. **TTL**: Anonymous memories auto-expire after `ANONYMOUS_DATA_TTL_DAYS` (default: 7)

---

## Cross-Store Linkage

```
User uploads document
        │
        ▼
   ┌─────────┐        ┌──────────┐
   │  Neo4j   │◄──────►│  Qdrant  │
   │ (graph)  │ shared │ (vectors)│
   │          │chunk ID│          │
   │ User     │        │documents │
   │ Document │        │collection│
   │ Chunk    │        │          │
   └─────────┘        └──────────┘
        │
   Mem0 SDK
        │
   ┌─────────┐        ┌──────────┐
   │  Neo4j   │◄──────►│  Qdrant  │
   │ (memory  │        │ memory   │
   │  graph)  │        │collection│
   └─────────┘        └──────────┘

   ┌─────────┐        ┌──────────┐
   │  Redis   │        │ Postgres │
   │ (tokens) │        │(LangGraph│
   │          │        │  state)  │
   └─────────┘        └──────────┘
```

- **Chunk IDs** are shared between Neo4j and Qdrant — vector search finds relevant chunks, then Neo4j enriches with document structure and relationships
- **Mem0** manages its own memory graph in Neo4j and vectors in a separate Qdrant collection
- **Redis** and **PostgreSQL** operate independently for auth and workflow state
