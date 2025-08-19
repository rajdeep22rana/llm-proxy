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


def get_provider_by_name(name: str) -> LLMProvider:
    name = (name or "stub").lower()
    if name in {"ollama"}:
        # Import here to avoid circular imports at module load time
        from app.providers.openai_compat import OpenAICompatibleProvider

        return OpenAICompatibleProvider()
    # fallback
    return StubProvider()


def resolve_provider_for_model(model: str) -> LLMProvider:
    mapping = parse_model_provider_map(os.getenv("MODEL_PROVIDER_MAP"))
    provider_name = resolve_provider_name_for_model(model, mapping)
    return get_provider_by_name(provider_name)
