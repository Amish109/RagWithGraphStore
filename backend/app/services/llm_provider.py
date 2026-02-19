"""LLM and Embedding provider factory for multi-provider support.

Supports OpenAI, Ollama, Anthropic (Claude), and OpenRouter.
OpenRouter gives access to 200+ models (GPT-4o, Claude, Llama, Gemini, Mistral, etc.)
via a single API key, using the OpenAI-compatible API format.

Uses LangChain's base classes to ensure a unified interface across providers.

Configuration is driven by environment variables:
- LLM_PROVIDER: "openai", "ollama", "anthropic", or "openrouter"
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
    model: Optional[str] = None,
) -> BaseChatModel:
    """Create an LLM instance based on the configured provider.

    Args:
        temperature: Sampling temperature (0 = deterministic).
        streaming: Enable streaming for token-by-token output.
        logprobs: Enable log probabilities (OpenAI/OpenRouter only, ignored for others).
        provider: Override the configured provider. If None, uses settings.LLM_PROVIDER.
        model: Override the model name. If None, uses provider default from settings.

    Returns:
        A LangChain BaseChatModel instance.

    Raises:
        ValueError: If the provider is not supported.
    """
    provider = (provider or settings.LLM_PROVIDER).lower()

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        kwargs = {
            "model": model or settings.OPENAI_MODEL,
            "temperature": temperature,
            "openai_api_key": settings.OPENAI_API_KEY,
            "streaming": streaming,
        }
        if logprobs:
            kwargs["logprobs"] = True
        if settings.OPENAI_BASE_URL:
            kwargs["openai_api_base"] = settings.OPENAI_BASE_URL

        return ChatOpenAI(**kwargs)

    elif provider == "openrouter":
        from langchain_openai import ChatOpenAI

        kwargs = {
            "model": model or settings.OPENROUTER_MODEL,
            "temperature": temperature,
            "openai_api_key": settings.OPENROUTER_API_KEY,
            "openai_api_base": settings.OPENROUTER_BASE_URL,
            "streaming": streaming,
            "default_headers": {
                "HTTP-Referer": "http://localhost:3000",
                "X-Title": "RAG With GraphStore",
            },
        }
        if logprobs:
            kwargs["logprobs"] = True

        return ChatOpenAI(**kwargs)

    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        kwargs = {
            "model": model or settings.ANTHROPIC_MODEL,
            "temperature": temperature,
            "anthropic_api_key": settings.ANTHROPIC_API_KEY,
            "streaming": streaming,
        }

        return ChatAnthropic(**kwargs)

    elif provider == "ollama":
        from langchain_ollama import ChatOllama

        kwargs = {
            "model": model or settings.OLLAMA_MODEL,
            "temperature": temperature,
            "base_url": settings.OLLAMA_BASE_URL,
        }

        return ChatOllama(**kwargs)

    else:
        raise ValueError(
            f"Unsupported LLM provider: '{provider}'. "
            f"Supported: openai, openrouter, anthropic, ollama"
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
            f"(Anthropic/OpenRouter do not provide embeddings — use openai or ollama for EMBEDDING_PROVIDER)"
        )


def supports_logprobs(provider: Optional[str] = None) -> bool:
    """Check if the configured LLM provider supports logprobs.

    Args:
        provider: Override the configured provider. If None, uses settings.LLM_PROVIDER.

    Returns:
        True if the provider supports logprobs, False otherwise.
    """
    provider = (provider or settings.LLM_PROVIDER).lower()
    return provider in ("openai", "openrouter")


def supports_tool_calling(provider: Optional[str] = None) -> bool:
    """Check if the configured LLM provider supports tool calling via bind_tools().

    Args:
        provider: Override the configured provider. If None, uses settings.LLM_PROVIDER.

    Returns:
        True if the provider supports tool calling, False otherwise.
    """
    provider = (provider or settings.LLM_PROVIDER).lower()
    return provider in ("openai", "anthropic", "openrouter")
