"""LLM and Embedding provider factory for multi-provider support.

Supports OpenAI, Ollama, and Anthropic (Claude).
OpenAI provider also works with any OpenAI-compatible API (Groq, DeepSeek, Azure, etc.)
via the OPENAI_BASE_URL setting.

Uses LangChain's base classes to ensure a unified interface across providers.

Configuration is driven by environment variables:
- LLM_PROVIDER: "openai", "ollama", or "anthropic"
- EMBEDDING_PROVIDER: "openai" or "ollama"
"""

import logging
from typing import Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.embeddings import Embeddings

from app.config import settings

logger = logging.getLogger(__name__)


def get_llm(
    temperature: float = 0,
    streaming: bool = False,
    logprobs: bool = False,
    provider: Optional[str] = None,
) -> BaseChatModel:
    """Create an LLM instance based on the configured provider.

    Args:
        temperature: Sampling temperature (0 = deterministic).
        streaming: Enable streaming for token-by-token output.
        logprobs: Enable log probabilities (OpenAI only, ignored for others).
        provider: Override the configured provider. If None, uses settings.LLM_PROVIDER.

    Returns:
        A LangChain BaseChatModel instance.

    Raises:
        ValueError: If the provider is not supported.
    """
    provider = (provider or settings.LLM_PROVIDER).lower()

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        kwargs = {
            "model": settings.OPENAI_MODEL,
            "temperature": temperature,
            "openai_api_key": settings.OPENAI_API_KEY,
            "streaming": streaming,
        }
        if logprobs:
            kwargs["logprobs"] = True
        if settings.OPENAI_BASE_URL:
            kwargs["openai_api_base"] = settings.OPENAI_BASE_URL

        return ChatOpenAI(**kwargs)

    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        kwargs = {
            "model": settings.ANTHROPIC_MODEL,
            "temperature": temperature,
            "anthropic_api_key": settings.ANTHROPIC_API_KEY,
            "streaming": streaming,
        }

        return ChatAnthropic(**kwargs)

    elif provider == "ollama":
        from langchain_ollama import ChatOllama

        kwargs = {
            "model": settings.OLLAMA_MODEL,
            "temperature": temperature,
            "base_url": settings.OLLAMA_BASE_URL,
        }

        return ChatOllama(**kwargs)

    else:
        raise ValueError(
            f"Unsupported LLM provider: '{provider}'. "
            f"Supported: openai, anthropic, ollama"
        )


def get_embedding_model(provider: Optional[str] = None) -> Embeddings:
    """Create an Embedding model instance based on the configured provider.

    Args:
        provider: Override the configured provider. If None, uses settings.EMBEDDING_PROVIDER.

    Returns:
        A LangChain Embeddings instance.

    Raises:
        ValueError: If the provider is not supported.
    """
    provider = (provider or settings.EMBEDDING_PROVIDER).lower()

    if provider == "openai":
        from langchain_openai import OpenAIEmbeddings

        kwargs = {
            "model": settings.OPENAI_EMBEDDING_MODEL,
            "openai_api_key": settings.OPENAI_API_KEY,
        }
        if settings.OPENAI_BASE_URL:
            kwargs["openai_api_base"] = settings.OPENAI_BASE_URL

        return OpenAIEmbeddings(**kwargs)

    elif provider == "ollama":
        from langchain_ollama import OllamaEmbeddings

        return OllamaEmbeddings(
            model=settings.OLLAMA_EMBEDDING_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
        )

    else:
        raise ValueError(
            f"Unsupported embedding provider: '{provider}'. "
            f"Supported: openai, ollama "
            f"(Anthropic does not provide embeddings — use openai or ollama for EMBEDDING_PROVIDER)"
        )


def supports_logprobs(provider: Optional[str] = None) -> bool:
    """Check if the configured LLM provider supports logprobs.

    Args:
        provider: Override the configured provider. If None, uses settings.LLM_PROVIDER.

    Returns:
        True if the provider supports logprobs, False otherwise.
    """
    provider = (provider or settings.LLM_PROVIDER).lower()
    return provider == "openai"
