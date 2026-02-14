"""Application configuration loaded from environment variables.

Uses Pydantic BaseSettings for type-safe configuration with validation.
Required fields will raise ValidationError at startup if not set.
"""

from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # API Settings
    PROJECT_NAME: str = "RAG with Memory Management"
    VERSION: str = "0.1.0"
    API_V1_PREFIX: str = "/api/v1"

    # Security
    SECRET_KEY: str  # REQUIRED - for JWT signing
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_MAX_CONNECTIONS: int = 50

    # Token Configuration
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JTI_BLOCKLIST_EXPIRE_SECONDS: int = 604800  # 7 days, match refresh lifetime

    # Anonymous Session Configuration
    ANONYMOUS_SESSION_EXPIRE_DAYS: int = 7
    ANONYMOUS_PREFIX: str = "anon_"
    COOKIE_SECURE: bool = False  # Set True for production (HTTPS required)
    COOKIE_SAMESITE: str = "lax"

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

    # LLM Provider Selection
    # Supported: "openai", "ollama", "anthropic"
    # Use "openai" + OPENAI_BASE_URL for any OpenAI-compatible API (Groq, DeepSeek, etc.)
    LLM_PROVIDER: str = "openai"
    EMBEDDING_PROVIDER: str = "openai"  # "openai" or "ollama" (Anthropic has no embeddings)

    # OpenAI Configuration (used when provider = "openai")
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OPENAI_EMBEDDING_DIMENSIONS: int = 1536
    OPENAI_BASE_URL: Optional[str] = None  # Custom base URL (Azure, Groq, DeepSeek, etc.)

    # Anthropic Configuration (used when LLM_PROVIDER = "anthropic")
    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_MODEL: str = "claude-sonnet-4-5-20250929"

    # Ollama Configuration (used when provider = "ollama")
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2"
    OLLAMA_EMBEDDING_MODEL: str = "nomic-embed-text"
    OLLAMA_EMBEDDING_DIMENSIONS: int = 768

    @property
    def EMBEDDING_DIMENSIONS(self) -> int:
        """Return embedding dimensions for the active provider."""
        if self.EMBEDDING_PROVIDER.lower() == "ollama":
            return self.OLLAMA_EMBEDDING_DIMENSIONS
        return self.OPENAI_EMBEDDING_DIMENSIONS

    # Document Processing
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    MAX_UPLOAD_SIZE_MB: int = 50

    # Logging
    LOG_LEVEL: str = "INFO"

    # Memory Configuration
    SHARED_MEMORY_USER_ID: str = "__shared__"  # Sentinel for company-wide memory

    # TTL Cleanup Configuration
    ANONYMOUS_DATA_TTL_DAYS: int = 7  # How long to keep anonymous data
    CLEANUP_SCHEDULE_HOUR: int = 3  # Run cleanup at 3 AM

    # PostgreSQL Configuration (for LangGraph checkpointing)
    POSTGRES_URI: str = "postgresql://postgres:password@localhost:5432/ragapp"
    POSTGRES_POOL_SIZE: int = 5

    # Memory Management Configuration
    MEMORY_MAX_TOKENS: int = 4000
    MEMORY_SUMMARIZATION_THRESHOLD: float = 0.75

    # GraphRAG Configuration
    GRAPHRAG_ENABLED: bool = True  # Master toggle for entity extraction during upload
    GRAPHRAG_MAX_ENTITIES_PER_CHUNK: int = 20
    GRAPHRAG_MAX_HOPS: int = 2


# Global settings instance
settings = Settings()
