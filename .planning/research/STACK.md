# Technology Stack

**Project:** RAG with Memory Management (Mem0 + Neo4j + Qdrant)
**Researched:** 2026-02-04
**Overall Confidence:** HIGH

## Executive Summary

The 2025-2026 standard stack for production RAG systems with graph + vector storage and memory management has converged around a clear set of technologies. This stack balances performance, developer experience, and production maturity. The core architecture pairs Mem0 SDK (for intelligent memory management) with dual storage backends (Neo4j for relationship graphs + Qdrant for vector search), orchestrated by LangChain/LangGraph, exposed through FastAPI, and powered by OpenAI's latest models.

## Recommended Stack

### Core Framework

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **FastAPI** | >=0.126.0 | Web framework & API server | Industry standard for async Python APIs in 2026. Native async support, automatic OpenAPI docs, Pydantic v2 integration. Proven at scale. | HIGH |
| **Pydantic** | >=2.7.0 | Data validation & settings | FastAPI's foundation. v2 is now the standard (v1 deprecated). Type-safe configuration and request/response validation. | HIGH |
| **Python** | >=3.10, <4.0 | Runtime | Minimum for modern type hints and performance. LangChain requires 3.10+, Neo4j driver supports up to 3.14. | HIGH |

**Rationale:** FastAPI + Pydantic v2 is the 2026 gold standard for production ML/AI APIs. Async-first architecture handles concurrent RAG requests efficiently. Built-in OpenAPI support simplifies frontend integration and API documentation.

### Memory Management Layer

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **Mem0 SDK** | latest | Intelligent memory management | Self-improving memory layer specifically designed for RAG. Dual-store architecture (graph + vector). 26% higher accuracy than OpenAI's memory, 91% lower latency than full-context approaches. Multi-user support with user/session/agent scopes. | HIGH |

**Rationale:** Mem0 is purpose-built for exactly this use case. Unlike generic vector stores, it provides intelligent memory consolidation, contradiction resolution, and automatic memory extraction from conversations. Supports both Neo4j (graph) and Qdrant (vector) natively with shared ID cross-referencing.

**Installation:** `pip install mem0ai`

### Database - Dual Storage Architecture

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **Neo4j** | Database 5.x | Graph database for relationships | Industry-leading graph database. Stores entity relationships and knowledge graphs. Enables Cypher queries for complex relationship traversal. Mem0's preferred graph store. | HIGH |
| **neo4j** (Python driver) | 6.1.0 | Neo4j Python client | Official driver, production-stable. Released Jan 2026. Supports Python 3.10-3.14. **NOTE:** Use `neo4j` package, NOT deprecated `neo4j-driver`. | HIGH |
| **Qdrant** | 1.x server | Vector database for embeddings | Fast, open-source vector search engine. Hybrid search (dense + sparse vectors). Efficient k-NN search at scale. Native Mem0 integration. | HIGH |
| **qdrant-client** | 1.16.2 | Qdrant Python client | Official client with async support (since v1.6.1). Supports local in-memory mode for testing. | HIGH |

**Rationale:** This dual-store architecture combines semantic search (Qdrant) with relationship reasoning (Neo4j). Mem0 acts as the orchestration layer, maintaining shared IDs between both stores for cross-referencing. Qdrant handles vector similarity efficiently while Neo4j adds structural context through graph traversal.

### LLM Orchestration

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **LangChain** | 1.0+ | High-level LLM orchestration | De facto standard for RAG workflows. Extensive integrations (100+ providers). Quick prototyping with chains. Seamless LangGraph integration. | HIGH |
| **langchain-openai** | 1.1.7 | OpenAI integration for LangChain | Official OpenAI connector. Latest release (Jan 7, 2026). Provides ChatOpenAI for reasoning. | HIGH |
| **LangGraph** | 1.0+ | Stateful agent workflows | Production-grade state management with rollback/checkpointing. Essential for complex multi-step RAG workflows with branching logic. Built on LangChain, fully compatible. | HIGH |

**Rationale:** Use **LangChain for simple, linear RAG pipelines** (document ingestion, retrieval, generation). Use **LangGraph when you need stateful, multi-step workflows** (document comparison, iterative refinement, human-in-the-loop). LangGraph v1.0 (GA as of 2026) provides robust state management that LangChain's basic memory can't match. They work together seamlessly—start with LangChain, add LangGraph when complexity demands it.

**Key Decision:** LangChain agents are now built on LangGraph under the hood. Legacy LangChain 0.3 + LangGraph 0.4 are in maintenance mode until Dec 2026.

### LLM & Embeddings

| Technology | Model | Purpose | Why | Confidence |
|------------|-------|---------|-----|------------|
| **OpenAI API** | GPT-4o / GPT-4 | Chat/reasoning model | Production-ready reasoning for RAG. ChatOpenAI via langchain-openai. | HIGH |
| **OpenAI Embeddings** | text-embedding-3-small | Vector embeddings | Best price/performance for RAG. $0.02/1M tokens (5x cheaper than ada-002). 54.9% MIRACL score (vs 31.4% for ada-002). Up to 1536 dimensions. | HIGH |
| **OpenAI Embeddings** | text-embedding-3-large | High-accuracy embeddings (optional) | Most capable model for critical applications. 3072 dimensions. $0.13/1M tokens. Use when accuracy > cost. | MEDIUM |

**Rationale:** text-embedding-3-small is the 2026 standard for RAG—massive performance improvement over ada-002 at 5x lower cost. Upgrade to text-embedding-3-large only if benchmarks show meaningful accuracy gains for your domain. Both are dense, multilingual, and optimized for RAG retrieval.

### Document Processing

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **pymupdf4llm** | latest | PDF to Markdown conversion | Sweet spot of speed and quality for RAG. Converts PDFs to GitHub-compatible Markdown with integrated table handling. Designed specifically for LLM/RAG pipelines. Fast (0.003-0.024s per page). | HIGH |
| **Docling** | latest (optional) | Advanced PDF/DOCX/PPTX parsing | IBM's open-source toolkit (MIT). Use when you need advanced layout analysis, table structure recognition (TableFormer AI model), or multi-format support (PDF, DOCX, PPTX, HTML, images, audio). Slower (4s/page) but more accurate for complex documents. | MEDIUM |
| **MarkItDown** | latest (alternative) | Multi-format document conversion | Microsoft's converter for diverse formats. Good for RAG systems ingesting multiple document types. `pip install 'markitdown[all]'` for full support. | MEDIUM |

**Rationale:** **Use pymupdf4llm as default** for PDF processing—it's fast, reliable, and outputs clean Markdown perfect for RAG chunking. **Add Docling** when you have complex layouts, tables, or mixed formats (DOCX, PPTX) that pymupdf4llm can't handle well. Both are production-tested for RAG workflows.

**What NOT to use:**
- ❌ **Unstructured** - Slower than pymupdf4llm, results quality varies significantly by document
- ❌ **pypdf/pdfplumber** - Not optimized for LLM/RAG workflows, requires extensive post-processing
- ❌ **textract** - OCR-focused, unnecessary complexity for born-digital PDFs

### Authentication & Security

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **PyJWT** | latest | JWT token generation/verification | Industry standard for stateless auth. Used by FastAPI official docs. | HIGH |
| **pwdlib** | latest with Argon2 | Password hashing | FastAPI's official recommendation. Argon2 is resistant to GPU cracking (vs bcrypt/scrypt). OWASP-compliant. | HIGH |
| **OAuth2PasswordBearer** | (FastAPI built-in) | OAuth2 flow | FastAPI's native OAuth2 implementation. Stateless, scalable. | HIGH |

**Rationale:** FastAPI's official pattern: OAuth2 + JWT for API auth, pwdlib with Argon2 for password hashing. This is the 2026 gold standard—stateless, secure, OWASP Top 10 compliant. Short-lived access tokens (15-30 min) + refresh tokens for session persistence.

**Security Best Practices (2026):**
- ✅ Store passwords as Argon2 hashes only
- ✅ Short-lived JWTs (15-30 min)
- ✅ Refresh tokens for session management
- ✅ HTTPS only in production
- ✅ HttpOnly cookies for token storage (or secure client storage)
- ✅ Environment variables for secrets (NEVER hardcode)
- ❌ NEVER put sensitive data in JWT payload (JWTs are not encrypted)

### Production Deployment

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **Uvicorn** | latest | ASGI server | High-performance async server for FastAPI. Production-ready. | HIGH |
| **Gunicorn** | latest | Process manager | Industry standard: Gunicorn + Uvicorn workers for parallelism. Formula: `(2 * CPU cores) + 1` workers as starting point. | HIGH |

**Deployment Command:**
```bash
gunicorn -k uvicorn.workers.UvicornWorker main:app \
  --workers 4 \
  --bind 0.0.0.0:8000 \
  --timeout 30 \
  --graceful-timeout 10 \
  --keepalive 5
```

**Rationale:** Gunicorn provides multi-process parallelism, Uvicorn provides async concurrency per process. This combination is the 2026 FastAPI deployment standard. Add Nginx as reverse proxy for SSL termination, caching, rate limiting.

**What NOT to use:**
- ❌ **FastAPI development server** (`uvicorn main:app --reload`) - Never in production, becomes bottleneck under load
- ❌ **Single Uvicorn process** - Wastes multi-core servers (unless Kubernetes-managed)

### Supporting Libraries

| Library | Version | Purpose | When to Use | Confidence |
|---------|---------|---------|-------------|------------|
| **python-dotenv** | latest | Environment variable management | Load .env files for local development. Never in production (use OS env vars). | HIGH |
| **httpx** | latest | Async HTTP client | If you need to call external APIs from async FastAPI routes. | MEDIUM |
| **pytest** | latest | Testing framework | Unit/integration tests for FastAPI routes and RAG pipelines. | HIGH |
| **pytest-asyncio** | latest | Async test support | Test async FastAPI endpoints. | HIGH |

## Alternatives Considered

| Category | Recommended | Alternative | Why Not | Confidence |
|----------|-------------|-------------|---------|------------|
| **Memory Layer** | Mem0 | LangChain Memory | LangChain's memory is basic (context window only). No graph integration, no auto-consolidation. Mem0 provides 26% higher accuracy and 91% lower latency. | HIGH |
| **Memory Layer** | Mem0 | LangGraph State | LangGraph state is workflow-specific, not persistent cross-session memory. Use LangGraph for workflow state, Mem0 for long-term memory. | HIGH |
| **Graph DB** | Neo4j | Amazon Neptune | Neptune is AWS-only, vendor lock-in. Neo4j is industry standard with better tooling and community. | MEDIUM |
| **Vector DB** | Qdrant | Pinecone | Pinecone is cloud-only, expensive at scale. Qdrant is open-source, self-hostable, and has native Mem0 integration. | HIGH |
| **Vector DB** | Qdrant | Milvus | Milvus is solid but more complex to operate. Qdrant has simpler deployment and better Mem0 support. | MEDIUM |
| **Vector DB** | Qdrant | ChromaDB | Chroma is good for prototyping but not production-grade. Qdrant handles scale better. | MEDIUM |
| **Vector DB** | Qdrant | pgvector (PostgreSQL) | pgvector is convenient but slower for large-scale vector search. Use Qdrant for dedicated vector workloads. | MEDIUM |
| **Web Framework** | FastAPI | Flask | Flask is synchronous. RAG requires async I/O for LLM calls. FastAPI is purpose-built for async. | HIGH |
| **Web Framework** | FastAPI | Django | Django is heavy, sync-first. Overkill for API-only backend. FastAPI is lighter and async-native. | HIGH |
| **Orchestration** | LangChain + LangGraph | LlamaIndex | LlamaIndex is excellent for RAG but less flexible for agents/workflows. LangChain has broader ecosystem. | MEDIUM |
| **Orchestration** | LangChain + LangGraph | AutoGen | AutoGen focuses on multi-agent systems, not RAG primitives. LangChain has better RAG tooling. | MEDIUM |
| **Document Parser** | pymupdf4llm | Unstructured | Unstructured is slower and quality varies. pymupdf4llm is faster and more consistent for PDFs. | HIGH |
| **Password Hashing** | pwdlib + Argon2 | bcrypt | Argon2 is more resistant to GPU attacks. FastAPI official recommendation. | HIGH |
| **Deployment** | Gunicorn + Uvicorn | Standalone Uvicorn | Single-process Uvicorn wastes multi-core servers. Gunicorn provides process management. | HIGH |

## Multi-Tenancy Architecture (Private + Shared Memory Spaces)

**Pattern:** Schema-level separation in PostgreSQL + metadata-based filtering in vector stores

| Component | Multi-Tenancy Approach | Rationale |
|-----------|------------------------|-----------|
| **Mem0 Memory** | User ID metadata filtering | Mem0 supports user_id in all operations. Ensures strict data isolation per user. |
| **Neo4j** | Shared database with user_id properties | Neo4j queries filter by user_id property. Cost-efficient, scales to 1000s of users. For strict isolation, use separate databases (silo pattern). |
| **Qdrant** | Metadata-based filtering by user_id | Qdrant filters vectors by user_id metadata during search. Orders of magnitude faster than post-filtering. |
| **Shared Spaces** | Special user_id (e.g., "shared") or organization_id | Documents tagged with shared/org identifier. All users in org can query. |
| **Anonymous Sessions** | Session-scoped user_id (e.g., "anon_{session_id}") | Temporary memory tied to session. Clean up after expiry. |

**Best Practice:** Implement API middleware that injects user_id from JWT into all Mem0/Neo4j/Qdrant operations. Never trust client-provided user_id.

**Confidence:** HIGH - This is the 2026 standard for multi-tenant RAG (used by Zendesk, HubSpot, Notion AI features).

## Installation & Setup

### Core Dependencies

```bash
# Core framework
pip install "fastapi>=0.126.0"
pip install "pydantic>=2.7.0"
pip install "uvicorn[standard]"
pip install gunicorn

# Memory & orchestration
pip install mem0ai
pip install "langchain>=1.0"
pip install "langchain-openai>=1.1.7"
pip install "langgraph>=1.0"

# Databases
pip install "neo4j>=6.1.0"  # NOT neo4j-driver (deprecated)
pip install "qdrant-client>=1.16.2"

# Document processing
pip install pymupdf4llm  # Primary PDF parser
pip install docling  # Optional: for complex layouts/DOCX/PPTX
# pip install 'markitdown[all]'  # Alternative: multi-format support

# Authentication
pip install pyjwt
pip install "pwdlib[argon2]"

# Development
pip install python-dotenv
pip install pytest pytest-asyncio
```

### Mem0 Configuration Example

```python
from mem0 import Memory

config = {
    "version": "v1.1",
    "llm": {
        "provider": "openai",
        "config": {
            "model": "gpt-4o",
            "temperature": 0.1,
        }
    },
    "embedder": {
        "provider": "openai",
        "config": {
            "model": "text-embedding-3-small",
        }
    },
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "collection_name": "memories",
            "host": "localhost",
            "port": 6333,
        }
    },
    "graph_store": {
        "provider": "neo4j",
        "config": {
            "url": "bolt://localhost:7687",
            "username": "neo4j",
            "password": "password",
        }
    },
}

memory = Memory.from_config(config)

# Add memory with user isolation
memory.add("User uploaded document about AI safety", user_id="user_123")

# Search memory for specific user
results = memory.search("AI safety", user_id="user_123")
```

## Version Pinning Strategy

**Production:** Pin exact versions in `requirements.txt`:
```
fastapi==0.126.0
langchain==1.0.0
mem0ai==0.1.X  # Check latest stable
```

**Development:** Use minimum versions in `pyproject.toml`:
```toml
[project.dependencies]
fastapi = ">=0.126.0"
langchain = ">=1.0"
```

**Rationale:** Exact pins prevent surprise breakages in production. Minimum versions allow dependency resolver flexibility in development.

## Configuration Management

**Development:**
```python
# .env file (NEVER commit)
OPENAI_API_KEY=sk-...
NEO4J_PASSWORD=password
SECRET_KEY=dev-secret-key

# Load with python-dotenv
from dotenv import load_dotenv
load_dotenv()
```

**Production:**
- Use environment variables set by deployment platform (Kubernetes secrets, AWS SSM, etc.)
- Use secret management services (AWS Secrets Manager, HashiCorp Vault)
- NEVER store secrets in .env files in production

## Performance Considerations

| Concern | Solution | Impact |
|---------|----------|--------|
| **Cold start latency** | Keep models loaded (LangChain caching) | Sub-2s response times |
| **Concurrent requests** | Gunicorn workers + async Uvicorn | Handle 100s of concurrent users |
| **Memory search speed** | Qdrant's HNSW index + metadata filtering | <100ms vector search at 1M+ vectors |
| **Graph query performance** | Neo4j indexes on user_id + entity types | <50ms Cypher queries |
| **Token costs** | Use text-embedding-3-small (5x cheaper) | 80% cost reduction vs ada-002 |

## Observability & Monitoring

**Recommended (choose one):**
- **LangSmith** (LangChain official) - Trace analysis, debugging, audit trails for LangChain/LangGraph workflows
- **FastAPI middleware** - Custom logging for request/response, latency tracking
- **Prometheus + Grafana** - Metrics for API latency, throughput, error rates

**Key Metrics to Track:**
- RAG response latency (target: <2s)
- Memory search latency (target: <100ms)
- Hallucination rate (target: <1%)
- Cost per query (OpenAI API usage)
- Document processing time

## Confidence Assessment

| Component | Confidence | Reason |
|-----------|------------|--------|
| FastAPI + Pydantic v2 | **HIGH** | Official docs verified. Industry standard 2026. |
| Mem0 SDK | **HIGH** | Official docs verified. Purpose-built for this use case. Benchmarks published. |
| Neo4j + Qdrant | **HIGH** | Official drivers verified. Production-stable versions. Native Mem0 support confirmed. |
| LangChain + LangGraph | **HIGH** | v1.0 GA releases verified. Official compatibility confirmed. |
| OpenAI models | **HIGH** | Official API docs verified. Production models with published pricing. |
| Document parsers | **HIGH** | Multiple 2025-2026 benchmarks confirm pymupdf4llm as speed/quality leader. |
| Auth pattern | **HIGH** | FastAPI official tutorial verified. OWASP-compliant. |
| Deployment | **HIGH** | Industry standard confirmed across multiple 2026 sources. |

## Sources

**Mem0:**
- [Mem0 Official Docs - Introduction](https://docs.mem0.ai/introduction)
- [Mem0 Qdrant Integration](https://qdrant.tech/documentation/frameworks/mem0/)
- [Mem0 GitHub Repository](https://github.com/mem0ai/mem0)
- [Mem0 Research Paper (arXiv 2504.19413)](https://arxiv.org/abs/2504.19413)
- [AWS Blog: Mem0 with Neptune and ElastiCache](https://aws.amazon.com/blogs/database/build-persistent-memory-for-agentic-ai-applications-with-mem0-open-source-amazon-elasticache-for-valkey-and-amazon-neptune-analytics/)

**Neo4j + Qdrant Integration:**
- [Integrate Qdrant and Neo4j to Enhance RAG Pipeline](https://neo4j.com/blog/developer/qdrant-to-enhance-rag-pipeline/)
- [Qdrant: GraphRAG with Neo4j](https://qdrant.tech/documentation/examples/graphrag-qdrant-neo4j/)
- [Neo4j GraphRAG Documentation](https://neo4j.com/docs/neo4j-graphrag-python/current/user_guide_rag.html)

**LangChain + LangGraph:**
- [LangChain 1.0 vs LangGraph 1.0 (2026)](https://www.clickittech.com/ai/langchain-1-0-vs-langgraph-1-0/)
- [LangGraph vs LangChain 2026 Comparison](https://langchain-tutorials.github.io/langgraph-vs-langchain-2026/)
- [LangChain and LangGraph 1.0 Milestones](https://www.blog.langchain.com/langchain-langgraph-1dot0/)
- [langchain-openai PyPI](https://pypi.org/project/langchain-openai/)

**FastAPI + Authentication:**
- [FastAPI OAuth2 with JWT (Official)](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/)
- [Securing FastAPI with JWT (TestDriven.io)](https://testdriven.io/blog/fastapi-jwt-auth/)
- [FastAPI JWT Authentication 2026 Guide](https://medium.com/@jagan_reddy/jwt-in-fastapi-the-secure-way-refresh-tokens-explained-f7d2d17b1d17)

**Document Processing:**
- [I Tested 7 Python PDF Extractors (2025 Edition)](https://dev.to/onlyoneaman/i-tested-7-python-pdf-extractors-so-you-dont-have-to-2025-edition-akm)
- [pymupdf4llm GitHub](https://github.com/pymupdf/RAG)
- [Docling for PDF to Markdown](https://www.mindfiretechnology.com/blog/archive/docling-for-pdf-to-markdown-conversion/)

**Production Deployment:**
- [FastAPI Deployment Guide 2026](https://www.zestminds.com/blog/fastapi-deployment-guide/)
- [Uvicorn Deployment Guide](https://uvicorn.dev/deployment/)
- [Production Deployment with Gunicorn/Uvicorn](https://apxml.com/courses/fastapi-ml-deployment/chapter-6-containerization-deployment-prep/production-deployment-gunicorn-uvicorn)

**Multi-Tenancy:**
- [Designing Multi-Tenancy RAG with Milvus](https://milvus.io/blog/build-multi-tenancy-rag-with-milvus-best-practices-part-one.md)
- [Azure: Secure Multitenant RAG](https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/secure-multitenant-rag)
- [Building Multi-Tenant RAG with PostgreSQL](https://www.tigerdata.com/blog/building-multi-tenant-rag-applications-with-postgresql-choosing-the-right-approach)

**OpenAI Models:**
- [text-embedding-3-small Model](https://platform.openai.com/docs/models/text-embedding-3-small)
- [text-embedding-3-large Model](https://platform.openai.com/docs/models/text-embedding-3-large)
- [OpenAI Vector Embeddings Guide](https://platform.openai.com/docs/guides/embeddings)

**Database Drivers:**
- [neo4j PyPI (v6.1.0)](https://pypi.org/project/neo4j/)
- [qdrant-client PyPI (v1.16.2)](https://pypi.org/project/qdrant-client/)

---

**Last Updated:** 2026-02-04
**Next Review:** Check for Mem0 SDK updates, LangChain/LangGraph patches, OpenAI model releases
