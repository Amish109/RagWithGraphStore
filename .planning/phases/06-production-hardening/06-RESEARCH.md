# Phase 6: Production Hardening - Research

**Researched:** 2026-02-05
**Domain:** Observability, Performance, Error Handling, Load Testing, Rate Limiting, RAG Evaluation
**Confidence:** HIGH

## Summary

Phase 6 focuses on making the RAG system production-ready through five key areas: observability (logging, metrics, tracing), performance optimization, error handling with resilience patterns, load testing, and RAG-specific evaluation metrics. The existing FastAPI codebase already has basic error handling (from Phase 3) and Redis infrastructure (from Phase 2), which provides a solid foundation.

The standard approach for Python/FastAPI production hardening centers on OpenTelemetry for distributed tracing, structlog for structured logging, prometheus-fastapi-instrumentator for metrics, slowapi for rate limiting, Locust for load testing, and RAGAs for retrieval evaluation. These tools integrate well with the existing async FastAPI + Redis stack.

The key challenge is balancing observability depth with performance overhead. The system must maintain sub-2-second response times (Success Criteria #1) while adding comprehensive monitoring. The research identified that OpenTelemetry automatic instrumentation adds minimal overhead, and async logging with structlog prevents blocking.

**Primary recommendation:** Use OpenTelemetry for unified observability with Prometheus metrics and structlog for structured logging. Implement rate limiting with slowapi backed by existing Redis. Use Locust for Python-native load testing. Add RAGAs evaluation for retrieval quality metrics.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| opentelemetry-instrumentation-fastapi | 0.50+ | Automatic HTTP tracing | Official OpenTelemetry package, zero-code instrumentation |
| prometheus-fastapi-instrumentator | 7.1.0 | Prometheus metrics | 234K weekly downloads, modular metrics design |
| structlog | 25.5.0 | Structured logging | Async support, contextvar propagation, JSON output |
| slowapi | 0.1.9+ | Rate limiting | Built for FastAPI/Starlette, supports Redis backend |
| tenacity | 9.0.0 | Retry logic | Standard for Python resilience, exponential backoff support |
| circuitbreaker | 2.0.0 | Circuit breaker pattern | Python implementation, async support |
| locust | 2.43.2 | Load testing | Python-native, greenlet-based, distributed support |
| ragas | 0.2.0+ | RAG evaluation | Industry standard for RAG metrics, LangChain integration |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| opentelemetry-sdk | 1.29+ | Telemetry SDK | Required for OpenTelemetry setup |
| opentelemetry-exporter-otlp | 1.29+ | OTLP exporter | Export traces to Jaeger/Tempo/etc |
| opentelemetry-instrumentation-redis | 0.50+ | Redis tracing | Trace Redis operations |
| opentelemetry-instrumentation-httpx | 0.50+ | HTTP client tracing | Trace outbound HTTP calls |
| limits | 3.15+ | Rate limit storage | Backend for slowapi (Redis async support) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| structlog | loguru | loguru simpler but less async-optimized |
| Locust | k6 | k6 faster but JavaScript-based, less Python integration |
| prometheus-fastapi-instrumentator | starlette-prometheus | Less feature-rich, fewer built-in metrics |
| slowapi | fastapi-limiter | slowapi more mature, better Redis support |

**Installation:**
```bash
pip install \
  opentelemetry-instrumentation-fastapi \
  opentelemetry-sdk \
  opentelemetry-exporter-otlp \
  opentelemetry-instrumentation-redis \
  opentelemetry-instrumentation-httpx \
  prometheus-fastapi-instrumentator \
  structlog \
  slowapi \
  tenacity \
  circuitbreaker \
  locust \
  ragas
```

## Architecture Patterns

### Recommended Project Structure
```
backend/app/
├── core/
│   ├── logging.py          # structlog configuration
│   ├── telemetry.py        # OpenTelemetry setup
│   ├── metrics.py          # Prometheus metrics definitions
│   ├── rate_limiter.py     # slowapi configuration
│   └── resilience.py       # circuit breaker, retry patterns
├── middleware/
│   └── observability.py    # Request correlation, timing middleware
└── evaluation/
    └── rag_metrics.py      # RAGAs integration for evaluation
```

### Pattern 1: OpenTelemetry Automatic Instrumentation
**What:** Single-line instrumentation that captures all HTTP requests, traces, and context propagation
**When to use:** Always - minimal overhead, maximum visibility
**Example:**
```python
# Source: OpenTelemetry FastAPI docs
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# Configure tracer
trace.set_tracer_provider(TracerProvider())
tracer_provider = trace.get_tracer_provider()
tracer_provider.add_span_processor(
    BatchSpanProcessor(OTLPSpanExporter(endpoint="http://localhost:4317"))
)

# Instrument FastAPI - this single line enables automatic tracing
FastAPIInstrumentor.instrument_app(app)
```

### Pattern 2: Structured Logging with Context
**What:** JSON-structured logs with request correlation IDs propagated via contextvars
**When to use:** All logging - enables log aggregation and trace correlation
**Example:**
```python
# Source: structlog documentation
import structlog
from contextvars import ContextVar

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")

def configure_structlog():
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

# Usage in endpoint
logger = structlog.get_logger()
await logger.ainfo("query_started", query=query, user_id=user_id)
```

### Pattern 3: Rate Limiting with Redis Backend
**What:** Per-user/IP rate limits stored in Redis for distributed consistency
**When to use:** All API endpoints, especially resource-intensive ones like /query
**Example:**
```python
# Source: slowapi + limits documentation
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Initialize with async Redis storage
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="async+redis://localhost:6379/0"
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Apply to endpoint
@router.post("/query")
@limiter.limit("10/minute")  # 10 requests per minute
async def query_documents(request: Request, ...):
    pass
```

### Pattern 4: Circuit Breaker for External Services
**What:** Prevent cascading failures when OpenAI/Neo4j/Qdrant are unavailable
**When to use:** All external service calls
**Example:**
```python
# Source: circuitbreaker PyPI
from circuitbreaker import circuit

@circuit(failure_threshold=5, recovery_timeout=30)
async def call_openai_embedding(text: str):
    """Circuit breaks after 5 failures, waits 30s before retry."""
    return await openai_client.embeddings.create(...)
```

### Pattern 5: Retry with Exponential Backoff
**What:** Automatic retry for transient failures with jitter to prevent thundering herd
**When to use:** Network calls, database operations
**Example:**
```python
# Source: tenacity documentation
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((TimeoutError, ConnectionError))
)
async def embed_text(text: str):
    """Retries up to 3 times with exponential backoff."""
    return await embedding_service.embed(text)
```

### Anti-Patterns to Avoid
- **Synchronous logging in async code:** Use structlog's async methods (ainfo, adebug) to prevent blocking
- **Unbounded rate limit storage:** Always use TTL on rate limit keys (handled by slowapi automatically)
- **Circuit breaker without fallback:** Always provide graceful degradation when circuit opens
- **Metrics without labels:** Always include user_id, endpoint, method labels for debugging
- **Logging sensitive data:** Never log tokens, passwords, or full request bodies

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Request tracing | Custom middleware with trace IDs | OpenTelemetry | Auto-propagates context, integrates with all components |
| Prometheus metrics | Manual Counter/Histogram tracking | prometheus-fastapi-instrumentator | Auto-instruments all endpoints, handles histograms correctly |
| Rate limiting | Redis INCR with custom TTL logic | slowapi + limits | Handles race conditions, sliding windows, multiple strategies |
| Retry logic | try/except loops with sleep | tenacity | Handles backoff, jitter, exception filtering properly |
| Circuit breaker | Custom failure counting | circuitbreaker | State machine is complex, edge cases handled |
| Load testing | Custom concurrent request scripts | Locust | Handles distribution, reporting, real-time metrics |
| RAG evaluation | Custom precision/recall calculations | RAGAs | Validated metrics, LangChain integration |

**Key insight:** Production hardening tools handle edge cases that are easy to miss: race conditions in rate limiting, backoff jitter in retries, distributed trace context propagation, and statistically valid metric bucketing.

## Common Pitfalls

### Pitfall 1: Blocking Async Event Loop with Sync Logging
**What goes wrong:** Synchronous logging calls block the async event loop, degrading throughput under load
**Why it happens:** Default Python logging is synchronous; structlog needs explicit async configuration
**How to avoid:** Use structlog's async methods (`await logger.ainfo()`) or configure thread pool execution
**Warning signs:** High latency variance, p99 latency spikes during log-heavy operations

### Pitfall 2: Missing Trace Context in Background Tasks
**What goes wrong:** Background tasks lose trace context, making debugging impossible
**Why it happens:** FastAPI BackgroundTasks run after response, outside request context
**How to avoid:** Explicitly copy trace context into background tasks
**Warning signs:** Orphan spans in trace visualization, gaps in distributed traces

### Pitfall 3: Rate Limit Key Collision
**What goes wrong:** Different users share rate limits, or authenticated users inherit anonymous limits
**Why it happens:** Using only IP address for rate limit key; not accounting for user identity
**How to avoid:** Composite key: `f"{user_id}:{ip_address}"` for authenticated, IP only for anonymous
**Warning signs:** Authenticated users getting rate limited unexpectedly, shared IP users (corporate) exhausting limits

### Pitfall 4: Circuit Breaker Flapping
**What goes wrong:** Circuit opens and closes rapidly, causing inconsistent behavior
**Why it happens:** Recovery timeout too short, or threshold too low for normal variance
**How to avoid:** Set failure threshold >= 5, recovery timeout >= 30s; use half-open state properly
**Warning signs:** Circuit state changing multiple times per minute in logs

### Pitfall 5: Metrics Cardinality Explosion
**What goes wrong:** Prometheus runs out of memory, scrape times increase exponentially
**Why it happens:** High-cardinality labels like user_id, query text, or request_id in metrics
**How to avoid:** Use bounded label values; bucket user IDs if needed; never log unbounded strings as labels
**Warning signs:** Prometheus memory growth, slow /metrics endpoint response

### Pitfall 6: Load Test Not Matching Production Traffic
**What goes wrong:** System passes load tests but fails in production
**Why it happens:** Synthetic tests use uniform patterns; real traffic has bursts, varied payloads
**How to avoid:** Model realistic user behavior in Locust; include authentication, varied query lengths
**Warning signs:** Production latency 2x+ load test latency, different failure modes

### Pitfall 7: RAG Evaluation Without Ground Truth
**What goes wrong:** Evaluation metrics are meaningless or misleading
**Why it happens:** Faithfulness/correctness require reference answers; retrieval metrics need relevance labels
**How to avoid:** Create evaluation dataset with human-labeled ground truth; start small (50-100 samples)
**Warning signs:** All metrics near 1.0 (too easy) or widely varying (unstable)

## Code Examples

Verified patterns from official sources:

### Prometheus Metrics Setup
```python
# Source: prometheus-fastapi-instrumentator GitHub
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_fastapi_instrumentator.metrics import Info
from prometheus_client import Counter

# Custom metric for LLM token usage
llm_tokens = Counter(
    "llm_tokens_total",
    "Total LLM tokens used",
    labelnames=("model", "operation")
)

def custom_llm_metric() -> Callable[[Info], None]:
    def instrumentation(info: Info) -> None:
        # Called for every request
        pass
    return instrumentation

# In main.py
instrumentator = Instrumentator(
    excluded_handlers=["/metrics", "/health"],
    should_group_status_codes=True,
)
instrumentator.add(custom_llm_metric())
instrumentator.instrument(app).expose(app, include_in_schema=False)
```

### Rate Limiting with User Identity
```python
# Source: slowapi + limits documentation
from slowapi import Limiter
from fastapi import Request

def get_rate_limit_key(request: Request) -> str:
    """Composite key: user_id for authenticated, IP for anonymous."""
    # Check for authenticated user in request state
    user = getattr(request.state, "user", None)
    if user and not user.is_anonymous:
        return f"user:{user.id}"
    return f"ip:{request.client.host}"

limiter = Limiter(
    key_func=get_rate_limit_key,
    storage_uri=f"async+redis://{settings.REDIS_URL.replace('redis://', '')}"
)

# Different limits per endpoint
@router.post("/query")
@limiter.limit("20/minute")
async def query_documents(...): pass

@router.post("/documents/upload")
@limiter.limit("5/minute")  # More restrictive for expensive operations
async def upload_document(...): pass
```

### Locust Load Test for RAG Endpoint
```python
# Source: Locust documentation
from locust import HttpUser, task, between

class RAGUser(HttpUser):
    wait_time = between(1, 3)  # 1-3 seconds between requests

    def on_start(self):
        """Login and store token."""
        response = self.client.post("/api/v1/auth/login", data={
            "username": "test@example.com",
            "password": "testpassword"
        })
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}

    @task(3)  # 3x more likely than upload
    def query_documents(self):
        """Simulate document query."""
        self.client.post(
            "/api/v1/query/",
            json={"query": "What is the main topic?", "max_results": 5},
            headers=self.headers
        )

    @task(1)
    def query_enhanced(self):
        """Simulate enhanced query with confidence scores."""
        self.client.post(
            "/api/v1/query/enhanced",
            json={"query": "Explain the key findings", "max_results": 3},
            headers=self.headers
        )
```

### RAGAs Evaluation Integration
```python
# Source: RAGAs documentation
from ragas import evaluate
from ragas.metrics import faithfulness, context_recall, factual_correctness
from datasets import Dataset

async def evaluate_rag_quality(test_cases: list[dict]) -> dict:
    """
    Evaluate RAG system quality using RAGAs metrics.

    test_cases format:
    [{"question": str, "answer": str, "contexts": list[str], "ground_truth": str}, ...]
    """
    dataset = Dataset.from_list(test_cases)

    result = evaluate(
        dataset,
        metrics=[
            faithfulness,       # Is answer grounded in context?
            context_recall,     # Did we retrieve all relevant info?
            factual_correctness # Is answer factually correct?
        ]
    )

    return {
        "faithfulness": result["faithfulness"],
        "context_recall": result["context_recall"],
        "factual_correctness": result["factual_correctness"],
        "overall": (result["faithfulness"] + result["context_recall"]) / 2
    }
```

### Circuit Breaker with Fallback
```python
# Source: circuitbreaker PyPI
from circuitbreaker import circuit, CircuitBreakerError

class OpenAICircuitBreaker:
    """Circuit breaker for OpenAI API calls with graceful fallback."""

    @circuit(failure_threshold=5, recovery_timeout=60)
    async def generate_answer(self, query: str, context: list) -> str:
        """Generate answer with circuit breaker protection."""
        return await self._call_openai(query, context)

    async def generate_answer_safe(self, query: str, context: list) -> str:
        """Safe wrapper with fallback when circuit is open."""
        try:
            return await self.generate_answer(query, context)
        except CircuitBreakerError:
            return self._fallback_response(query, context)

    def _fallback_response(self, query: str, context: list) -> str:
        """Return cached/default response when OpenAI unavailable."""
        return "I'm temporarily unable to generate a detailed response. Please try again in a moment."
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Custom request logging | OpenTelemetry auto-instrumentation | 2023 | Single line for full observability |
| aioredis | redis.asyncio | 2022 (redis-py 5.0) | aioredis deprecated, merged into redis-py |
| Manual metrics | prometheus-fastapi-instrumentator | 2022 | Auto-exports standard HTTP metrics |
| Print debugging | Distributed tracing | 2024 (OpenTelemetry maturity) | Cross-service debugging possible |
| Manual RAG evaluation | RAGAs framework | 2024 | Standardized, reproducible metrics |

**Deprecated/outdated:**
- aioredis: Merged into redis-py 5.0+, use redis.asyncio instead (already done in project)
- flask-limiter patterns: slowapi is the FastAPI-native equivalent
- Manual prometheus_client usage: prometheus-fastapi-instrumentator handles common cases

## Open Questions

Things that couldn't be fully resolved:

1. **OpenTelemetry backend choice**
   - What we know: OTLP exporter supports Jaeger, Tempo, Zipkin, and commercial APM tools
   - What's unclear: Which backend to use for this project (local dev vs production)
   - Recommendation: Use Jaeger for local development (Docker), design for backend-agnostic OTLP export

2. **Rate limit values for RAG endpoints**
   - What we know: Query endpoints are expensive (LLM costs, database queries)
   - What's unclear: Appropriate limits for "100+ concurrent users" requirement
   - Recommendation: Start conservative (10 req/min for /query, 50 req/min for /documents), tune based on load testing

3. **RAGAs evaluation dataset creation**
   - What we know: Need ground truth for meaningful evaluation
   - What's unclear: How to efficiently create evaluation dataset for this specific domain
   - Recommendation: Create 50 test cases manually, expand as system matures

## Sources

### Primary (HIGH confidence)
- [OpenTelemetry FastAPI instrumentation docs](https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/fastapi/fastapi.html) - Automatic instrumentation setup
- [prometheus-fastapi-instrumentator GitHub](https://github.com/trallnag/prometheus-fastapi-instrumentator) - Metrics configuration
- [structlog documentation](https://www.structlog.org/en/stable/getting-started.html) - Async logging patterns
- [slowapi documentation](https://slowapi.readthedocs.io/) - Rate limiting setup
- [limits library storage docs](https://limits.readthedocs.io/en/stable/storage.html) - Redis async backend
- [tenacity documentation](https://tenacity.readthedocs.io/) - Retry patterns
- [circuitbreaker PyPI](https://pypi.org/project/circuitbreaker/) - Circuit breaker usage
- [Locust documentation](https://docs.locust.io/en/stable/what-is-locust.html) - Load testing
- [RAGAs documentation](https://docs.ragas.io/en/stable/) - RAG evaluation metrics

### Secondary (MEDIUM confidence)
- [FastAPI observability patterns article](https://deepwiki.com/fastapi-practices/fastapi_best_architecture/10.3-logging-and-monitoring) - Architecture recommendations
- [Redis caching patterns tutorial](https://redis.io/tutorials/develop/python/fastapi/) - Cache-aside pattern
- [Load testing comparison 2026](https://medium.com/@sohail_saifi/load-testing-your-api-k6-vs-artillery-vs-locust-66a8d7f575bd) - Tool selection

### Tertiary (LOW confidence)
- Various Medium articles on FastAPI performance - General patterns, verify with official docs

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries verified via official documentation and PyPI
- Architecture: HIGH - Patterns from official docs, consistent with existing codebase
- Pitfalls: MEDIUM - Based on multiple sources, some require validation in load testing

**Research date:** 2026-02-05
**Valid until:** 30 days (stable domain, mature libraries)
