"""FastAPI application entry point with lifespan events."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.core.error_handlers import register_exception_handlers


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown events."""
    # Startup: Initialize database connections
    print("Starting up - connecting to databases...")

    # Import database clients here to avoid circular imports
    from app.db.neo4j_client import neo4j_driver, close_neo4j, init_neo4j_schema
    from app.db.qdrant_client import qdrant_client, close_qdrant, init_qdrant_collection
    from app.db.redis_client import close_redis
    from app.db.postgres_client import close_postgres_pool
    from app.db.checkpoint_store import setup_checkpointer
    from app.jobs.cleanup import setup_cleanup_scheduler, shutdown_cleanup_scheduler

    # Verify Neo4j connection
    neo4j_driver.verify_connectivity()
    print("Neo4j connected")

    # Initialize Neo4j schema (constraints and indexes)
    init_neo4j_schema()
    print("Neo4j schema initialized")

    # Verify Qdrant connection
    qdrant_client.get_collections()
    print("Qdrant connected")

    # Initialize Qdrant collection
    init_qdrant_collection()
    print("Qdrant collection initialized")

    # Validate embedding dimensions at startup
    from app.services.embedding_service import validate_embedding_dimensions

    await validate_embedding_dimensions()
    print("Embedding dimensions validated")

    # Start cleanup scheduler for anonymous data TTL
    setup_cleanup_scheduler()
    print("Cleanup scheduler started")

    # Initialize LangGraph checkpoint tables in PostgreSQL
    try:
        await setup_checkpointer()
        print("LangGraph checkpointer initialized")
    except Exception as e:
        print(f"Warning: LangGraph checkpointer setup failed: {e}")
        print("Continuing without LangGraph checkpointing - workflows will use in-memory state")

    print("Startup complete")

    yield  # Application runs

    # Shutdown: Close connections and stop scheduler
    print("Shutting down - closing database connections...")
    shutdown_cleanup_scheduler()
    close_neo4j()
    close_qdrant()
    await close_redis()
    await close_postgres_pool()
    print("Connections closed")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
)

# Register global exception handlers for consistent error responses
register_exception_handlers(app)

# CORS middleware (configure for your frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": settings.VERSION}


# Router includes
from app.api.admin import router as admin_router
from app.api.auth import router as auth_router
from app.api.comparisons import router as comparisons_router
from app.api.documents import router as documents_router
from app.api.memory import router as memory_router
from app.api.queries import router as queries_router

app.include_router(admin_router, prefix=settings.API_V1_PREFIX, tags=["admin"])
app.include_router(auth_router, prefix=f"{settings.API_V1_PREFIX}/auth", tags=["auth"])
app.include_router(comparisons_router, prefix=f"{settings.API_V1_PREFIX}/compare", tags=["comparison"])
app.include_router(documents_router, prefix=f"{settings.API_V1_PREFIX}/documents", tags=["documents"])
app.include_router(memory_router, prefix=settings.API_V1_PREFIX, tags=["memory"])
app.include_router(queries_router, prefix=f"{settings.API_V1_PREFIX}/query", tags=["queries"])
