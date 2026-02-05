# Backend Architecture

## Directory Structure

```
backend/app/
├── main.py              # FastAPI entry point
├── config.py            # Environment settings
│
├── api/                 # REST endpoints
│   ├── auth.py          # Login, register, logout, refresh
│   ├── documents.py     # Upload, list, delete, summarize
│   ├── queries.py       # RAG Q&A with streaming
│   ├── comparisons.py   # Multi-document comparison
│   ├── memory.py        # User memory CRUD
│   └── admin.py         # Shared knowledge (admin only)
│
├── services/            # Business logic
│   ├── document_processor.py   # Parse PDF/DOCX → chunks
│   ├── embedding_service.py    # Text → vectors (OpenAI)
│   ├── indexing_service.py     # Store in Neo4j + Qdrant
│   ├── retrieval_service.py    # Hybrid search
│   ├── graphrag_service.py     # Multi-hop graph traversal
│   ├── generation_service.py   # LLM answer generation
│   ├── memory_service.py       # Mem0 integration
│   ├── confidence_service.py   # Response confidence scores
│   └── summarization_service.py
│
├── workflows/           # LangGraph multi-step flows
│   ├── document_comparison.py  # Compare docs workflow
│   └── nodes/                  # Workflow steps
│
├── db/                  # Database clients
│   ├── neo4j_client.py  # Graph database
│   ├── qdrant_client.py # Vector database
│   ├── redis_client.py  # Token blacklist + cache
│   ├── postgres_client.py # LangGraph checkpoints
│   └── mem0_client.py   # Memory store
│
├── core/                # Auth & security
│   ├── auth.py          # Password hashing, JWT creation
│   ├── security.py      # Token validation, user extraction
│   ├── rbac.py          # Role-based access (user/admin)
│   └── session.py       # Anonymous session management
│
├── models/              # Data schemas
│   ├── schemas.py       # Pydantic request/response
│   ├── user.py          # User CRUD (Neo4j)
│   └── document.py      # Document CRUD (Neo4j)
│
└── jobs/
    └── cleanup.py       # TTL cleanup for anonymous data
```

---

## Request Flow

### 1. Document Upload

```
POST /api/v1/documents/upload
         │
         ▼
┌─────────────────┐
│ document_processor │  Parse PDF/DOCX → text chunks
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ embedding_service │  Chunks → OpenAI embeddings
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ indexing_service  │  Store in both:
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
 Neo4j     Qdrant
(graph)   (vectors)
```

### 2. RAG Query

```
POST /api/v1/queries/
         │
         ▼
┌─────────────────┐
│ retrieval_service │  Hybrid search:
└────────┬────────┘   • Qdrant vector similarity
         │            • Neo4j graph relationships
         │
         ▼
┌─────────────────┐
│ memory_service    │  Add user context from Mem0
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ generation_service│  LLM generates answer + citations
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ confidence_service│  Calculate confidence score
└────────┬────────┘
         │
         ▼
    SSE Stream → Client
```

### 3. Document Comparison

```
POST /api/v1/comparisons/
         │
         ▼
┌──────────────────────┐
│ LangGraph Workflow    │
│  ┌─────────────────┐ │
│  │ retrieval_node  │ │  Get chunks from selected docs
│  └────────┬────────┘ │
│           ▼          │
│  ┌─────────────────┐ │
│  │ comparison_node │ │  LLM compares content
│  └────────┬────────┘ │
│           ▼          │
│  ┌─────────────────┐ │
│  │ generation_node │ │  Format response + citations
│  └─────────────────┘ │
└──────────────────────┘
```

---

## Data Storage

| Store | Purpose | Data |
|-------|---------|------|
| **Neo4j** | Graph DB | Users, Documents, Chunks, Entities, Relationships |
| **Qdrant** | Vector DB | Chunk embeddings for similarity search |
| **Redis** | Cache | Token blacklist, refresh token rotation |
| **PostgreSQL** | Checkpoints | LangGraph workflow state |
| **Mem0** | Memory | User conversation history, preferences |

---

## Authentication Flow

```
Register/Login
      │
      ▼
┌───────────┐     ┌───────────┐
│ access_token│     │refresh_token│
│  (15 min)  │     │  (7 days)  │
└─────┬─────┘     └─────┬─────┘
      │                 │
      ▼                 ▼
  API calls      POST /auth/refresh
      │                 │
      ▼                 ▼
  get_current_user   New token pair
  (JWT validation)   (old refresh blacklisted)
```

**Roles:**
- `user` — Default, access own documents/memory
- `admin` — Can manage shared knowledge base
- `anonymous` — Temporary session, auto-cleanup after TTL

---

## Multi-Tenant Isolation

All queries filter by `user_id`:

```cypher
// Neo4j - only user's documents
MATCH (d:Document {user_id: $user_id})

// Qdrant - filtered vector search
filter: { user_id: { $eq: user_id } }

// Mem0 - user-specific memory
mem0.search(query, user_id=user_id)
```

Shared knowledge uses sentinel: `user_id = "__shared__"`

---

## Key Environment Variables

```bash
# Databases
NEO4J_URI=bolt://localhost:7687
QDRANT_URL=http://localhost:6333
REDIS_URL=redis://localhost:6379
DATABASE_URL=postgresql://...

# AI
OPENAI_API_KEY=sk-...

# Auth
JWT_SECRET_KEY=your-secret
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
```
