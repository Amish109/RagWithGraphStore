# Domain Pitfalls: RAG with Graph + Vector Storage and Memory Management

**Domain:** RAG System with Mem0, Neo4j, Qdrant, LangGraph, LangChain
**Project Type:** Multi-user FastAPI document Q&A with persistent memory
**Researched:** 2026-02-04
**Confidence:** HIGH

## Critical Pitfalls

Mistakes that cause rewrites, major architectural issues, or production failures.

---

### Pitfall 1: Confusing RAG with Agent Memory

**What goes wrong:** Teams use RAG's semantic similarity for user memory storage, causing agents to "forget" context and lose conversation coherence. Memory isn't retrieved correctly because relationships, temporal context, and user state require different data structures than document retrieval.

**Why it happens:** RAG and memory management are conceptually conflated. Developers assume vector similarity works for both document retrieval and user state management.

**Consequences:**
- Agents fail to maintain conversation context across sessions
- User preferences and history don't persist correctly
- Memory retrieval returns irrelevant past interactions based on keyword similarity rather than temporal or relational relevance
- 20-30% higher hallucination rates when memory is implemented as pure RAG

**Prevention:**
- Use Mem0's hybrid approach: Neo4j for relationship/temporal memory + Qdrant for semantic document search
- Separate memory spaces: user profile memory (graph) vs. document knowledge (vector)
- Design memory schemas that capture relationships, not just text similarity
- Implement explicit memory types (user preferences, conversation history, document metadata)

**Detection:**
- Users report that the system "forgets" previous conversations
- Memory queries return topically similar but contextually irrelevant results
- Session continuity breaks when switching topics
- Testing shows agents can't answer "What did I ask you last week?"

**Phase to address:** Phase 1 (Foundation) - Architecture must separate memory types from the start

**Sources:**
- [RAG is not Agent Memory | Letta](https://www.letta.com/blog/rag-vs-agent-memory)
- [The Evolution from RAG to Agentic RAG to Agent Memory](https://www.leoniemonigatti.com/blog/from-rag-to-agent-memory.html)
- [Stop Pretending Your Agent Memory Isn't RAG](https://medium.com/asymptotic-spaghetti-integration/stop-pretending-your-agent-memory-isnt-rag-c2daf995d820)

---

### Pitfall 2: Memory Deletion Leaving Orphaned Graph Data

**What goes wrong:** When using Mem0 with Neo4j + Qdrant, calling `Memory.delete(memory_id)` only removes vectors from Qdrant and adds a history record, but fails to clean up corresponding nodes and relationships in Neo4j. This creates orphaned graph data that accumulates indefinitely.

**Why it happens:** Current Mem0 implementation has incomplete deletion logic across dual stores (GitHub issue #3245 as of 2026).

**Consequences:**
- Neo4j database grows unbounded with orphaned nodes
- Graph queries become slower as dead data accumulates
- Memory usage increases without bound
- Graph visualization shows deleted entities
- Eventual database corruption or performance collapse

**Prevention:**
- Implement custom deletion that explicitly removes Neo4j nodes/relationships
- Add monitoring for orphaned nodes (nodes with deletion history but still present)
- Schedule periodic cleanup jobs to detect and remove orphans
- Test deletion workflows thoroughly in staging
- Consider implementing soft-deletes with cleanup jobs instead of immediate deletion

**Detection:**
- Neo4j node count increases but vector count stays stable
- Graph queries show entities that should be deleted
- Query: `MATCH (n) WHERE NOT EXISTS((n)--()) RETURN count(n)` shows increasing orphans
- Memory metrics show Qdrant/Neo4j size diverging over time

**Phase to address:** Phase 2 (Multi-user Core) - Critical for GDPR/privacy compliance

**Sources:**
- [Memory deletion does not clean up Neo4j graph data · Issue #3245](https://github.com/mem0ai/mem0/issues/3245)
- [The Dispatch Report: GitHub Repo Analysis: mem0ai/mem0](https://thedispatch.ai/reports/6847/)

---

### Pitfall 3: Poor Chunking Strategy Torpedoes Retrieval Accuracy

**What goes wrong:** Using fixed chunk sizes (e.g., "split every 512 tokens") destroys semantic context and torpedoes retrieval accuracy regardless of reranking sophistication. Context boundaries are ignored, leading to retrieval of incomplete or meaningless fragments.

**Why it happens:** Most tutorials show simple fixed-size chunking as the default. Teams underestimate how critical chunking is to RAG performance.

**Consequences:**
- Retrieval returns partial paragraphs that lack context
- LLM receives fragments that don't answer the question
- Accuracy drops 30-50% compared to semantic chunking
- Tables, lists, and code blocks are split mid-structure
- Users get incomplete or nonsensical answers

**Prevention:**
- Use semantic chunking that respects document structure (paragraphs, sections, tables)
- For PDFs: Use layout-aware parsers like Docling (not PyPDF2)
- For DOCX: Preserve document hierarchy and embedded images
- Implement hybrid chunking: semantic boundaries + max token limits
- Test chunking strategies: fixed (baseline), semantic, sentence-window, document-summary
- Use metadata to track chunk context (parent document, section, page number)
- Chunk size recommendations: Start with 512 tokens, 50-100 token overlap for baseline testing

**Detection:**
- Retrieved chunks often lack context to answer queries
- Manual inspection shows chunks split mid-sentence or mid-table
- Evaluation shows low retrieval precision (<60%)
- Users complain answers are "incomplete" or "cut off"
- Similar queries return vastly different quality results

**Phase to address:** Phase 1 (Foundation) - Core ingestion pipeline

**Sources:**
- [23 RAG Pitfalls and How to Fix Them](https://www.nb-data.com/p/23-rag-pitfalls-and-how-to-fix-them)
- [Chunking Strategies to Improve Your RAG Performance | Weaviate](https://weaviate.io/blog/chunking-strategies-for-rag)
- [FAQ - Docling](https://docling-project.github.io/docling/faq/)
- [Chunking and Embedding Documents | RAG | Mastra Docs](https://mastra.ai/docs/rag/chunking-and-embedding)

---

### Pitfall 4: Multi-Tenant Isolation Failures

**What goes wrong:** Using a single Qdrant collection without proper tenant isolation allows users to retrieve other users' documents. Metadata filtering alone is insufficient if query validation is missing or bypassable.

**Why it happens:** Teams implement "one big bucket" indices with tenant_id filtering, but forget to enforce filtering at every access point. API bypasses or logic errors expose cross-tenant data.

**Consequences:**
- CRITICAL: Data breach - users see other users' private documents
- Regulatory violations (GDPR, HIPAA, SOC2)
- Complete loss of customer trust
- Legal liability
- Requires immediate disclosure and remediation

**Prevention:**
- **For small tenants (<1000 users):** Single collection + payload-based partitioning with `is_tenant=true` index parameter
- **For large tenants:** Use Qdrant v1.16+ tiered multitenancy (dedicated shards for large tenants, shared shards for small)
- Enforce tenant_id filtering in middleware, not in application code (defense in depth)
- Use separate collections for anonymous vs. authenticated users
- Implement query validation: reject queries missing tenant_id filter
- Add audit logging for all cross-tenant boundary queries
- Test: Attempt to query without tenant_id, with wrong tenant_id, with SQL injection patterns
- For Neo4j: Use similar node property filtering with mandatory WHERE clauses

**Detection:**
- Security audit shows queries without tenant filters
- Logs reveal successful queries across tenant boundaries
- Penetration testing finds filter bypass
- Users report seeing others' data (worst case)
- Monitoring shows queries returning data from multiple tenant_ids

**Phase to address:** Phase 2 (Multi-user Core) - MUST BE ROCK SOLID before user data ingestion

**Sources:**
- [Design a Secure Multitenant RAG Inferencing Solution](https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/secure-multitenant-rag)
- [Multitenancy - Qdrant](https://qdrant.tech/documentation/guides/multitenancy/)
- [Qdrant 1.16 - Tiered Multitenancy](https://qdrant.tech/blog/qdrant-1.16.x/)
- [Building Production RAG Systems in 2026](https://brlikhon.engineer/blog/building-production-rag-systems-in-2026-complete-architecture-guide)

---

### Pitfall 5: JWT Security Vulnerabilities in RAG Context

**What goes wrong:** RAG-specific attack: poisoning RAG data to manipulate AI agents into sending JWTs to attacker-controlled "logging services" for "debugging." Additionally, common JWT mistakes (hardcoded secrets, no signature validation, accepting "none" algorithm) expose the entire system.

**Why it happens:**
- 40%+ of breaches involve authentication flaws
- Teams underestimate RAG as an attack vector
- JWTs seem simple but have subtle security requirements
- Secrets are hardcoded for "convenience"

**Consequences:**
- Token theft allows full account takeover
- Attacker gains access to all user documents and memories
- Data exfiltration of multi-tenant data
- Privilege escalation (anonymous → authenticated → admin)
- Chain attacks: JWT → API access → data poisoning → further JWT theft

**Prevention:**
- **JWT Basics:**
  - Never accept "none" algorithm - always verify signature
  - Use strong secrets (32+ bytes, cryptographically random)
  - Store secrets in environment variables, never in code
  - Set short expiration (15 min access token, 7 day refresh token)
  - Implement refresh token rotation
  - Use HTTPS exclusively in production

- **RAG-Specific:**
  - Sanitize all ingested documents before storing
  - Validate retrieved context before sending to LLM
  - Monitor for unusual patterns (e.g., documents mentioning external logging services)
  - Implement prompt injection detection
  - Never log full JWTs (only last 4 characters)
  - For anonymous sessions: Generate single-use tokens, short TTL, no sensitive operations

- **2026 Best Practices:**
  - Treat every machine action as unique, time-bound event
  - Implement Zero Standing Privileges
  - Move toward ephemeral authentication where possible

**Detection:**
- Security scan shows hardcoded secrets
- Logs contain full JWT tokens
- API accepts tokens with "none" algorithm
- No token expiration validation
- Anonymous tokens have same privileges as authenticated
- Document content contains suspicious external URLs or logging instructions

**Phase to address:** Phase 1 (Foundation) + Phase 2 (Multi-user Core)

**Sources:**
- [JWT Vulnerabilities List: 2026 Security Risks & Mitigation Guide](https://redsentry.com/resources/blog/jwt-vulnerabilities-list-2026-security-risks-mitigation-guide)
- [Beyond the Secret: The Silent Risks of JWT and Machine Identity](https://medium.com/@instatunnel/beyond-the-secret-the-silent-risks-of-jwt-and-machine-identity-49bea4aa4547)
- [7 Ways to Avoid API Security Pitfalls when using JWT](https://42crunch.com/7-ways-to-avoid-jwt-pitfalls/)

---

### Pitfall 6: LangGraph Memory Checkpoint Bloat and OOM Errors

**What goes wrong:** LangGraph stores full application state at each checkpoint. Storing large binary objects (PDFs, images as base64) or running many sessions without TTL causes checkpoint bloat, memory errors, pod crashes, and eventual database exhaustion.

**Why it happens:**
- Teams store document content directly in LangGraph state for "convenience"
- No TTL configured on checkpoints (old sessions never expire)
- Memory leaks in custom code (caches that block garbage collection)
- Long conversations accumulate unbounded history

**Consequences:**
- Out of Memory (OOM) errors kill pods/processes
- Database disk space exhaustion
- Degraded performance as checkpoint tables grow
- Connection timeouts for long-running workflows
- System becomes unusable under normal load
- Recovery requires manual database cleanup

**Prevention:**
- **Never store large objects in state:**
  - Store document IDs/references, not content
  - Use external blob storage (S3) for PDFs/images
  - Keep state minimal: only IDs, short strings, small metadata

- **Configure TTL:**
  - Set checkpoint retention (e.g., 30 days for active, 7 days for completed)
  - Implement automatic cleanup jobs
  - Use exit durability mode for short-lived workflows

- **Conversation Memory:**
  - Implement sliding window (keep last N messages)
  - Summarize old conversation history
  - Don't store full context in every checkpoint
  - Most LLMs perform poorly over long contexts anyway

- **Database Configuration:**
  - If using PostgresSaver directly, don't hold connections for entire run duration
  - Use connection pooling
  - Monitor database size and query performance

- **Memory Leak Prevention:**
  - Avoid in-memory caches that block GC
  - Profile memory usage in staging
  - Set pod memory limits appropriate to workload

**Detection:**
- Pods/processes crash with OOM errors
- Database disk usage grows unbounded
- Query: `SELECT pg_size_pretty(pg_total_relation_size('checkpoints'))` shows excessive growth
- Checkpoint table has millions of rows for handful of users
- Performance degrades over days/weeks
- Logs show "connection timeout" or "database full" errors

**Phase to address:** Phase 3 (LangGraph Integration) - Before deploying to production

**Sources:**
- [Understanding Checkpointers, Databases, API Memory and TTL](https://support.langchain.com/articles/6253531756-understanding-checkpointers-databases-api-memory-and-ttl)
- [Memory overview - LangChain](https://docs.langchain.com/oss/python/langgraph/memory)
- [Agents log everything… except the reason they failed](https://forum.langchain.com/t/agents-log-everything-except-the-reason-they-failed-why/1421)

---

## Moderate Pitfalls

Mistakes that cause delays, technical debt, or significant rework.

---

### Pitfall 7: Embedding Dimension Mismatches

**What goes wrong:** Creating a Qdrant collection with 1536 dimensions, then switching to an embedding model that outputs 768 dimensions. Or vice versa. The vector store rejects insertions with cryptic errors.

**Why it happens:**
- Embedding model changed mid-development (e.g., OpenAI to Ollama)
- Different models used for indexing vs. querying
- Model upgrade changes dimension count
- Collection dimensionality set on first insert and locked forever

**Consequences:**
- Runtime errors during document ingestion or querying
- 400 Bad Request with dimension mismatch messages
- Need to recreate collections and re-embed all documents
- Hours/days of wasted debugging time

**Prevention:**
- **Document embedding model early:** Model name, version, dimension count
- **Centralize embedding logic:** Single function for all embeddings
- **Configuration validation at startup:**
  ```python
  assert len(embed("test")) == config.vector_dimension, "Dimension mismatch!"
  ```
- **Version lock dependencies:** Pin exact versions of embedding libraries
- **Test in CI:** Verify embedding dimensions match collection config
- **Migration planning:** If changing models, plan for re-embedding entire corpus

**Detection:**
- Errors like "Vector dimension 768 does not match index 1536"
- Insertion/query failures with dimension-related messages
- Unit tests fail after dependency update
- Different behavior between development (Ollama) and production (OpenAI)

**Phase to address:** Phase 1 (Foundation) - Prevent from start

**Sources:**
- [Dealing with Vector Dimension Mismatch](https://medium.com/@epappas/dealing-with-vector-dimension-mismatch-my-experience-with-openai-embeddings-and-qdrant-vector-20a6e13b6d9f)
- [Resolving Vector Dimension Mismatches in AI Workflows](https://dev.to/hijazi313/resolving-vector-dimension-mismatches-in-ai-workflows-47m)
- [mem0.add() does not store embeddings in Qdrant · Issue #3441](https://github.com/mem0ai/mem0/issues/3441)

---

### Pitfall 8: Graph Database Schema Neglect Causes Performance Collapse

**What goes wrong:** Not designing Neo4j schema upfront leads to inefficient queries, missing indexes, and eventual performance collapse. Complex traversals and multi-hop queries become unusably slow.

**Why it happens:**
- Teams start with "just store everything" mentality
- Graph flexibility misunderstood as "no schema needed"
- Performance issues only appear at scale (>100K nodes)
- Initial queries are simple and hide the problem

**Consequences:**
- Multi-hop relationship queries take seconds/minutes
- Graph becomes unusable for real-time retrieval
- Need to redesign schema after significant data ingestion
- Migration requires reprocessing all documents and memories
- Poor schema can't support planned features (e.g., document comparison needs relationship types defined upfront)

**Prevention:**
- **Design schema early:** Define node types, relationship types, and properties before ingestion
  - Example nodes: User, Document, Memory, Conversation, Entity
  - Example relationships: OWNS, CONTAINS, MENTIONS, RELATES_TO, FOLLOWS

- **Index critical properties:**
  - User.id, Document.id, Memory.id (unique constraints)
  - Document.tenant_id (for filtering)
  - Relationship timestamps (for temporal queries)

- **Relationship direction matters:**
  - Decide direction based on query patterns
  - Use consistent direction for same relationship types

- **Balance detail vs. complexity:**
  - Too granular: performance suffers, query logic complex
  - Too coarse: can't answer sophisticated queries

- **Test queries at expected scale:**
  - Generate synthetic data (1M+ nodes)
  - Run query patterns and measure performance
  - Identify slow queries and add indexes

**Detection:**
- Queries taking >1 second at <100K nodes
- EXPLAIN shows full scans without index usage
- Graph visualization is unstructured "hairball"
- Queries require complex multi-hop logic to find simple relationships
- New feature requirements reveal missing relationship types

**Phase to address:** Phase 1 (Foundation) - Schema design is architectural

**Sources:**
- [GraphRAG & Knowledge Graphs: Making Your Data AI-Ready for 2026](https://flur.ee/fluree-blog/graphrag-knowledge-graphs-making-your-data-ai-ready-for-2026/)
- [What Is GraphRAG? - Neo4j](https://neo4j.com/blog/genai/what-is-graphrag/)
- [Graph RAG vs vector RAG: 3 differences, pros and cons](https://www.instaclustr.com/education/retrieval-augmented-generation/graph-rag-vs-vector-rag-3-differences-pros-and-cons-and-how-to-choose/)

---

### Pitfall 9: Context Pollution Degrading LLM Reasoning

**What goes wrong:** Retrieving too many irrelevant chunks (5-10 documents where 3+ are tangentially related) pollutes the LLM context, degrading reasoning performance by 20-30%. RAG introduces noise that harms model performance.

**Why it happens:**
- Default retrieval retrieves top-K by similarity (e.g., top-10) without quality filtering
- No re-ranking or relevance threshold
- Vector similarity doesn't equal semantic relevance
- "More context is better" assumption

**Consequences:**
- LLM outputs become less accurate despite "more information"
- Increased hallucination rates
- Slower inference (longer context)
- Higher costs (more tokens processed)
- Users get answers that mix irrelevant information

**Prevention:**
- **Implement re-ranking:** Use cross-encoder models after initial retrieval to score relevance
- **Set relevance thresholds:** Only include chunks with similarity >0.7 (tune based on evaluation)
- **Limit retrieval count:** Start with top-3, not top-10
- **Use metadata filtering:** Pre-filter by document type, date, tenant before similarity search
- **Hybrid search:** Combine semantic (vector) + keyword (BM25) for better precision
- **Context compression:** Summarize or extract key sentences from retrieved chunks
- **Evaluation-driven tuning:** Measure precision/recall at different K values

**Detection:**
- Users report answers include irrelevant information
- Manual review shows retrieved chunks are off-topic
- Evaluation metrics show low precision (<60%)
- Increasing retrieval count decreases answer quality
- LLM outputs mention "based on the documents provided..." but answer is generic

**Phase to address:** Phase 4 (Advanced RAG) - Optimization phase

**Sources:**
- [23 RAG Pitfalls and How to Fix Them](https://www.nb-data.com/p/23-rag-pitfalls-and-how-to-fix-them)
- [Stanford's Warning: Your RAG System Is Broken](https://medium.com/@sameerizwan3/stanfords-warning-your-rag-system-is-broken-and-how-to-fix-it-c28a770fe7fe)
- [Building Production RAG Systems in 2026](https://brlikhon.engineer/blog/building-production-rag-systems-in-2026-complete-architecture-guide)

---

### Pitfall 10: Document Processing Pipeline Errors (PDF/DOCX)

**What goes wrong:**
- DOCX/HTML image extraction fails silently
- PDF table structures are destroyed during parsing
- Embedded images ignored, losing critical context
- Token length warnings flood logs
- ImportError conflicts between opencv-python and opencv-python-headless

**Why it happens:**
- Using basic parsers (PyPDF2, python-docx) that don't handle complex documents
- Not testing on real-world documents (tables, images, multi-column layouts)
- Dependency conflicts in document processing libraries

**Consequences:**
- Users upload documents but key information is lost
- Tables become unreadable text blobs
- Images with critical diagrams are invisible to RAG
- System appears to work but provides incomplete answers
- Users lose trust when answers ignore obvious document content

**Prevention:**
- **Use production-grade parsers:**
  - Docling for PDF/DOCX/PPTX/HTML (layout-aware, OCR support)
  - Not PyPDF2 or basic libraries

- **Handle embedded content:**
  - Extract and process images separately
  - Use vision models for diagram/chart understanding
  - Preserve table structures with markdown or HTML

- **Test on diverse documents:**
  - Multi-column layouts
  - Complex tables with merged cells
  - Documents with embedded images
  - Scanned PDFs requiring OCR

- **Dependency management:**
  - Pin exact versions to avoid conflicts
  - Use virtual environments
  - Resolve opencv conflicts before deployment

- **Chunk with structure awareness:**
  - Keep tables together
  - Keep image captions with images
  - Preserve hierarchical document structure

**Detection:**
- Manual review shows missing content from PDFs
- Tables rendered as garbled text
- Images mentioned in text but not in retrieved context
- Logs show ImportError or library conflicts
- Users complain about "incomplete" answers from clearly documented topics

**Phase to address:** Phase 1 (Foundation) - Core ingestion

**Sources:**
- [Unable to Use Mem0 with Ollama Locally · Issue #2030](https://github.com/mem0ai/mem0/issues/2030)
- [How to configure Docling Pipeline for DOCX and HTML · Issue #1347](https://github.com/docling-project/docling/issues/1347)
- [FAQ - Docling](https://docling-project.github.io/docling/faq/)
- [Advanced chunking for PDF/Word with embedded images](https://medium.com/@saptarshi701/advanced-chunking-for-pdf-word-with-embedded-images-using-regular-parsers-and-gpt-4o-7f0d5eb97052)

---

### Pitfall 11: Hybrid Storage Synchronization Complexity

**What goes wrong:** Managing dual stores (Neo4j + Qdrant) creates synchronization challenges. Updates to one store may fail while the other succeeds, creating inconsistent state. Rollback logic is complex or missing.

**Why it happens:**
- No distributed transaction support across Neo4j and Qdrant
- Mem0 abstraction hides complexity
- Teams don't plan for partial failures
- "Happy path" testing doesn't reveal issues

**Consequences:**
- Data inconsistency: vector exists but graph doesn't (or vice versa)
- Queries return incomplete results
- Difficult to debug which store is authoritative
- Manual intervention required to fix inconsistencies
- Production incidents during store maintenance

**Prevention:**
- **Write-ahead logging:** Log intent before dual writes
- **Implement compensating transactions:** If second write fails, rollback first
- **Idempotency:** Make operations replayable (use UUIDs, not auto-increment)
- **Monitoring:** Alert when store sizes diverge significantly
- **Background reconciliation:** Periodic job to detect and fix inconsistencies
- **Graceful degradation:** If one store is down, queue operations or return partial results
- **Use Mem0 carefully:** Understand what it does vs. what you need to handle

**Detection:**
- Qdrant collection count != Neo4j node count (for same entity type)
- Queries to one store succeed, queries to other fail for same ID
- Logs show partial write failures
- Manual data inspection reveals missing relationships or vectors
- Users report inconsistent search results

**Phase to address:** Phase 2 (Multi-user Core) - Before production load

**Sources:**
- [Memory deletion does not clean up Neo4j graph data · Issue #3245](https://github.com/mem0ai/mem0/issues/3245)
- [Hybrid RAG in the Real World](https://community.netapp.com/t5/Tech-ONTAP-Blogs/Hybrid-RAG-in-the-Real-World-Graphs-BM25-and-the-End-of-Black-Box-Retrieval/ba-p/464834)
- [HybridRAG: Integrating Knowledge Graphs and Vector Retrieval](https://arxiv.org/html/2408.04948v1)

---

## Minor Pitfalls

Mistakes that cause annoyance but are fixable without major rework.

---

### Pitfall 12: No Evaluation Framework = Silent Quality Degradation

**What goes wrong:** Building RAG without automated evaluation means quality issues go undetected. Manual testing misses edge cases. Changes break performance without anyone noticing.

**Why it happens:**
- "It works in my tests" mentality
- Evaluation seems like extra work
- Not clear what metrics to track

**Consequences:**
- Quality degrades over time (embeddings change, models update, data drifts)
- Can't compare improvement experiments
- Bugs reach production
- No objective measure of system performance

**Prevention:**
- **Implement evaluation from Phase 1:**
  - Retrieval metrics: Precision@K, Recall@K, MRR (Mean Reciprocal Rank)
  - Generation metrics: RAGAS, context precision, faithfulness, answer relevance
  - Create gold standard test set (50-100 Q&A pairs)

- **Automated testing:**
  - Run evaluation on every PR
  - Alert on metric regression
  - Track metrics over time in dashboard

- **Not just final answer:**
  - Evaluate retrieval quality separately
  - Catch retrieval problems before generation

**Detection:**
- No test coverage for RAG pipeline
- Changes deployed without quality measurement
- User complaints are first sign of quality issues

**Phase to address:** Phase 1 (Foundation) - Set up early

**Sources:**
- [RAG Evaluation: 2026 Metrics and Benchmarks](https://labelyourdata.com/articles/llm-fine-tuning/rag-evaluation)
- [RAG Monitoring Tools Benchmark in 2026](https://research.aimultiple.com/rag-monitoring/)

---

### Pitfall 13: Ignoring Metadata for Retrieval Boost

**What goes wrong:** Relying solely on text similarity ignores metadata that could dramatically improve relevance (document type, upload date, author, tags).

**Why it happens:** Focus on embeddings overshadows traditional structured filtering.

**Consequences:**
- Lower retrieval precision
- Can't filter by user-specific requirements ("only PDFs from last month")
- Missed opportunity for hybrid search improvements

**Prevention:**
- Store metadata: document_type, upload_date, author, tenant_id, tags, file_size
- Use metadata in queries: Pre-filter before similarity search
- Allow users to specify metadata filters
- Index metadata fields in Qdrant with `is_tenant=true` for tenant_id

**Phase to address:** Phase 1 (Foundation) - Schema design

---

### Pitfall 14: Stale Embeddings After Model Updates

**What goes wrong:** Upgrading embedding models or changing data leaves old embeddings in place. New queries use new embeddings, old documents have old embeddings. Similarity comparisons are invalid.

**Why it happens:** No re-embedding strategy planned.

**Consequences:**
- Retrieval accuracy drops mysteriously
- New documents rank differently than old
- Inconsistent search results

**Prevention:**
- Version embeddings (metadata: `embedding_model_version: "text-embedding-3-small-v1"`)
- Plan re-embedding strategy before model changes
- Background job to re-embed documents in batches
- Hybrid approach during migration (query both old and new, favor new)

**Phase to address:** Phase 4 (Advanced RAG) - Operational concern

**Sources:**
- [RAG at Scale: How to Build Production AI Systems in 2026](https://redis.io/blog/rag-at-scale/)

---

### Pitfall 15: FastAPI Async/Sync Confusion Killing Performance

**What goes wrong:** Mixing async/sync incorrectly, calling synchronous database operations from async endpoints, or making everything async without understanding when it helps.

**Why it happens:**
- async/await is trendy but poorly understood
- SQLAlchemy, Neo4j, Qdrant clients have both sync and async versions
- Tutorials show simple cases, not hybrid scenarios

**Consequences:**
- High latency despite "async" everywhere
- Blocked event loop causes slow responses under load
- ThreadPoolExecutor overhead without benefit

**Prevention:**
- Use async for I/O-bound operations (DB, API calls, file I/O)
- Keep CPU-bound work in sync functions (embedding, chunking) or use `run_in_executor()`
- Use async clients: asyncpg, motor, httpx
- Profile to find actual bottlenecks before optimizing
- Don't assume async = fast (measure!)

**Phase to address:** Phase 3 (LangGraph Integration) - Performance optimization

**Sources:**
- [FastAPI Performance Tuning & Caching Strategy 101](https://blog.greeden.me/en/2026/02/03/fastapi-performance-tuning-caching-strategy-101-a-practical-recipe-for-growing-a-slow-api-into-a-lightweight-fast-api/)
- [Building High-Performance APIs with Haystack, Bytewax and FastAPI](https://bytewax.io/blog/rag-app-case-study-haystack-bytewax-fastapi/)

---

### Pitfall 16: Neo4j Vector Index Memory Misconfiguration

**What goes wrong:** Insufficient memory allocated for Neo4j's Lucene-based vector indexes causes page swapping and disk I/O, dramatically degrading search performance.

**Why it happens:** Default memory settings are too low for production vector workloads.

**Consequences:**
- Vector search takes seconds instead of milliseconds
- System becomes unresponsive under load
- Graph queries are fine but vector queries timeout

**Prevention:**
- Configure vector index memory allocation in neo4j.conf
- Increase lucene memory for vector indexes based on corpus size
- Monitor swap usage and disk I/O
- Consider quantization for better performance (slight accuracy tradeoff)

**Phase to address:** Phase 1 (Foundation) - Infrastructure setup

**Sources:**
- [Vector index memory configuration - Neo4j](https://neo4j.com/docs/operations-manual/current/performance/vector-index-memory-configuration/)
- [Why Vector Search Didn't Work for Your RAG Solution](https://neo4j.com/blog/developer/why-vector-search-didnt-work-rag/)

---

### Pitfall 17: Document Comparison Scaling Issues

**What goes wrong:** Implementing document comparison naively (retrieve full documents, compare in memory) causes memory spikes and slow response times as document size/count grows.

**Why it happens:** "Just load and compare" is obvious approach but doesn't scale.

**Consequences:**
- Comparison timeouts for large documents
- OOM errors when comparing many documents
- User frustration with slow feature

**Prevention:**
- Use vector similarity for initial filtering (find similar documents)
- Compare summaries or key sections, not full text
- Chunk-level comparison with aggregation
- Stream results instead of loading everything
- Set hard limits (max documents to compare, max size per document)
- Cache comparison results

**Phase to address:** Phase 5 (Advanced Features) - Document comparison feature

**Sources:**
- [RAG at Scale: How to Build Production AI Systems in 2026](https://redis.io/blog/rag-at-scale/)
- [15 Best Open-Source RAG Frameworks in 2026](https://www.firecrawl.dev/blog/best-open-source-rag-frameworks)

---

## Phase-Specific Warnings

| Phase | Likely Pitfall | Mitigation |
|-------|---------------|------------|
| Phase 1: Foundation | Confusing RAG with memory (#1), Poor chunking (#3), Embedding dimensions (#7), Schema neglect (#8) | Design separate memory/knowledge stores, semantic chunking, lock embedding model, design Neo4j schema |
| Phase 2: Multi-user Core | Multi-tenant isolation (#4), Memory deletion bugs (#2), JWT vulnerabilities (#5) | Tiered multitenancy, test deletion workflows, JWT security audit |
| Phase 3: LangGraph Integration | Checkpoint bloat (#6), Async/sync confusion (#15) | Configure TTL, profile memory usage, use appropriate async patterns |
| Phase 4: Advanced RAG | Context pollution (#9), Stale embeddings (#14), No evaluation (#12) | Implement re-ranking, version embeddings, set up evaluation framework |
| Phase 5: Advanced Features | Document comparison scaling (#17), Graph query performance (#8) | Chunk-level comparison, optimize Neo4j indexes and queries |

---

## Technology-Specific Warnings

### Mem0
- **Active bugs:** Memory deletion incomplete (issue #3245), Ollama embedding storage (issue #3441), Qdrant Cloud connection errors (issue #3915)
- **Recommendation:** Test deletion workflows thoroughly, monitor for orphaned data, consider implementing custom deletion logic
- **Confidence:** MEDIUM - Active development, issues being tracked

### Neo4j + Vector Search
- **Performance:** Memory configuration critical, quantization tradeoffs
- **Schema:** Design upfront, add indexes before scale
- **Recommendation:** Don't rely on "schemaless" flexibility
- **Confidence:** HIGH - Well-documented, mature technology

### Qdrant
- **Multitenancy:** Use tiered approach (v1.16+) for mixed tenant sizes
- **Dimensions:** Locked on first insert, plan carefully
- **Performance:** `is_tenant=true` parameter significantly improves tenant filtering
- **Confidence:** HIGH - Official documentation, production-proven

### LangChain/LangGraph
- **Memory:** Checkpoint bloat is primary concern
- **Logging:** Don't log everything, causes memory bloat
- **Complexity:** Adds significant operational overhead
- **Recommendation:** Only use if multi-step workflows genuinely benefit
- **Confidence:** HIGH - Official documentation and community reports

### FastAPI
- **Performance:** Async/sync mixing is common pitfall
- **Auth:** JWT handling requires careful security consideration
- **Recommendation:** Profile before optimizing, don't assume async = fast
- **Confidence:** HIGH - Mature ecosystem, well-understood patterns

---

## Summary: Top 5 "Must Address Early" Pitfalls

1. **Confusing RAG with memory (#1)** - Architectural mistake requiring fundamental redesign if wrong
2. **Multi-tenant isolation failures (#4)** - Security critical, causes data breaches
3. **Poor chunking strategy (#3)** - Affects all downstream quality, hard to fix after ingestion
4. **JWT security vulnerabilities (#5)** - Entire system compromise
5. **Memory deletion leaving orphaned data (#2)** - Accumulates silently until system fails

**These five must be prevented in Phase 1-2. Fixing them later requires major rework or causes production incidents.**

---

## Sources Summary

**HIGH Confidence Sources (Official Documentation & GitHub Issues):**
- Mem0 GitHub Issues (active bug reports)
- Neo4j Official Documentation (vector index, performance)
- Qdrant Official Documentation (multitenancy, best practices)
- LangChain/LangGraph Official Documentation (memory, checkpoints)
- FastAPI Official Documentation (security, async)

**MEDIUM Confidence Sources (Industry Analysis & Recent Blogs):**
- Recent 2026 blog posts from practitioners (Redis, Likhon, NetApp)
- Security analysis from established vendors (Curity, Red Sentry)
- Academic papers (HybridRAG, RAG surveys)

**Key Insight:** The pitfalls documented here are not theoretical. They're actively reported in GitHub issues (Mem0 bugs), security advisories (JWT vulnerabilities), and production post-mortems (multi-tenant breaches, memory leaks). This research has HIGH confidence for technology-specific issues and MEDIUM confidence for operational patterns.
