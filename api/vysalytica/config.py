"""
Configuration helper utilities for Vysalytica.

Values are resolved from Streamlit's secrets when available and fall back to
standard environment variables. Typed accessors centralize defaults and any
normalization required by the application.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any, Optional

DEFAULT_ROUTELLM_API_KEY = "s2_887db278b1b24f14b49fe0294436e87a"
DEFAULT_ROUTELLM_BASE_URL = "https://api.abacus.ai/v1"
DEFAULT_ROUTELLM_MODEL = "gpt-3.5-turbo"
DEFAULT_DATABASE_URL = "sqlite:///vysalytica.db"
DEFAULT_API_BASE_URL = "http://localhost:8080/api"

try:
    import streamlit as _st  # type: ignore
except Exception:  # pragma: no cover - streamlit not always available
    _st = None


def _normalize_value(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
    else:
        cleaned = str(value).strip()
    return cleaned or None


def _get_from_streamlit(key: str) -> Optional[str]:
    if _st is None:
        return None
    try:
        secrets = _st.secrets
    except Exception:
        return None

    try:
        if key in secrets:
            return _normalize_value(secrets[key])
    except Exception:
        return None
    return None


@lru_cache(maxsize=None)
def _get_value(key: str) -> Optional[str]:
    secret_value = _get_from_streamlit(key)
    if secret_value is not None:
        return secret_value
    return _normalize_value(os.getenv(key))


def clear_cached_config() -> None:
    """Clear cached configuration lookups (useful in tests)."""
    _get_value.cache_clear()  # type: ignore[attr-defined]


def get_routellm_api_key() -> Optional[str]:
    """Return the configured RouteLLM API key, if any."""
    return _get_value("ROUTELLM_API_KEY") or DEFAULT_ROUTELLM_API_KEY


def get_routellm_base_url() -> str:
    """Return the RouteLLM base URL with default fallback."""
    return _get_value("ROUTELLM_BASE_URL") or DEFAULT_ROUTELLM_BASE_URL


def get_routellm_model() -> str:
    """Return the RouteLLM model name with default fallback."""
    return _get_value("ROUTELLM_MODEL") or DEFAULT_ROUTELLM_MODEL


def get_openai_api_key() -> Optional[str]:
    """Return the configured OpenAI API key, if present."""
    return _get_value("OPENAI_API_KEY")


def get_anthropic_api_key() -> Optional[str]:
    """Return the configured Anthropic API key, if present."""
    return _get_value("ANTHROPIC_API_KEY")


def _normalize_database_url(url: str) -> str:
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql://") and "+psycopg" not in url:
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def get_database_url() -> str:
    """Return the database URL, normalized for SQLAlchemy."""
    raw_url = _get_value("DATABASE_URL") or DEFAULT_DATABASE_URL
    return _normalize_database_url(raw_url)


def _strip_trailing_slashes(url: str) -> str:
    normalized = url
    while normalized.endswith("/") and not normalized.endswith("://"):
        normalized = normalized[:-1]
    return normalized


def get_api_base_url() -> str:
    """Return the API base URL used by Streamlit and other clients."""
    raw_url = _get_value("API_BASE_URL") or DEFAULT_API_BASE_URL
    return _strip_trailing_slashes(raw_url)


def debug_openai_client_info():
    """Debug OpenAI client initialization parameters."""
    try:
        from openai import OpenAI
        import inspect

        init_sig = inspect.signature(OpenAI.__init__)
        params = list(init_sig.parameters.keys())
        print(f"OpenAI client accepts parameters: {params}")
        print(f"OpenAI client version: {getattr(OpenAI, '__version__', 'unknown')}")
    except Exception as e:
        print(f"Failed to debug OpenAI client: {e}")


def create_openai_client_safe(**kwargs):
    """Create OpenAI client with explicit 'proxies' removal to prevent RouteLLM initialization errors."""
    # Remove proxies if present (defensive measure against library version conflicts)
    kwargs.pop('proxies', None)
    from openai import OpenAI
    return OpenAI(**kwargs)


def create_anthropic_client_safe(**kwargs):
    """Create Anthropic client with explicit 'proxies' removal to prevent initialization errors."""
    # Remove proxies if present (defensive measure against library version conflicts)
    kwargs.pop('proxies', None)
    import anthropic
    return anthropic.Anthropic(**kwargs)


__all__ = [
    "DEFAULT_API_BASE_URL",
    "DEFAULT_DATABASE_URL",
    "DEFAULT_ROUTELLM_API_KEY",
    "DEFAULT_ROUTELLM_BASE_URL",
    "DEFAULT_ROUTELLM_MODEL",
    "clear_cached_config",
    "create_anthropic_client_safe",
    "create_openai_client_safe",
    "debug_openai_client_info",
    "get_anthropic_api_key",
    "get_api_base_url",
    "get_database_url",
    "get_openai_api_key",
    "get_routellm_api_key",
    "get_routellm_base_url",
    "get_routellm_model",
]
