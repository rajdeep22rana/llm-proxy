import os
from typing import Dict
from app.providers.base import LLMProvider
from app.providers.stub import StubProvider

# Mapping format example (env MODEL_PROVIDER_MAP):
# "gpt-4=stub,claude-3=openai,local-*=stub"


def parse_model_provider_map(raw: str | None) -> Dict[str, str]:
    if not raw:
        return {}
    mapping: Dict[str, str] = {}
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if "=" not in part:
            continue
        model_key, provider_name = part.split("=", 1)
        mapping[model_key.strip()] = provider_name.strip().lower()
    return mapping


def resolve_provider_name_for_model(model: str, mapping: Dict[str, str]) -> str:
    # exact match first
    if model in mapping:
        return mapping[model]
    # prefix match with trailing * (e.g., "gpt-*=")
    for key, provider in mapping.items():
        if key.endswith("*"):
            prefix = key[:-1]
            if model.startswith(prefix):
                return provider
    # default from LLM_PROVIDER env or stub
    return os.getenv("LLM_PROVIDER", "stub").lower()


_provider_cache: Dict[str, LLMProvider] = {}


def get_provider_by_name(name: str) -> LLMProvider:
    name = (name or "stub").lower()
    # Common aliases for OpenAI-compatible backends
    openai_compat_aliases = {
        "ollama",
        "openai",
        "openai_compat",
        "openai-compatible",
        "compat",
        "vllm",
        "localai",
        "lmstudio",
        "llamacpp",
        "llama.cpp",
    }
    if name in openai_compat_aliases:
        # Import here to avoid circular imports at module load time
        from app.providers.openai_compat import OpenAICompatibleProvider

        # Cache provider instances by normalized name to enable connection reuse
        if name not in _provider_cache:
            _provider_cache[name] = OpenAICompatibleProvider()
        return _provider_cache[name]
    # fallback
    if name not in _provider_cache:
        _provider_cache[name] = StubProvider()
    return _provider_cache[name]


def resolve_provider_for_model(model: str) -> LLMProvider:
    mapping = parse_model_provider_map(os.getenv("MODEL_PROVIDER_MAP"))
    provider_name = resolve_provider_name_for_model(model, mapping)
    return get_provider_by_name(provider_name)


async def close_all_providers() -> None:
    """Close any provider resources (e.g., shared HTTP clients) on shutdown."""
    # Import type locally to avoid circular import for optional methods
    for provider in list(_provider_cache.values()):
        # Providers may optionally expose an async `aclose()`
        aclose = getattr(provider, "aclose", None)
        if callable(aclose):
            try:
                await aclose()  # type: ignore[misc]
            except Exception:
                # Best-effort cleanup; avoid raising during shutdown
                pass
