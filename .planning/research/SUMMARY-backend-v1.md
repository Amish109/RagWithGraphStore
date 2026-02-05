# Project Research Summary

**Project:** RAG with Memory Management (Mem0 + Neo4j + Qdrant)
**Domain:** Multi-User Document Q&A System with Persistent Memory
**Researched:** 2026-02-04
**Confidence:** HIGH

## Executive Summary

RAG systems with persistent memory represent the 2026 standard for enterprise document Q&A platforms. This project combines three critical technologies in a hybrid architecture: Neo4j (graph relationships), Qdrant (vector search), and Mem0 (intelligent memory management). This stack delivers 20-25% accuracy improvements over pure vector approaches while maintaining sub-2s response times. FastAPI provides the async-first API layer, LangChain handles LLM orchestration, and OpenAI's GPT-4o with text-embedding-3-small embeddings power the AI capabilities.

The recommended approach prioritizes vector-first retrieval enriched with graph relationships, semantic chunking over fixed-size splits, and three-tier memory isolation (user-private, session-temporary, tenant-shared). Multi-tenancy is achieved through query-time metadata filtering rather than separate database instances. The critical architectural decision is separating document knowledge (RAG) from user memory (Mem0) - confusing these two is the #1 cause of RAG system failures.

Key risks include multi-tenant data isolation failures (critical security), memory deletion bugs leaving orphaned graph data (known Mem0 issue), LangGraph checkpoint bloat causing OOM errors, and poor chunking strategies torpedoing retrieval accuracy. These risks are entirely mitigatable with proper architecture from Phase 1: enforce tenant filtering in middleware, implement custom Neo4j cleanup, configure checkpoint TTL, and use semantic chunking from the start. The technology stack is production-proven, but the integration complexity requires careful phase ordering and testing.

## Key Findings

### Recommended Stack

The 2026 production stack for RAG systems with memory has crystallized around FastAPI + Mem0 + Neo4j + Qdrant + LangChain/LangGraph + OpenAI. This combination balances developer experience, performance, and production maturity. Mem0 specifically addresses the RAG-memory confusion that plagues 73% of failed RAG systems by providing purpose-built memory management with dual-store orchestration.

**Core technologies:**

- **FastAPI (>=0.126.0)**: Async-first web framework - industry standard for ML/AI APIs in 2026, handles concurrent RAG requests efficiently with native async/await
- **Mem0 SDK**: Intelligent memory management layer - 26% higher accuracy than OpenAI's memory, 91% lower latency than full-context, self-improving with contradiction resolution
- **Neo4j (5.x) + neo4j driver (6.1.0)**: Graph database for entity relationships - enables multi-hop reasoning and GraphRAG, critical for document comparison features
- **Qdrant (1.x) + qdrant-client (1.16.2)**: Vector database for semantic search - fast k-NN with hybrid search support, native Mem0 integration, sub-200ms retrieval
- **LangChain (1.0+) + langchain-openai (1.1.7)**: LLM orchestration - de facto standard for RAG workflows, 100+ integrations, seamless LangGraph compatibility
- **LangGraph (1.0+)**: Stateful agent workflows - production-grade state management with rollback/checkpointing for complex multi-step RAG
- **OpenAI GPT-4o**: Reasoning model - production-ready for RAG generation
- **OpenAI text-embedding-3-small**: Embeddings - best price/performance (5x cheaper than ada-002, 54.9% vs 31.4% MIRACL score)
- **pymupdf4llm**: PDF processing - fastest for RAG (0.003-0.024s/page), outputs clean Markdown, sweet spot of speed and quality
- **pwdlib with Argon2**: Password hashing - FastAPI official recommendation, GPU-resistant, OWASP-compliant
- **Gunicorn + Uvicorn**: Deployment - industry standard multi-process + async workers pattern

**Key architectural decisions:**
- Use LangChain for linear RAG pipelines (document ingestion, retrieval, generation)
- Add LangGraph only when stateful workflows require it (document comparison, iterative refinement)
- Start with pymupdf4llm for PDFs; add Docling only if complex layouts/tables require it
- Use query-time metadata filtering for multi-tenancy, not separate database instances
- Short-lived JWTs (15-30 min) + refresh tokens for security

### Expected Features

RAG systems in 2026 have clear table stakes vs. differentiators. Memory is no longer novel - it's expected. The real differentiation comes from how memory is managed, document processing sophistication, and trustworthiness through citations.

**Must have (table stakes):**
- PDF/DOCX upload and processing with streaming progress indicators
- Natural language queries with streaming responses (non-streaming feels broken in 2026)
- Source citations (mandatory - 17-33% hallucination rate makes this critical for trust)
- "I don't know" responses when context is insufficient (prevents hallucinations)
- Conversation history with session persistence (memory is table stakes, not differentiator)
- Multi-user isolation with document access control (security requirement, not just feature)
- JWT authentication with user registration/login
- Anonymous session support (reduce friction for trial users)
- Document list/management and deletion (GDPR/privacy requirement)
- Sub-2 second query response times (slower feels broken)
- Graceful error handling and rate limiting

**Should have (competitive edge):**
- Multi-document comparison powered by GraphRAG (few RAG systems do this well - leverage your Neo4j advantage)
- Shared knowledge spaces for team collaboration (major enterprise need)
- Document summarization (saves user time on long documents)
- Highlighted citations showing exact text passages (superior UX)
- Follow-up question suggestions (guides exploration)
- Confidence scores (builds trust - users know when to verify)
- Memory summarization to prevent context overflow
- Cross-session memory (system "remembers" user preferences)

**Defer (v2+):**
- Advanced chunking strategies (start with semantic, optimize later)
- Reranking layer (10-20% improvement but adds complexity)
- Hybrid search (combine semantic + keyword BM25)
- Multimodal support (images, charts - very high complexity)
- Document versioning (VersionRAG framework)
- Voice input
- Integrations (Slack, Teams, etc.)
- Advanced analytics dashboard
- Custom embedding models (OpenAI embeddings suffice for general use)

**Anti-features (explicitly don't build):**
- Custom embedding fine-tuning (expensive, rarely beats OpenAI for general use)
- 100+ configuration options exposed to users (decision paralysis)
- Multi-LLM provider support (adds complexity for minimal benefit)
- Real-time collaborative document editing (different product category)
- Every document format (start PDF + DOCX, covers 80% of use cases)

### Architecture Approach

The recommended architecture is a seven-layer hybrid system: API layer (FastAPI with auth), document processing pipeline (ingestion, chunking, entity extraction), dual storage (Neo4j graph + Qdrant vectors with shared IDs), hybrid retrieval (vector-first with graph enrichment), memory management (Mem0 with three-tier isolation), LLM generation (LangChain orchestration with OpenAI), and memory update loop (extract and persist new context).

**Major components:**

1. **API Layer (FastAPI)** - Handles HTTP requests, JWT validation, session management, and query orchestration; async/await for non-blocking I/O with 1000+ concurrent user support
2. **Document Processing Pipeline** - Offline async pipeline for PDF/DOCX parsing, semantic chunking, entity extraction, and dual-write to both Neo4j and Qdrant with shared UUIDs
3. **Dual Storage (Neo4j + Qdrant)** - Neo4j stores entities, relationships, and graph structure for multi-hop reasoning; Qdrant stores vector embeddings for semantic search; linked via shared chunk IDs
4. **Hybrid Retrieval Layer** - Vector-first strategy: query Qdrant for top-K chunks, extract entity IDs, expand with Neo4j graph traversal, fuse contexts for enriched retrieval
5. **Memory Management (Mem0)** - Three-tier isolation: user-private memory (preferences), session-temporary memory (current conversation), tenant-shared memory (team knowledge); uses Neo4j for relationships + Qdrant for vectors
6. **LLM Generation Layer** - LangChain assembles context (documents + graph + memory), OpenAI GPT-4o generates responses, streaming for UX, strict prompts with "I don't know" fallback
7. **Memory Update Loop** - Post-response extraction of salient facts, update user/shared memory via Mem0, available for next query

**Critical patterns to follow:**
- **Vector-First, Graph-Enriched Retrieval**: Use Qdrant for fast semantic search (breadth), then Neo4j for relationship context (depth)
- **Shared ID Linkage**: Identical UUIDs in Neo4j and Qdrant enable efficient cross-referencing without data duplication
- **Three-Tier Memory Isolation**: Separate user-private, session-temporary, and tenant-shared memory spaces
- **Semantic Chunking**: Chunk by semantic boundaries (paragraphs, sections), not fixed character counts; 15-30% accuracy improvement
- **Query-Time Tenant Filtering**: Filter by tenant_id/user_id at query time in both Qdrant and Neo4j, not separate databases
- **Async Document Processing**: Decouple indexing from API requests using FastAPI BackgroundTasks; maintain responsiveness for large files

### Critical Pitfalls

Research identified 17 documented pitfalls across critical, moderate, and minor severity. The top 5 must be prevented in Phase 1-2 or they require major rework.

1. **Confusing RAG with Agent Memory** - Using RAG's semantic similarity for user memory causes agents to "forget" context (20-30% higher hallucination rates); prevent by using Mem0's hybrid approach (Neo4j for relationships + Qdrant for documents) and designing separate memory types from start
2. **Multi-Tenant Isolation Failures** - Single collection without proper filtering allows cross-user data access (critical security breach, GDPR/SOC2 violations); prevent with Qdrant v1.16+ tiered multitenancy, enforce tenant_id filtering in middleware, audit all queries
3. **Poor Chunking Strategy** - Fixed-size chunking (e.g., "split every 512 tokens") destroys semantic context (30-50% accuracy drop); prevent with semantic chunking that respects document structure, use layout-aware parsers like Docling for complex PDFs
4. **JWT Security Vulnerabilities** - Hardcoded secrets, no signature validation, accepting "none" algorithm enables full account takeover; prevent with strong secrets in env vars, short expiration (15 min), HTTPS only, never log full tokens
5. **Memory Deletion Leaving Orphaned Graph Data** - Mem0 `delete()` removes Qdrant vectors but leaves Neo4j nodes/relationships (known GitHub issue #3245); prevent with custom deletion logic, monitoring for orphans, periodic cleanup jobs, test deletion workflows thoroughly

**Additional critical pitfalls:**
- **LangGraph checkpoint bloat** - Storing large objects in state causes OOM errors; configure TTL, store IDs not content, implement sliding window for conversations
- **Embedding dimension mismatches** - Changing models mid-development requires recreating collections; lock embedding model early, centralize logic, validate dimensions at startup
- **Graph schema neglect** - No upfront schema leads to performance collapse at scale; design node/relationship types before ingestion, add indexes on critical properties
- **Context pollution** - Retrieving too many irrelevant chunks degrades LLM reasoning by 20-30%; implement re-ranking, set relevance thresholds, start with top-3 not top-10
- **No evaluation framework** - Quality degrades silently without metrics; implement RAGAS evaluation from Phase 1, track Precision@K, Recall@K, MRR

## Implications for Roadmap

Based on architecture dependencies and pitfall prevention, the roadmap should follow a strict sequential build with these phases:

### Phase 1: Foundation & Core RAG (Weeks 1-2)
**Rationale:** Authentication, database infrastructure, and basic document processing are prerequisites for all other components. Core RAG must work before adding memory complexity.

**Delivers:** Working document upload, parsing, embedding, storage, basic retrieval, and query answering with citations

**Addresses (table stakes):**
- PDF/DOCX upload and processing (use pymupdf4llm for speed)
- Semantic chunking (400-512 tokens, 15% overlap) - prevents pitfall #3
- Vector storage in Qdrant with tenant metadata
- Basic retrieval with source citations
- JWT authentication + anonymous sessions
- Database connections (Neo4j, Qdrant)

**Avoids (critical pitfalls):**
- Pitfall #3: Semantic chunking from start, not fixed-size
- Pitfall #7: Lock embedding model (text-embedding-3-small), validate dimensions
- Pitfall #8: Design Neo4j schema (nodes: User, Document, Chunk, Entity; relationships: OWNS, CONTAINS, MENTIONS, RELATES_TO)
- Pitfall #4: JWT security basics (env vars, signature validation, short expiration)

**Research flag:** Standard patterns. Skip phase-specific research.

### Phase 2: Multi-User Core & Memory Integration (Week 3)
**Rationale:** Multi-tenancy must be rock solid before user data ingestion. Memory layer sits on top of working retrieval. This phase addresses 3 critical security pitfalls.

**Delivers:** Secure multi-user isolation, Mem0 memory management, conversation persistence

**Uses (stack elements):**
- Mem0 SDK configured with Neo4j + Qdrant dual stores
- Query-time metadata filtering (tenant_id, user_id)
- Three-tier memory: user-private, session-temporary, tenant-shared

**Addresses (table stakes):**
- Multi-user isolation with document access control
- Session persistence and conversation history
- User-specific document collections

**Avoids (critical pitfalls):**
- Pitfall #1: Separate RAG (document knowledge) from memory (user context) architecturally
- Pitfall #4: Multi-tenant filtering in middleware, test with wrong tenant_id attempts
- Pitfall #2: Implement custom Neo4j deletion to prevent orphaned data
- Pitfall #5: Comprehensive JWT security (refresh tokens, HTTPS, audit logging)

**Research flag:** Needs research. Multi-tenant security patterns with Mem0 + dual stores are complex. Consider `/gsd:research-phase` for isolation testing strategies.

### Phase 3: UX & Streaming (Week 4)
**Rationale:** Core features work but UX needs polish for production feel. Streaming responses are table stakes in 2026.

**Delivers:** Streaming responses, document management UI, query history, progress indicators, "I don't know" fallback

**Addresses (table stakes):**
- Streaming responses via SSE (non-streaming feels broken)
- Document list/management CRUD operations
- Query history persistence
- Delete documents (cascade to both stores)
- "I don't know" responses (hallucination prevention)
- Progress indicators and loading states

**Avoids (pitfalls):**
- Pitfall #2: Test document deletion thoroughly (custom Neo4j cleanup)
- Pitfall #12: Set up basic evaluation framework (track MRR, precision)

**Research flag:** Standard patterns. Skip phase-specific research.

### Phase 4: LangGraph & Advanced Workflows (Week 5)
**Rationale:** Add LangGraph only when stateful workflows are needed (document comparison, iterative refinement). Earlier phases use LangChain for linear RAG.

**Delivers:** Document comparison, complex multi-step queries, workflow state management

**Implements (architecture component):**
- LangGraph for stateful workflows
- GraphRAG multi-hop reasoning with Neo4j
- Document comparison leveraging graph relationships

**Addresses (differentiators):**
- Multi-document comparison (competitive advantage - few do this well)
- Memory summarization to prevent context overflow
- Advanced query routing with workflow state

**Avoids (critical pitfalls):**
- Pitfall #6: Configure LangGraph checkpoint TTL (30 days active, 7 days completed)
- Pitfall #6: Never store document content in state (store IDs only)
- Pitfall #6: Implement sliding window for conversation history
- Pitfall #15: Use appropriate async patterns (profile before optimizing)

**Research flag:** Needs research. LangGraph with dual stores (Neo4j + Qdrant) for document comparison is complex. Consider `/gsd:research-phase` for workflow patterns.

### Phase 5: Differentiation Features (Week 6)
**Rationale:** Value-added features build on solid foundation. These create competitive advantage.

**Delivers:** Shared knowledge spaces, document summaries, highlighted citations, confidence scores, follow-up suggestions

**Addresses (differentiators):**
- Shared knowledge spaces (team collaboration)
- Document summarization (saves user time)
- Highlighted citations (superior to basic citations)
- Follow-up question suggestions (guides exploration)
- Confidence scores (builds trust)

**Avoids (pitfalls):**
- Pitfall #9: Implement re-ranking to reduce context pollution
- Pitfall #17: Document comparison scaling (chunk-level, not full documents)
- Pitfall #13: Store rich metadata for retrieval boost

**Research flag:** Standard patterns. Skip phase-specific research.

### Phase 6: Production Hardening (Week 7)
**Rationale:** Production-readiness is final step after all features built. Cannot optimize what doesn't exist.

**Delivers:** Observability, error handling, performance optimization, load testing

**Addresses (production requirements):**
- Logging, metrics, tracing (LangSmith or Prometheus)
- Error handling with fallbacks
- Sub-2s latency under load
- Graceful degradation when dependencies fail
- Rate limiting and cost protection

**Avoids (pitfalls):**
- Pitfall #12: Full evaluation framework (RAGAS, retrieval metrics)
- Pitfall #14: Plan for embedding model updates (version metadata)
- Pitfall #16: Neo4j vector index memory configuration
- Performance profiling to identify actual bottlenecks

**Research flag:** Standard patterns. Skip phase-specific research.

### Phase Ordering Rationale

**Sequential dependencies (must follow this order):**
1. Auth + Databases → All components need user/tenant context and storage
2. Basic RAG → Cannot add memory to non-working retrieval
3. Memory → Augments working RAG, cannot work standalone
4. Multi-tenancy → Must be solid before real user data
5. LangGraph → Requires stable RAG + memory foundation
6. Differentiation → Builds on stable core
7. Production hardening → Final layer after all features work

**Why this prevents pitfalls:**
- Phase 1 addresses chunking (#3), embedding dimensions (#7), schema design (#8) before data ingestion
- Phase 2 addresses multi-tenancy (#4), memory confusion (#1), JWT security (#5) before real users
- Phase 4 addresses checkpoint bloat (#6) when adding LangGraph, not after production issues
- Early evaluation (#12) catches quality degradation throughout development

**Parallel opportunities within phases:**
- Phase 1: Document parsers + embedding service (independent)
- Phase 1: Neo4j schema + Qdrant collections (different databases)
- Phase 3: UI components + API endpoints (different layers)
- Phase 6: Logging + metrics (independent observability)

### Research Flags

**Phases needing deeper research during planning:**
- **Phase 2 (Multi-user Core):** Multi-tenant isolation with Mem0 dual stores is complex. Qdrant tiered multitenancy (v1.16+) patterns, Neo4j query-time filtering enforcement, testing strategies for cross-tenant access attempts. Consider `/gsd:research-phase` for security validation.
- **Phase 4 (LangGraph Integration):** LangGraph workflow patterns for document comparison using GraphRAG, checkpoint configuration for production scale, state management with dual stores. Consider `/gsd:research-phase` for workflow design.

**Phases with standard patterns (skip research-phase):**
- **Phase 1 (Foundation):** FastAPI + JWT auth + basic RAG is well-documented with extensive 2026 tutorials
- **Phase 3 (UX & Streaming):** SSE streaming, document CRUD, progress indicators are standard FastAPI patterns
- **Phase 5 (Differentiation):** Document summarization, citations, confidence scores have established LangChain patterns
- **Phase 6 (Production Hardening):** Observability, error handling, load testing follow FastAPI deployment standards

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | **HIGH** | All technologies verified from official docs (FastAPI, Mem0, Neo4j, Qdrant, LangChain, OpenAI). Versions checked against PyPI/official releases as of Jan 2026. Production-proven stack. |
| Features | **HIGH** | Based on multiple 2026 production RAG reports, user expectations from ChatGPT/Claude baseline, and enterprise requirements. Table stakes vs differentiators clearly validated. |
| Architecture | **HIGH** | Hybrid architecture (graph + vector + memory) is 2026 production standard. Official documentation from Mem0, Neo4j GraphRAG, Qdrant examples. Performance benchmarks published. |
| Pitfalls | **HIGH** | Technology-specific issues verified from GitHub (Mem0 #3245, #3441), official docs (Neo4j memory config, Qdrant multitenancy), and 2026 security advisories (JWT vulnerabilities). Production post-mortems documented. |

**Overall confidence:** **HIGH**

All core technologies are mature (Neo4j, Qdrant, FastAPI) or purpose-built for this use case (Mem0). The hybrid architecture pattern is well-documented with official integration examples from Neo4j and Qdrant. Critical pitfalls are actively reported in GitHub issues and production incident reports, not theoretical concerns. The main complexity is integration orchestration, not individual technology risk.

### Gaps to Address

**Gap 1: Mem0 active development and known bugs**
- Mem0 has active issues (memory deletion incomplete #3245, embedding storage bugs #3441)
- **Handle during planning:** Plan custom deletion logic, monitor GitHub for patches, implement workarounds
- **Validation:** Test memory lifecycle (add, retrieve, update, delete) in Phase 2 with both stores
- **Confidence:** MEDIUM - Mem0 is actively maintained but relatively new (watch for breaking changes)

**Gap 2: LangGraph checkpoint performance at scale**
- Checkpoint bloat is well-documented but optimal TTL values are workload-dependent
- **Handle during planning:** Phase 4 must include checkpoint profiling with realistic data volumes
- **Validation:** Load test with 1000+ concurrent sessions, monitor database growth
- **Confidence:** MEDIUM - Pattern is known, but tuning requires empirical testing

**Gap 3: Document comparison implementation complexity**
- GraphRAG for multi-document comparison is differentiator but implementation sparse in docs
- **Handle during planning:** Phase 4 should research GraphRAG patterns specifically for comparison
- **Validation:** Prototype comparison workflow before full implementation
- **Confidence:** MEDIUM - Neo4j graph capabilities proven, but application pattern is custom

**Gap 4: Multi-tenant filtering enforcement**
- Query-time filtering is standard but enforcement across all access points requires vigilance
- **Handle during planning:** Phase 2 must include security audit of all query paths
- **Validation:** Penetration testing with crafted queries attempting cross-tenant access
- **Confidence:** HIGH (pattern known) but CRITICAL (security failure mode)

**Gap 5: Embedding model future-proofing**
- Current recommendation is text-embedding-3-small, but model landscape evolves
- **Handle during planning:** Version embeddings in metadata, plan re-embedding strategy upfront
- **Validation:** Test migration path with subset of data
- **Confidence:** LOW - Embedding model changes are unpredictable

**Gap 6: GraphRAG accuracy vs complexity tradeoff**
- Adding Neo4j graph enrichment adds 20-25% accuracy but significant complexity
- **Handle during planning:** Validate whether graph enrichment is worth complexity for your use case
- **Validation:** A/B test pure vector vs hybrid retrieval on eval set
- **Confidence:** MEDIUM - Benchmark data available but domain-specific

## Sources

### Primary (HIGH confidence)

**Official Documentation:**
- [Mem0 Official Docs - Introduction](https://docs.mem0.ai/introduction)
- [Mem0 Qdrant Integration](https://qdrant.tech/documentation/frameworks/mem0/)
- [Mem0 Research Paper (arXiv 2504.19413)](https://arxiv.org/abs/2504.19413)
- [Neo4j GraphRAG Documentation](https://neo4j.com/docs/neo4j-graphrag-python/current/user_guide_rag.html)
- [Integrate Qdrant and Neo4j to Enhance RAG Pipeline](https://neo4j.com/blog/developer/qdrant-to-enhance-rag-pipeline/)
- [GraphRAG with Qdrant and Neo4j](https://qdrant.tech/documentation/examples/graphrag-qdrant-neo4j/)
- [FastAPI OAuth2 with JWT (Official)](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/)
- [LangChain and LangGraph 1.0 Milestones](https://www.blog.langchain.com/langchain-langgraph-1dot0/)
- [Qdrant Multitenancy Guide](https://qdrant.tech/documentation/guides/multitenancy/)
- [Qdrant 1.16 - Tiered Multitenancy](https://qdrant.tech/blog/qdrant-1.16.x/)

**Package Versions (PyPI verified Jan 2026):**
- [neo4j PyPI v6.1.0](https://pypi.org/project/neo4j/)
- [qdrant-client PyPI v1.16.2](https://pypi.org/project/qdrant-client/)
- [langchain-openai PyPI v1.1.7](https://pypi.org/project/langchain-openai/)

**GitHub Issues (Active bugs):**
- [Memory deletion does not clean up Neo4j graph data · Issue #3245](https://github.com/mem0ai/mem0/issues/3245)
- [mem0.add() does not store embeddings in Qdrant · Issue #3441](https://github.com/mem0ai/mem0/issues/3441)

### Secondary (MEDIUM confidence)

**Industry Analysis (2026):**
- [Building Production RAG Systems in 2026: Complete Architecture Guide](https://brlikhon.engineer/blog/building-production-rag-systems-in-2026-complete-architecture-guide)
- [Learn How to Build Reliable RAG Applications in 2026](https://dev.to/pavanbelagatti/learn-how-to-build-reliable-rag-applications-in-2026-1b7p)
- [The Next Frontier of RAG: Enterprise Knowledge Systems 2026-2030](https://nstarxinc.com/blog/the-next-frontier-of-rag-how-enterprise-knowledge-systems-will-evolve-2026-2030/)
- [GraphRAG: How Lettria Unlocked 20% Accuracy Gains with Qdrant and Neo4j](https://qdrant.tech/blog/case-study-lettria-v2/)
- [Design a Secure Multitenant RAG Inferencing Solution](https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/secure-multitenant-rag)

**Security Analysis:**
- [JWT Vulnerabilities List: 2026 Security Risks & Mitigation Guide](https://redsentry.com/resources/blog/jwt-vulnerabilities-list-2026-security-risks-mitigation-guide)
- [Beyond the Secret: The Silent Risks of JWT and Machine Identity](https://medium.com/@instatunnel/beyond-the-secret-the-silent-risks-of-jwt-and-machine-identity-49bea4aa4547)

**RAG Patterns:**
- [RAG is not Agent Memory | Letta](https://www.letta.com/blog/rag-vs-agent-memory)
- [A Systematic Review of RAG Systems (arxiv.org)](https://arxiv.org/html/2507.18910v1)
- [23 RAG Pitfalls and How to Fix Them](https://www.nb-data.com/p/23-rag-pitfalls-and-how-to-fix-them)
- [Why 73% of RAG Systems Fail in Production](https://mindtechharbour.medium.com/why-73-of-rag-systems-fail-in-production-and-how-to-build-one-that-actually-works-part-1-6a888af915fa)

**Document Processing:**
- [I Tested 7 Python PDF Extractors (2025 Edition)](https://dev.to/onlyoneaman/i-tested-7-python-pdf-extractors-so-you-dont-have-to-2025-edition-akm)
- [Chunking Strategies to Improve Your RAG Performance](https://weaviate.io/blog/chunking-strategies-for-rag)

**Memory Management:**
- [Understanding Checkpointers, Databases, API Memory and TTL](https://support.langchain.com/articles/6253531756-understanding-checkpointers-databases-api-memory-and-ttl)
- [Collaborative Memory: Multi-User Memory Sharing in LLM Agents](https://arxiv.org/html/2505.18279v1)

### Tertiary (LOW confidence - needs validation)

**Benchmarks (domain-dependent):**
- OpenAI embedding accuracy improvements (54.9% vs 31.4% MIRACL score) - validated but domain-specific
- Mem0 26% accuracy improvement - from research paper but needs validation in your domain
- GraphRAG 20-25% accuracy gains - from case studies but workload-dependent
- 73% RAG production failure rate - from blog post, treat as directional not precise

**Emerging Patterns (2026):**
- Semantic chunking 15-30% improvement - multiple sources agree but range is wide
- Context pollution 20-30% degradation - Stanford research but specific to their test set
- Vector-first + graph enrichment - established pattern but implementation varies

---

**Research completed:** 2026-02-04
**Ready for roadmap:** Yes

**Next steps for orchestrator:**
1. Use phase structure from "Implications for Roadmap" as starting point
2. Flag Phase 2 and Phase 4 for potential deeper research during roadmap planning
3. Ensure requirements definition addresses critical pitfalls #1-5 in Phase 1-2
4. Validate multi-tenant security patterns before Phase 2 implementation
5. Plan checkpoint profiling and LangGraph testing for Phase 4
