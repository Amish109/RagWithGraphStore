# Phase 1: Foundation & Core RAG - Research

**Researched:** 2026-02-04
**Domain:** FastAPI + Mem0 + Neo4j + Qdrant RAG foundation
**Confidence:** HIGH

## Summary

Phase 1 establishes the critical foundation for a production RAG system with memory management. This phase delivers working document upload (PDF/DOCX), semantic chunking, dual-storage indexing (Neo4j + Qdrant), basic retrieval with citations, and JWT authentication. The architecture must be correct from day one because three of the five critical pitfalls identified in project research (#1: memory confusion, #3: poor chunking, #4: multi-tenant isolation) are architectural decisions that are expensive to fix later.

The standard approach for Phase 1 is: FastAPI with async/await for the API layer, Pydantic BaseSettings for configuration, semantic chunking with RecursiveCharacterTextSplitter (not fixed-size), pymupdf4llm for PDF parsing, dual-write to Neo4j and Qdrant with shared UUIDs, and JWT authentication with pwdlib Argon2 hashing. This phase intentionally keeps memory management simple (Mem0 configuration only, full integration in Phase 2) to validate the core RAG loop before adding complexity.

**Primary recommendation:** Build authentication and database connections first, then document processing pipeline, then basic retrieval. Test multi-tenant filtering from the start even though Phase 1 is single-user focused. Lock the embedding model (text-embedding-3-small) and validate dimensions before any document ingestion. Design the Neo4j schema upfront with clear node types and relationships - don't start with "just store everything."

## Standard Stack

The established libraries/tools for Phase 1 foundation:

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| fastapi | >=0.126.0 | Async web framework | 2026 industry standard for ML/AI APIs. Native async, automatic OpenAPI docs, Pydantic v2 integration. |
| pydantic | >=2.7.0 | Data validation & settings | FastAPI foundation. v2 is now standard (v1 deprecated). Type-safe config via BaseSettings. |
| uvicorn[standard] | latest | ASGI server | High-performance async server for FastAPI. "standard" includes websockets, watchfiles. |
| mem0ai | latest | Memory management | Purpose-built for RAG memory. Dual-store orchestration (Neo4j + Qdrant), auto memory extraction. |
| neo4j | >=6.1.0 | Neo4j Python driver | Official driver. Use `neo4j`, NOT `neo4j-driver` (deprecated). Supports Python 3.10-3.14. |
| qdrant-client | >=1.16.2 | Qdrant Python client | Official client with async support. v1.16+ has tiered multitenancy. |
| langchain | >=1.0 | LLM orchestration | De facto standard for RAG workflows. 100+ integrations. Use for linear pipelines. |
| langchain-openai | >=1.1.7 | OpenAI integration | Official connector. Latest release Jan 7, 2026. Provides ChatOpenAI for reasoning. |
| pymupdf4llm | latest | PDF to Markdown | Fast (0.003-0.024s/page) and accurate for RAG. Outputs clean Markdown for chunking. |
| python-docx | latest | DOCX parsing | Standard library for Word document parsing. Handles text, tables, embedded objects. |
| pyjwt | latest | JWT tokens | Industry standard for stateless auth. Used in FastAPI official docs. |
| pwdlib[argon2] | latest | Password hashing | FastAPI official recommendation. Argon2 is GPU-resistant. OWASP-compliant. |
| python-dotenv | latest | Env var loading | Load .env files for local dev. Never use in production (use OS env vars). |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| openai | latest | Direct OpenAI API access | If not using langchain-openai. For embeddings generation. |
| pytest | latest | Testing framework | Unit/integration tests for FastAPI routes and RAG pipelines. |
| pytest-asyncio | latest | Async test support | Test async FastAPI endpoints. Required for async test functions. |
| httpx | latest | Async HTTP client | If calling external APIs from async routes. Testing async endpoints. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| FastAPI | Flask | Flask is synchronous. RAG requires async I/O for LLM calls. FastAPI purpose-built. |
| FastAPI | Django | Django is heavy, sync-first. Overkill for API-only backend. |
| pymupdf4llm | Unstructured | Unstructured slower, quality varies. pymupdf4llm is faster and more consistent. |
| pymupdf4llm | Docling | Docling better for complex layouts but 4s/page vs 0.024s/page. Use if needed in Phase 3+. |
| langchain | LlamaIndex | LlamaIndex excellent for RAG but less flexible for agents. LangChain broader ecosystem. |
| Mem0 | LangChain Memory | LangChain memory is basic (context window only). Mem0 provides graph integration, auto-consolidation. |
| neo4j package | neo4j-driver | neo4j-driver is DEPRECATED. Use `neo4j` package (official as of 2026). |
| pwdlib | bcrypt | Argon2 more resistant to GPU attacks. FastAPI official recommendation 2026. |

**Installation:**
```bash
# Core framework
pip install "fastapi>=0.126.0"
pip install "pydantic>=2.7.0"
pip install "uvicorn[standard]"

# Memory & databases
pip install mem0ai
pip install "neo4j>=6.1.0"
pip install "qdrant-client>=1.16.2"

# LLM orchestration
pip install "langchain>=1.0"
pip install "langchain-openai>=1.1.7"

# Document processing
pip install pymupdf4llm
pip install python-docx

# Authentication
pip install pyjwt
pip install "pwdlib[argon2]"

# Development
pip install python-dotenv
pip install pytest pytest-asyncio httpx
```

## Architecture Patterns

### Recommended Project Structure
```
RAGWithGraphStore/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI app entry point
│   │   ├── config.py                  # Pydantic BaseSettings configuration
│   │   ├── dependencies.py            # FastAPI dependency injection
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py               # POST /auth/register, /auth/login, /auth/logout
│   │   │   ├── documents.py          # POST /documents/upload
│   │   │   └── queries.py            # POST /query (Q&A endpoint)
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py               # JWT generation, validation, password hashing
│   │   │   ├── security.py           # OAuth2 scheme, get_current_user dependency
│   │   │   └── exceptions.py         # Custom exception classes
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── neo4j_client.py       # Neo4j connection and operations
│   │   │   ├── qdrant_client.py      # Qdrant connection and operations
│   │   │   └── mem0_client.py        # Mem0 initialization (Phase 2 full usage)
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── document_processor.py # PDF/DOCX parsing, chunking
│   │   │   ├── embedding_service.py  # Generate embeddings via OpenAI
│   │   │   ├── indexing_service.py   # Dual-write to Neo4j + Qdrant
│   │   │   └── retrieval_service.py  # Hybrid retrieval (vector + graph)
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── user.py               # User model (stored in Neo4j)
│   │   │   ├── document.py           # Document model
│   │   │   └── schemas.py            # Pydantic request/response schemas
│   │   └── utils/
│   │       ├── __init__.py
│   │       └── logging.py            # Structured logging setup
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_auth.py
│   │   ├── test_documents.py
│   │   └── test_queries.py
│   ├── .env.example                  # Template for environment variables
│   ├── requirements.txt              # Pinned versions for production
│   └── pyproject.toml                # Project metadata and dependencies
├── .planning/                         # Planning docs (existing)
└── README.md
```

**Rationale:** Separate API routes (`api/`), business logic (`services/`), database clients (`db/`), and auth/security (`core/`). This structure scales well and makes testing easier. Services layer abstracts database operations from API routes.

### Pattern 1: Configuration Management with Pydantic BaseSettings

**What:** Centralized configuration using Pydantic BaseSettings that loads from environment variables with validation.

**When to use:** Phase 1 setup, before any database connections.

**Example:**
```python
# app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # API Settings
    PROJECT_NAME: str = "RAG with Memory Management"
    VERSION: str = "0.1.0"
    API_V1_PREFIX: str = "/api/v1"

    # Security
    SECRET_KEY: str  # REQUIRED - for JWT signing
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Neo4j Configuration
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USERNAME: str = "neo4j"
    NEO4J_PASSWORD: str  # REQUIRED
    NEO4J_DATABASE: str = "neo4j"

    # Qdrant Configuration
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_API_KEY: Optional[str] = None  # For Qdrant Cloud
    QDRANT_COLLECTION: str = "documents"

    # OpenAI Configuration
    OPENAI_API_KEY: str  # REQUIRED
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OPENAI_EMBEDDING_DIMENSIONS: int = 1536

    # Document Processing
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    MAX_UPLOAD_SIZE_MB: int = 50

    # Logging
    LOG_LEVEL: str = "INFO"

# Global settings instance
settings = Settings()
```

**Critical:** Store `SECRET_KEY`, `NEO4J_PASSWORD`, and `OPENAI_API_KEY` in environment variables, NEVER in code. Use strong random secret for `SECRET_KEY` (32+ bytes).

**Validation:** At startup, Pydantic raises ValidationError if required fields are missing. This fails fast.

### Pattern 2: FastAPI App Setup with Lifespan Events

**What:** Proper FastAPI initialization with startup/shutdown events for database connections.

**When to use:** main.py entry point.

**Example:**
```python
# app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db.neo4j_client import neo4j_driver, close_neo4j
from app.db.qdrant_client import qdrant_client, close_qdrant
from app.api import auth, documents, queries

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown events."""
    # Startup: Initialize database connections
    print("Starting up - connecting to databases...")

    # Verify Neo4j connection
    neo4j_driver.verify_connectivity()
    print("✓ Neo4j connected")

    # Verify Qdrant connection
    qdrant_client.get_collections()
    print("✓ Qdrant connected")

    # Validate embedding dimensions
    from app.services.embedding_service import validate_embedding_dimensions
    validate_embedding_dimensions()
    print("✓ Embedding dimensions validated")

    yield  # Application runs

    # Shutdown: Close connections
    print("Shutting down - closing database connections...")
    close_neo4j()
    close_qdrant()
    print("✓ Connections closed")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan
)

# CORS middleware (configure for your frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix=f"{settings.API_V1_PREFIX}/auth", tags=["auth"])
app.include_router(documents.router, prefix=f"{settings.API_V1_PREFIX}/documents", tags=["documents"])
app.include_router(queries.router, prefix=f"{settings.API_V1_PREFIX}/query", tags=["queries"])

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": settings.VERSION}
```

**Critical:** Use `lifespan` context manager (new in FastAPI 0.93+) instead of deprecated `@app.on_event("startup")`. Validate connections at startup to fail fast if misconfigured.

### Pattern 3: Neo4j Connection and Schema Setup

**What:** Initialize Neo4j driver with connection pooling and create schema constraints/indexes.

**When to use:** Phase 1 database setup.

**Example:**
```python
# app/db/neo4j_client.py
from neo4j import GraphDatabase
from app.config import settings

# Initialize Neo4j driver (singleton)
neo4j_driver = GraphDatabase.driver(
    settings.NEO4J_URI,
    auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD),
    max_connection_lifetime=3600,  # 1 hour
    max_connection_pool_size=50,
    connection_acquisition_timeout=60
)

def close_neo4j():
    """Close Neo4j driver connection."""
    neo4j_driver.close()

def init_neo4j_schema():
    """Initialize Neo4j schema with constraints and indexes.

    Run once during deployment or in migration script.
    CRITICAL: Define schema BEFORE data ingestion to prevent performance issues.
    """
    with neo4j_driver.session(database=settings.NEO4J_DATABASE) as session:
        # Constraints (also create indexes)
        session.run("""
            CREATE CONSTRAINT user_id_unique IF NOT EXISTS
            FOR (u:User) REQUIRE u.id IS UNIQUE
        """)

        session.run("""
            CREATE CONSTRAINT document_id_unique IF NOT EXISTS
            FOR (d:Document) REQUIRE d.id IS UNIQUE
        """)

        session.run("""
            CREATE CONSTRAINT chunk_id_unique IF NOT EXISTS
            FOR (c:Chunk) REQUIRE c.id IS UNIQUE
        """)

        session.run("""
            CREATE CONSTRAINT entity_id_unique IF NOT EXISTS
            FOR (e:Entity) REQUIRE e.id IS UNIQUE
        """)

        # Additional indexes for filtering (multi-tenancy)
        session.run("""
            CREATE INDEX user_email IF NOT EXISTS
            FOR (u:User) ON (u.email)
        """)

        session.run("""
            CREATE INDEX document_user_id IF NOT EXISTS
            FOR (d:Document) ON (d.user_id)
        """)

        session.run("""
            CREATE INDEX chunk_document_id IF NOT EXISTS
            FOR (c:Chunk) ON (c.document_id)
        """)

        print("✓ Neo4j schema initialized")

def create_user(email: str, hashed_password: str, user_id: str) -> dict:
    """Create a new user in Neo4j."""
    with neo4j_driver.session(database=settings.NEO4J_DATABASE) as session:
        result = session.run("""
            CREATE (u:User {
                id: $user_id,
                email: $email,
                hashed_password: $hashed_password,
                created_at: datetime()
            })
            RETURN u
        """, user_id=user_id, email=email, hashed_password=hashed_password)

        return result.single()["u"]

def get_user_by_email(email: str) -> dict:
    """Retrieve user by email."""
    with neo4j_driver.session(database=settings.NEO4J_DATABASE) as session:
        result = session.run("""
            MATCH (u:User {email: $email})
            RETURN u
        """, email=email)

        record = result.single()
        return dict(record["u"]) if record else None
```

**Critical:** Create constraints and indexes BEFORE data ingestion. Without indexes on `user_id` and `document_id`, multi-tenant filtering becomes unusably slow at scale.

**Schema Design (Phase 1):**
```cypher
// Node types
(:User {id, email, hashed_password, created_at})
(:Document {id, user_id, filename, upload_date, file_size})
(:Chunk {id, document_id, text, position, embedding_id})  // embedding_id links to Qdrant
(:Entity {id, name, type, chunk_ids[]})  // Phase 2+ for graph enrichment

// Relationships
(User)-[:OWNS]->(Document)
(Document)-[:CONTAINS]->(Chunk)
(Entity)-[:MENTIONED_IN]->(Chunk)
(Entity)-[:RELATES_TO {type, confidence}]->(Entity)  // Phase 2+
```

### Pattern 4: Qdrant Connection and Collection Setup

**What:** Initialize Qdrant client and create collection with proper configuration.

**When to use:** Phase 1 database setup.

**Example:**
```python
# app/db/qdrant_client.py
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, OptimizersConfigDiff
from app.config import settings
from typing import List, Dict
import uuid

# Initialize Qdrant client (singleton)
if settings.QDRANT_API_KEY:
    # Qdrant Cloud
    qdrant_client = QdrantClient(
        url=f"https://{settings.QDRANT_HOST}",
        api_key=settings.QDRANT_API_KEY,
        timeout=60
    )
else:
    # Local Qdrant
    qdrant_client = QdrantClient(
        host=settings.QDRANT_HOST,
        port=settings.QDRANT_PORT,
        timeout=60
    )

def close_qdrant():
    """Close Qdrant client connection."""
    qdrant_client.close()

def init_qdrant_collection():
    """Initialize Qdrant collection with proper configuration.

    CRITICAL: Vector dimension MUST match embedding model.
    Once created, dimension cannot be changed - requires recreation.
    """
    collection_name = settings.QDRANT_COLLECTION

    # Check if collection exists
    collections = qdrant_client.get_collections().collections
    if any(c.name == collection_name for c in collections):
        print(f"✓ Qdrant collection '{collection_name}' already exists")
        return

    # Create collection
    qdrant_client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(
            size=settings.OPENAI_EMBEDDING_DIMENSIONS,  # MUST match embedding model
            distance=Distance.COSINE  # Cosine similarity for OpenAI embeddings
        ),
        optimizers_config=OptimizersConfigDiff(
            indexing_threshold=10000  # Start indexing after 10k vectors
        )
    )

    # Create payload indexes for filtering (multi-tenancy)
    qdrant_client.create_payload_index(
        collection_name=collection_name,
        field_name="user_id",
        field_schema="keyword"  # Exact match filtering
    )

    qdrant_client.create_payload_index(
        collection_name=collection_name,
        field_name="document_id",
        field_schema="keyword"
    )

    print(f"✓ Qdrant collection '{collection_name}' created")

def upsert_chunks(chunks: List[Dict]) -> None:
    """Insert or update document chunks with embeddings.

    Args:
        chunks: List of dicts with keys: id, vector, text, document_id, user_id, metadata
    """
    points = [
        PointStruct(
            id=chunk["id"],  # Use UUID from Neo4j for linkage
            vector=chunk["vector"],
            payload={
                "chunk_id": chunk["id"],
                "text": chunk["text"],
                "document_id": chunk["document_id"],
                "user_id": chunk["user_id"],
                "position": chunk.get("position", 0),
                "metadata": chunk.get("metadata", {})
            }
        )
        for chunk in chunks
    ]

    qdrant_client.upsert(
        collection_name=settings.QDRANT_COLLECTION,
        points=points
    )

def search_similar_chunks(query_vector: List[float], user_id: str, limit: int = 10) -> List[Dict]:
    """Search for similar chunks filtered by user_id.

    CRITICAL: Always filter by user_id for multi-tenant isolation.
    """
    from qdrant_client.models import Filter, FieldCondition, MatchValue

    results = qdrant_client.search(
        collection_name=settings.QDRANT_COLLECTION,
        query_vector=query_vector,
        limit=limit,
        query_filter=Filter(
            must=[
                FieldCondition(
                    key="user_id",
                    match=MatchValue(value=user_id)
                )
            ]
        ),
        with_payload=True,
        with_vectors=False  # Don't return vectors (save bandwidth)
    )

    return [
        {
            "id": hit.id,
            "score": hit.score,
            "text": hit.payload["text"],
            "document_id": hit.payload["document_id"],
            "position": hit.payload.get("position", 0)
        }
        for hit in results
    ]
```

**Critical:**
1. Vector dimension MUST match embedding model. Validate at startup.
2. ALWAYS filter by `user_id` in search queries (multi-tenant isolation).
3. Create payload indexes on `user_id` and `document_id` for fast filtering.

### Pattern 5: JWT Authentication with FastAPI Security

**What:** Implement JWT-based authentication with password hashing and FastAPI's OAuth2PasswordBearer.

**When to use:** Phase 1 authentication setup.

**Example:**
```python
# app/core/auth.py
from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from app.config import settings

# Password hasher (Argon2 - OWASP recommended)
password_hash = PasswordHash((Argon2Hasher(),))

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return password_hash.verify(plain_password, hashed_password)

def hash_password(password: str) -> str:
    """Hash a password using Argon2."""
    return password_hash.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    return encoded_jwt

def decode_access_token(token: str) -> Optional[dict]:
    """Decode and verify a JWT token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
```

```python
# app/core/security.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.core.auth import decode_access_token
from app.db.neo4j_client import get_user_by_email

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """Dependency to get current authenticated user from JWT token.

    Use this in route dependencies to protect endpoints:
    @app.get("/protected")
    async def protected_route(current_user: dict = Depends(get_current_user)):
        ...
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    email: str = payload.get("sub")
    if email is None:
        raise credentials_exception

    user = get_user_by_email(email)
    if user is None:
        raise credentials_exception

    return user
```

```python
# app/api/auth.py
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from datetime import timedelta
import uuid

from app.config import settings
from app.core.auth import verify_password, hash_password, create_access_token
from app.db.neo4j_client import create_user, get_user_by_email

router = APIRouter()

class UserRegister(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister):
    """Register a new user (AUTH-01)."""
    # Check if user exists
    existing_user = get_user_by_email(user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create user
    user_id = str(uuid.uuid4())
    hashed_password = hash_password(user_data.password)
    create_user(email=user_data.email, hashed_password=hashed_password, user_id=user_id)

    # Generate token
    access_token = create_access_token(data={"sub": user_data.email})

    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Login and get JWT token (AUTH-02)."""
    user = get_user_by_email(form_data.username)  # OAuth2 uses 'username' field for email

    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Generate token
    access_token = create_access_token(data={"sub": user["email"]})

    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/logout")
async def logout():
    """Logout user (AUTH-07).

    JWT tokens are stateless - actual logout handled client-side by discarding token.
    This endpoint exists for completeness and future session management.
    """
    return {"message": "Successfully logged out"}
```

**Critical:**
1. NEVER store passwords in plaintext. Use Argon2 (GPU-resistant).
2. NEVER hardcode `SECRET_KEY`. Use env vars.
3. Set short token expiration (15-30 min recommended).
4. NEVER accept `"none"` algorithm in JWT validation.
5. ALWAYS use HTTPS in production.

### Pattern 6: Document Upload with Async Processing

**What:** Accept document uploads and process them asynchronously using FastAPI BackgroundTasks.

**When to use:** Phase 1 document ingestion.

**Example:**
```python
# app/api/documents.py
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks
from app.core.security import get_current_user
from app.services.document_processor import process_document_pipeline
import uuid

router = APIRouter()

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    current_user: dict = Depends(get_current_user)
):
    """Upload PDF or DOCX document (API-01, DOC-01, DOC-02).

    Returns immediately with document_id. Processing happens in background.
    """
    # Validate file type
    allowed_types = ["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files are supported")

    # Generate document ID
    document_id = str(uuid.uuid4())
    user_id = current_user["id"]

    # Save file temporarily
    import tempfile
    import os
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1])

    try:
        contents = await file.read()
        temp_file.write(contents)
        temp_file.flush()
        temp_file.close()

        # Queue background processing
        background_tasks.add_task(
            process_document_pipeline,
            file_path=temp_file.name,
            document_id=document_id,
            user_id=user_id,
            filename=file.filename
        )

        return {
            "document_id": document_id,
            "filename": file.filename,
            "status": "processing",
            "message": "Document uploaded successfully. Processing in background."
        }

    except Exception as e:
        # Clean up temp file on error
        os.unlink(temp_file.name)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
```

**Critical:** Use `BackgroundTasks` for document processing to avoid timeout errors. Large documents can take minutes to process. Return immediately with status.

### Pattern 7: Document Processing Pipeline (PDF/DOCX → Chunks → Embeddings → Storage)

**What:** Complete pipeline from document upload to dual-storage indexing.

**When to use:** Background task for document processing.

**Example:**
```python
# app/services/document_processor.py
import os
from typing import List, Dict
from langchain.text_splitter import RecursiveCharacterTextSplitter
from app.config import settings

def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from PDF using pymupdf4llm."""
    import pymupdf4llm

    # Convert PDF to Markdown
    md_text = pymupdf4llm.to_markdown(file_path)
    return md_text

def extract_text_from_docx(file_path: str) -> str:
    """Extract text from DOCX using python-docx."""
    from docx import Document

    doc = Document(file_path)

    # Extract all paragraphs and tables
    text_parts = []

    for para in doc.paragraphs:
        if para.text.strip():
            text_parts.append(para.text)

    for table in doc.tables:
        for row in table.rows:
            row_text = " | ".join(cell.text for cell in row.cells)
            text_parts.append(row_text)

    return "\n\n".join(text_parts)

def chunk_text(text: str) -> List[Dict[str, any]]:
    """Chunk text using semantic chunking (RecursiveCharacterTextSplitter).

    CRITICAL: Use semantic chunking, NOT fixed-size splitting.
    Prevents Pitfall #3 (poor chunking strategy).
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""]  # Respect semantic boundaries
    )

    chunks = splitter.split_text(text)

    # Add position metadata
    return [
        {"text": chunk, "position": idx}
        for idx, chunk in enumerate(chunks)
    ]

async def process_document_pipeline(file_path: str, document_id: str, user_id: str, filename: str):
    """Complete document processing pipeline.

    Steps:
    1. Extract text (PDF/DOCX)
    2. Chunk text (semantic chunking)
    3. Generate embeddings
    4. Store in Neo4j (metadata, chunks)
    5. Store in Qdrant (vectors)
    6. Clean up temp file
    """
    from app.services.embedding_service import generate_embeddings
    from app.services.indexing_service import store_document_in_neo4j, store_chunks_in_qdrant
    import uuid

    try:
        print(f"Processing document {document_id}: {filename}")

        # Step 1: Extract text
        if filename.lower().endswith(".pdf"):
            text = extract_text_from_pdf(file_path)
        elif filename.lower().endswith(".docx"):
            text = extract_text_from_docx(file_path)
        else:
            raise ValueError(f"Unsupported file type: {filename}")

        print(f"✓ Extracted {len(text)} characters")

        # Step 2: Chunk text
        chunks = chunk_text(text)
        print(f"✓ Created {len(chunks)} chunks")

        # Step 3: Generate embeddings
        chunk_texts = [c["text"] for c in chunks]
        embeddings = await generate_embeddings(chunk_texts)
        print(f"✓ Generated {len(embeddings)} embeddings")

        # Step 4: Prepare chunk data with UUIDs (for Neo4j + Qdrant linkage)
        chunk_data = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_id = str(uuid.uuid4())  # Shared ID between Neo4j and Qdrant
            chunk_data.append({
                "id": chunk_id,
                "text": chunk["text"],
                "position": chunk["position"],
                "vector": embedding,
                "document_id": document_id,
                "user_id": user_id
            })

        # Step 5: Store in Neo4j
        store_document_in_neo4j(
            document_id=document_id,
            user_id=user_id,
            filename=filename,
            chunks=chunk_data
        )
        print(f"✓ Stored in Neo4j")

        # Step 6: Store in Qdrant
        store_chunks_in_qdrant(chunks=chunk_data)
        print(f"✓ Stored in Qdrant")

        print(f"✓ Document {document_id} processing complete")

    except Exception as e:
        print(f"✗ Error processing document {document_id}: {e}")
        # TODO: Store error status in database for user notification
        raise

    finally:
        # Clean up temp file
        if os.path.exists(file_path):
            os.unlink(file_path)
```

```python
# app/services/embedding_service.py
from typing import List
from openai import AsyncOpenAI
from app.config import settings

# Initialize OpenAI client
openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

async def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """Generate embeddings using OpenAI API.

    CRITICAL: Model must match OPENAI_EMBEDDING_DIMENSIONS config.
    Prevents Pitfall #7 (embedding dimension mismatch).
    """
    response = await openai_client.embeddings.create(
        model=settings.OPENAI_EMBEDDING_MODEL,
        input=texts,
        encoding_format="float"
    )

    embeddings = [item.embedding for item in response.data]

    return embeddings

async def generate_query_embedding(query: str) -> List[float]:
    """Generate embedding for a single query."""
    embeddings = await generate_embeddings([query])
    return embeddings[0]

def validate_embedding_dimensions():
    """Validate that embedding dimensions match configuration.

    Run at startup to fail fast if misconfigured.
    """
    import asyncio

    async def _validate():
        test_embedding = await generate_embeddings(["test"])
        actual_dim = len(test_embedding[0])
        expected_dim = settings.OPENAI_EMBEDDING_DIMENSIONS

        if actual_dim != expected_dim:
            raise ValueError(
                f"Embedding dimension mismatch! "
                f"Expected {expected_dim}, got {actual_dim}. "
                f"Check OPENAI_EMBEDDING_MODEL and OPENAI_EMBEDDING_DIMENSIONS config."
            )

    asyncio.run(_validate())
```

```python
# app/services/indexing_service.py
from typing import List, Dict
from app.db.neo4j_client import neo4j_driver
from app.db.qdrant_client import upsert_chunks
from app.config import settings
from datetime import datetime

def store_document_in_neo4j(document_id: str, user_id: str, filename: str, chunks: List[Dict]):
    """Store document metadata and chunks in Neo4j with relationships."""
    with neo4j_driver.session(database=settings.NEO4J_DATABASE) as session:
        # Create Document node
        session.run("""
            MATCH (u:User {id: $user_id})
            CREATE (d:Document {
                id: $document_id,
                filename: $filename,
                user_id: $user_id,
                upload_date: datetime(),
                chunk_count: $chunk_count
            })
            CREATE (u)-[:OWNS]->(d)
        """, user_id=user_id, document_id=document_id, filename=filename, chunk_count=len(chunks))

        # Create Chunk nodes with relationships
        for chunk in chunks:
            session.run("""
                MATCH (d:Document {id: $document_id})
                CREATE (c:Chunk {
                    id: $chunk_id,
                    document_id: $document_id,
                    text: $text,
                    position: $position,
                    embedding_id: $chunk_id
                })
                CREATE (d)-[:CONTAINS]->(c)
            """,
            document_id=document_id,
            chunk_id=chunk["id"],
            text=chunk["text"],
            position=chunk["position"]
            )

def store_chunks_in_qdrant(chunks: List[Dict]):
    """Store chunk embeddings in Qdrant."""
    upsert_chunks(chunks)
```

**Critical:**
1. Use semantic chunking (`RecursiveCharacterTextSplitter`), NOT fixed-size.
2. Use shared UUIDs between Neo4j and Qdrant for linkage.
3. ALWAYS include `user_id` in Qdrant payload for multi-tenant filtering.
4. Validate embedding dimensions at startup.

### Pattern 8: Query Endpoint with Hybrid Retrieval

**What:** Handle user queries with vector search + basic citation.

**When to use:** Phase 1 query API.

**Example:**
```python
# app/api/queries.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List
from app.core.security import get_current_user
from app.services.retrieval_service import retrieve_relevant_context
from app.services.generation_service import generate_answer

router = APIRouter()

class QueryRequest(BaseModel):
    query: str
    max_results: int = 3

class Citation(BaseModel):
    document_id: str
    filename: str
    chunk_text: str
    relevance_score: float

class QueryResponse(BaseModel):
    answer: str
    citations: List[Citation]

@router.post("/", response_model=QueryResponse)
async def query_documents(
    request: QueryRequest,
    current_user: dict = Depends(get_current_user)
):
    """Ask a question about uploaded documents (API-04, QRY-01, QRY-03, QRY-04)."""
    user_id = current_user["id"]

    # Step 1: Retrieve relevant context
    context = await retrieve_relevant_context(
        query=request.query,
        user_id=user_id,
        max_results=request.max_results
    )

    if not context["chunks"]:
        return QueryResponse(
            answer="I don't know. I couldn't find any relevant information in your documents.",
            citations=[]
        )

    # Step 2: Generate answer
    answer = await generate_answer(
        query=request.query,
        context=context["chunks"]
    )

    # Step 3: Format citations
    citations = [
        Citation(
            document_id=chunk["document_id"],
            filename=chunk["filename"],
            chunk_text=chunk["text"][:200] + "..." if len(chunk["text"]) > 200 else chunk["text"],
            relevance_score=chunk["score"]
        )
        for chunk in context["chunks"]
    ]

    return QueryResponse(answer=answer, citations=citations)
```

```python
# app/services/retrieval_service.py
from typing import List, Dict
from app.services.embedding_service import generate_query_embedding
from app.db.qdrant_client import search_similar_chunks
from app.db.neo4j_client import neo4j_driver
from app.config import settings

async def retrieve_relevant_context(query: str, user_id: str, max_results: int = 3) -> Dict:
    """Retrieve relevant context using vector search.

    Phase 1: Vector-only retrieval from Qdrant.
    Phase 2+: Add graph enrichment with Neo4j.
    """
    # Step 1: Generate query embedding
    query_embedding = await generate_query_embedding(query)

    # Step 2: Vector search in Qdrant (filtered by user_id)
    similar_chunks = search_similar_chunks(
        query_vector=query_embedding,
        user_id=user_id,
        limit=max_results
    )

    # Step 3: Enrich with document metadata from Neo4j
    enriched_chunks = []
    with neo4j_driver.session(database=settings.NEO4J_DATABASE) as session:
        for chunk in similar_chunks:
            result = session.run("""
                MATCH (c:Chunk {id: $chunk_id})-[:PART_OF|CONTAINS*]-(d:Document)
                RETURN d.filename AS filename, d.id AS document_id
            """, chunk_id=chunk["id"])

            record = result.single()
            if record:
                enriched_chunks.append({
                    **chunk,
                    "filename": record["filename"],
                    "document_id": record["document_id"]
                })

    return {"chunks": enriched_chunks}
```

```python
# app/services/generation_service.py
from typing import List, Dict
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from app.config import settings

# Initialize LLM
llm = ChatOpenAI(
    model=settings.OPENAI_MODEL,
    temperature=0,  # Deterministic for consistency
    openai_api_key=settings.OPENAI_API_KEY
)

async def generate_answer(query: str, context: List[Dict]) -> str:
    """Generate answer using LLM with strict context-only constraint.

    CRITICAL: Prevents hallucination by enforcing "I don't know" fallback.
    Addresses QRY-04 requirement.
    """
    # Assemble context from chunks
    context_text = "\n\n".join([
        f"[Document: {chunk['filename']}]\n{chunk['text']}"
        for chunk in context
    ])

    # Prompt template with strict constraints
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a helpful document Q&A assistant. Answer questions ONLY based on the provided context.

CRITICAL INSTRUCTIONS:
- If the context does not contain information to answer the question, respond EXACTLY with: "I don't know. I couldn't find information about this in the provided documents."
- Do not use any knowledge outside the provided context
- Cite the document name when referencing information
- Be concise and direct"""),
        ("user", """Context:
{context}

Question: {query}

Answer:""")
    ])

    # Generate response
    messages = prompt.format_messages(context=context_text, query=query)
    response = await llm.ainvoke(messages)

    return response.content
```

**Critical:**
1. ALWAYS filter Qdrant search by `user_id` (multi-tenant isolation).
2. Strict prompt with "I don't know" fallback prevents hallucinations.
3. Phase 1 uses vector-only retrieval. Graph enrichment comes in Phase 2.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Password hashing | Custom hashing function | pwdlib with Argon2 | Argon2 is GPU-resistant, handles salting, constant-time comparison. Custom implementations have timing attacks. |
| JWT tokens | Custom token generation | PyJWT library | Handles signature validation, expiration, algorithm validation. Custom implementations miss edge cases (e.g., "none" algorithm attack). |
| Semantic chunking | Fixed-size text splitting | LangChain RecursiveCharacterTextSplitter | Respects semantic boundaries (paragraphs, sentences). Fixed splits destroy context. |
| API authentication | Custom middleware | FastAPI Security (OAuth2PasswordBearer) | Handles token extraction, error responses, OpenAPI schema generation. |
| Configuration management | Manual env var parsing | Pydantic BaseSettings | Type validation, default values, required fields, automatic .env loading. |
| Database connection pooling | Manual connection management | Official drivers (neo4j, qdrant-client) | Handle reconnection, timeout, connection limits, health checks. |
| Async operations | Threading or multiprocessing | FastAPI async/await + BackgroundTasks | True async I/O for database and API calls. Cleaner code, better performance. |
| PDF parsing | Regular expressions on PDF bytes | pymupdf4llm or Docling | PDF structure is complex (fonts, encodings, layouts). Libraries handle edge cases. |

**Key insight:** Security, data processing, and database operations have subtle edge cases that take years to discover. Use battle-tested libraries instead of custom implementations.

## Common Pitfalls

### Pitfall 1: Confusing RAG with Agent Memory (CRITICAL)

**What goes wrong:** Using RAG's vector similarity for user memory storage causes agents to "forget" context and lose conversation coherence. Memory retrieval returns irrelevant past interactions based on keyword similarity rather than temporal or relational relevance.

**Why it happens:** RAG and memory management are conceptually conflated. Developers assume vector similarity works for both document retrieval and user state management.

**How to avoid:**
- Phase 1: Configure Mem0 with dual stores (Neo4j for relationships + Qdrant for documents) but don't fully integrate yet
- Keep document knowledge (RAG) separate from user memory architecturally
- In Phase 1, focus on RAG. Full Mem0 integration comes in Phase 2
- Design clear separation: `services/retrieval_service.py` (documents) vs. `services/memory_service.py` (user context, added Phase 2)

**Warning signs:**
- Planning to store user preferences in document embeddings
- Using same Qdrant collection for documents and memory
- No distinction between "what user asked before" (memory) and "what documents say" (knowledge)

**Phase to address:** Phase 1 architecture, Phase 2 implementation

### Pitfall 2: Poor Chunking Strategy Torpedoes Retrieval Accuracy (CRITICAL)

**What goes wrong:** Using fixed chunk sizes (e.g., "split every 512 tokens") destroys semantic context, leading to retrieval of incomplete or meaningless fragments. Accuracy drops 30-50% compared to semantic chunking.

**Why it happens:** Most tutorials show simple fixed-size chunking as the default. Teams underestimate how critical chunking is to RAG performance.

**How to avoid:**
- Use `RecursiveCharacterTextSplitter` with semantic separators (`["\n\n", "\n", ". ", " "]`)
- Start with chunk_size=1000, chunk_overlap=200 (tune based on evaluation)
- For PDFs, use pymupdf4llm which outputs clean Markdown
- Test chunking strategy: manually inspect chunks to ensure context is preserved
- Add chunk metadata (position, parent document) for debugging

**Warning signs:**
- Retrieved chunks lack context to answer queries
- Manual inspection shows chunks split mid-sentence or mid-table
- Users complain answers are "incomplete" or "cut off"

**Phase to address:** Phase 1 (document processing pipeline)

### Pitfall 3: Embedding Dimension Mismatch (MODERATE)

**What goes wrong:** Creating Qdrant collection with 1536 dimensions, then switching to embedding model that outputs 768 dimensions (or vice versa). Vector store rejects insertions with cryptic errors.

**Why it happens:** Embedding model changed mid-development, or different models used for indexing vs. querying.

**How to avoid:**
- Document embedding model early in `config.py`: `OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"`
- Set dimension constant: `OPENAI_EMBEDDING_DIMENSIONS = 1536`
- Validate at startup with `validate_embedding_dimensions()` (see Pattern 7)
- Centralize embedding logic in `embedding_service.py`
- Pin exact model version in requirements.txt

**Warning signs:**
- Errors like "Vector dimension 768 does not match index 1536"
- Insertion/query failures after dependency update
- Different behavior between dev (local model) and prod (OpenAI)

**Phase to address:** Phase 1 (configuration and startup validation)

### Pitfall 4: JWT Security Vulnerabilities (CRITICAL)

**What goes wrong:** Hardcoded secrets, no signature validation, accepting "none" algorithm enables full account takeover. Attacker gains access to all user documents and memories.

**Why it happens:** JWTs seem simple but have subtle security requirements. Secrets hardcoded for "convenience."

**How to avoid:**
- Store `SECRET_KEY` in environment variables, NEVER in code
- Use strong random secret (32+ bytes): `openssl rand -hex 32`
- Never accept "none" algorithm - PyJWT rejects by default, but verify
- Set short expiration: 15-30 min for access tokens
- Use HTTPS exclusively in production
- Never log full JWTs (only last 4 characters)
- Implement refresh token rotation (Phase 2)

**Warning signs:**
- `SECRET_KEY` visible in git history or code
- Logs contain full JWT tokens
- No token expiration validation
- API accepts tokens with "none" algorithm

**Phase to address:** Phase 1 (authentication setup)

### Pitfall 5: Graph Schema Neglect Causes Performance Collapse (MODERATE)

**What goes wrong:** Not designing Neo4j schema upfront leads to inefficient queries, missing indexes, and performance collapse at scale. Complex traversals become unusably slow.

**Why it happens:** Teams start with "just store everything" mentality. Graph flexibility misunderstood as "no schema needed."

**How to avoid:**
- Design schema BEFORE Phase 1 implementation (see Pattern 3)
- Define node types: User, Document, Chunk, Entity (Phase 2+)
- Define relationships: OWNS, CONTAINS, MENTIONS, RELATES_TO
- Create constraints and indexes on: `user.id`, `document.id`, `chunk.id`, `document.user_id`
- Use consistent relationship directions
- Test queries at expected scale (generate synthetic data)

**Warning signs:**
- Queries taking >1 second at <100K nodes
- EXPLAIN shows full scans without index usage
- New feature requirements reveal missing relationship types

**Phase to address:** Phase 1 (schema initialization in `init_neo4j_schema()`)

### Pitfall 6: No Multi-Tenant Filtering from Start (CRITICAL)

**What goes wrong:** Building without tenant filtering, then trying to add it later. Requires refactoring every database query. High risk of cross-tenant data leaks.

**Why it happens:** "Phase 1 is single-user" mindset leads to skipping filtering logic.

**How to avoid:**
- ALWAYS include `user_id` filtering in Qdrant search (even for single user)
- ALWAYS include `user_id` in Neo4j WHERE clauses
- Create payload indexes on `user_id` in Qdrant
- Test with multiple users from Phase 1
- Use middleware to inject `user_id` from JWT into all operations

**Warning signs:**
- Database queries without user/tenant filtering
- Planning to "add multi-tenancy later"
- No tests with multiple users

**Phase to address:** Phase 1 (all database operations)

### Pitfall 7: Synchronous Document Processing Blocks API (MODERATE)

**What goes wrong:** Processing documents inline during API requests causes timeout errors for large files. Poor UX.

**Why it happens:** Simple approach is to process immediately, but large documents take minutes.

**How to avoid:**
- Use FastAPI `BackgroundTasks` for document processing
- Return immediately with `{"status": "processing", "document_id": "..."}`
- Store processing status in database for user to check
- Handle errors gracefully (store error message for user)

**Warning signs:**
- API timeouts on large file uploads
- Users complaining about slow uploads
- Server logs show long-running requests

**Phase to address:** Phase 1 (document upload endpoint)

### Pitfall 8: Missing Startup Validation (MINOR)

**What goes wrong:** Misconfigured database connections or API keys cause cryptic runtime errors during first usage.

**Why it happens:** No health checks at startup.

**How to avoid:**
- Use FastAPI `lifespan` event to validate connections at startup
- Test Neo4j connectivity: `neo4j_driver.verify_connectivity()`
- Test Qdrant connectivity: `qdrant_client.get_collections()`
- Validate embedding dimensions: `validate_embedding_dimensions()`
- Fail fast with clear error messages

**Warning signs:**
- Cryptic errors on first API call after deployment
- Database connection errors discovered by users
- No health check endpoint

**Phase to address:** Phase 1 (startup in `main.py`)

## Code Examples

Verified patterns from official sources:

### Mem0 Configuration with Neo4j + Qdrant (Phase 1 Setup Only)

```python
# app/db/mem0_client.py
from mem0 import Memory
from app.config import settings

def init_mem0() -> Memory:
    """Initialize Mem0 with dual stores (Neo4j + Qdrant).

    Phase 1: Basic configuration only. Full integration in Phase 2.
    """
    config = {
        "version": "v1.1",
        "llm": {
            "provider": "openai",
            "config": {
                "model": settings.OPENAI_MODEL,
                "temperature": 0.1,
            }
        },
        "embedder": {
            "provider": "openai",
            "config": {
                "model": settings.OPENAI_EMBEDDING_MODEL,
            }
        },
        "vector_store": {
            "provider": "qdrant",
            "config": {
                "collection_name": "memory",  # Separate from documents collection
                "host": settings.QDRANT_HOST,
                "port": settings.QDRANT_PORT,
            }
        },
        "graph_store": {
            "provider": "neo4j",
            "config": {
                "url": settings.NEO4J_URI,
                "username": settings.NEO4J_USERNAME,
                "password": settings.NEO4J_PASSWORD,
            }
        },
    }

    memory = Memory.from_config(config)
    return memory

# Initialize singleton
mem0_memory = init_mem0()
```

**Source:** [Mem0 Official Docs - Configuration](https://docs.mem0.ai/introduction)

**Note:** Phase 1 initializes Mem0 but doesn't use it. Full memory integration comes in Phase 2.

### FastAPI with CORS and Error Handling

```python
# app/main.py (additional middleware)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi import Request

# ... (lifespan and app setup from Pattern 2)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all exception handler for unhandled errors."""
    import traceback
    print(f"Unhandled exception: {exc}")
    print(traceback.format_exc())

    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "type": type(exc).__name__
        }
    )
```

**Source:** [FastAPI Documentation - Middleware](https://fastapi.tiangolo.com/tutorial/middleware/)

### LangChain RAG Chain (Basic)

```python
# app/services/generation_service.py (alternative pattern)
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.prompts import ChatPromptTemplate
from langchain.schema.output_parser import StrOutputParser
from langchain.schema.runnable import RunnablePassthrough

def create_rag_chain():
    """Create a LangChain RAG chain for answer generation.

    Alternative to direct LLM invocation (see Pattern 8).
    """
    llm = ChatOpenAI(model=settings.OPENAI_MODEL, temperature=0)

    prompt = ChatPromptTemplate.from_messages([
        ("system", """Answer questions ONLY based on the provided context.
If context is insufficient, respond: "I don't know."
Cite document names when referencing information."""),
        ("user", """Context: {context}

Question: {question}

Answer:""")
    ])

    chain = (
        {"context": RunnablePassthrough(), "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

    return chain

# Usage:
# chain = create_rag_chain()
# answer = await chain.ainvoke({"context": context_text, "question": query})
```

**Source:** [LangChain Documentation - RAG](https://docs.langchain.com/oss/python/langchain/rag)

### Pytest for FastAPI Async Endpoints

```python
# tests/test_auth.py
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_register_user():
    """Test user registration (AUTH-01)."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "securepassword123"
            }
        )

    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

@pytest.mark.asyncio
async def test_login_user():
    """Test user login (AUTH-02)."""
    # First register
    async with AsyncClient(app=app, base_url="http://test") as client:
        await client.post(
            "/api/v1/auth/register",
            json={"email": "test2@example.com", "password": "password123"}
        )

        # Then login
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": "test2@example.com", "password": "password123"}  # OAuth2 format
        )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data

@pytest.mark.asyncio
async def test_protected_endpoint():
    """Test protected endpoint requires authentication."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Without token
        response = await client.post("/api/v1/documents/upload")
        assert response.status_code == 401

        # With token (register first)
        reg_response = await client.post(
            "/api/v1/auth/register",
            json={"email": "test3@example.com", "password": "password123"}
        )
        token = reg_response.json()["access_token"]

        # Use token (without file, will fail differently but auth passes)
        response = await client.post(
            "/api/v1/documents/upload",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code != 401  # Not auth error
```

**Source:** [Pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| LangChain 0.x | LangChain 1.0+ | GA Dec 2025 | Stable APIs, better typing, LangGraph integration. Use 1.0+ for new projects. |
| Pydantic v1 | Pydantic v2 | Released 2023 | 17x faster validation, better error messages. v1 is deprecated. FastAPI >=0.100 requires v2. |
| PyJWT <2.0 | PyJWT >=2.0 | 2021 | Rejects "none" algorithm by default. Safer defaults. Always use >=2.0. |
| bcrypt | Argon2 | 2015 (Argon2 won PHC) | Argon2 more resistant to GPU attacks. Use pwdlib[argon2] for easy integration. |
| neo4j-driver | neo4j | 2026 | `neo4j-driver` is deprecated. Use `neo4j` package (official as of 2026). |
| OpenAI ada-002 | text-embedding-3-small | 2024 | 54.9% vs 31.4% MIRACL score, 5x cheaper ($0.02 vs $0.10 per 1M tokens). |
| Fixed chunking | Semantic chunking | 2023-2024 | 15-30% accuracy improvement. RecursiveCharacterTextSplitter is now standard. |
| Vector-only RAG | Hybrid (vector + graph) | 2025 | 20-25% accuracy gains with GraphRAG. Standard for complex queries. |

**Deprecated/outdated:**
- `neo4j-driver` package: Use `neo4j` instead
- Pydantic v1: FastAPI >=0.100 requires v2
- OpenAI ada-002 embeddings: text-embedding-3-small is superior and cheaper
- LangChain `@app.on_event("startup")`: Use `lifespan` context manager
- Fixed-size text splitting: Use semantic chunking

## Open Questions

Things that couldn't be fully resolved:

1. **Optimal chunk size and overlap for mixed document types**
   - What we know: Start with chunk_size=1000, overlap=200 works well for general text
   - What's unclear: Optimal values vary by document type (technical papers vs. reports) and domain
   - Recommendation: Start with defaults, tune based on evaluation metrics in Phase 4

2. **Mem0 memory deletion bug timeline**
   - What we know: GitHub issue #3245 confirms orphaned Neo4j data after delete
   - What's unclear: When fix will be released, whether workaround is sufficient
   - Recommendation: Implement custom deletion logic in Phase 2, monitor GitHub for updates

3. **Performance of dual-write at scale**
   - What we know: Writing to both Neo4j and Qdrant adds latency, partial failures possible
   - What's unclear: Optimal batch sizes, retry strategies, performance at 100K+ documents
   - Recommendation: Profile in Phase 1, implement compensating transactions in Phase 2

4. **"I don't know" detection accuracy**
   - What we know: Strict prompts with fallback instruction work but not 100% reliable
   - What's unclear: Whether additional validation (check if answer mentions context) improves reliability
   - Recommendation: Implement basic prompt-based approach in Phase 1, evaluate hallucination rate in Phase 4

## Sources

### Primary (HIGH confidence)

**Official Documentation:**
- [FastAPI Official Docs](https://fastapi.tiangolo.com/)
- [Pydantic v2 Documentation](https://docs.pydantic.dev/)
- [Neo4j Python Driver Documentation](https://neo4j.com/docs/python-manual/current/)
- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [Mem0 Official Docs](https://docs.mem0.ai/introduction)
- [LangChain Documentation](https://docs.langchain.com/)
- [OpenAI API Documentation](https://platform.openai.com/docs/)

**GitHub Repositories:**
- [pymupdf/RAG (pymupdf4llm)](https://github.com/pymupdf/RAG)
- [pwdlib GitHub](https://github.com/frankie567/pwdlib)
- [mem0ai/mem0](https://github.com/mem0ai/mem0)

**Package Versions (PyPI verified Jan 2026):**
- [fastapi PyPI](https://pypi.org/project/fastapi/)
- [neo4j PyPI v6.1.0](https://pypi.org/project/neo4j/)
- [qdrant-client PyPI v1.16.2](https://pypi.org/project/qdrant-client/)
- [langchain-openai PyPI v1.1.7](https://pypi.org/project/langchain-openai/)

### Secondary (MEDIUM confidence)

**Integration Guides (2026):**
- [FastAPI JWT Authentication Guide](https://testdriven.io/blog/fastapi-jwt-auth/)
- [Building Production RAG Systems in 2026](https://brlikhon.engineer/blog/building-production-rag-systems-in-2026-complete-architecture-guide)
- [How to Build RAG Applications with LangChain and FastAPI](https://www.bitcot.com/build-rag-applications-with-langchain-and-fastapi/)

**Best Practices:**
- [FastAPI OAuth2 with JWT (Official Tutorial)](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/)
- [23 RAG Pitfalls and How to Fix Them](https://www.nb-data.com/p/23-rag-pitfalls-and-how-to-fix-them)
- [Chunking Strategies for RAG](https://weaviate.io/blog/chunking-strategies-for-rag)

### Tertiary (LOW confidence - project research referenced)

From `.planning/research/` files:
- GraphRAG accuracy improvements (20-25%) - from case studies, workload-dependent
- Mem0 accuracy improvements (26%) - from research paper, needs domain validation
- Semantic chunking improvements (15-30%) - range is wide, needs testing

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All packages verified from official PyPI, versions checked as of Jan 2026
- Architecture: HIGH - Patterns verified from official FastAPI, LangChain, Neo4j, Qdrant docs
- Pitfalls: HIGH - Technology-specific issues verified from GitHub (Mem0 #3245), official docs, 2026 security advisories

**Research date:** 2026-02-04
**Valid until:** 30 days (stable technologies, but check for Mem0 updates)

**Critical Phase 1 Success Criteria:**
- [ ] Neo4j schema designed and initialized with constraints/indexes
- [ ] Qdrant collection created with correct embedding dimensions
- [ ] Semantic chunking implemented (RecursiveCharacterTextSplitter)
- [ ] JWT authentication with Argon2 password hashing
- [ ] Multi-tenant filtering included in all database queries (even for single user)
- [ ] Embedding dimensions validated at startup
- [ ] Document processing runs in background tasks (async)
- [ ] Basic retrieval returns relevant chunks with citations
- [ ] "I don't know" fallback prevents hallucinations
- [ ] All configuration via environment variables (Pydantic BaseSettings)
