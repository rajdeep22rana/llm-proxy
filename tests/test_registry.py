import os
from app.providers.registry import (
    parse_model_provider_map,
    resolve_provider_name_for_model,
    resolve_provider_for_model,
)


def test_parse_model_provider_map_basic():
    raw = "gpt-4=openai, local-*=stub,invalid, ,x=y"
    mapping = parse_model_provider_map(raw)
    assert mapping == {"gpt-4": "openai", "local-*": "stub", "x": "y"}


def test_resolve_provider_exact_and_wildcard():
    mapping = {"gpt-4": "openai", "local-*": "stub"}
    assert resolve_provider_name_for_model("gpt-4", mapping) == "openai"
    assert resolve_provider_name_for_model("local-7b", mapping) == "stub"
    # unknown falls back to env or stub
    os.environ.pop("LLM_PROVIDER", None)
    assert resolve_provider_name_for_model("unknown", mapping) == "stub"


def test_resolve_provider_for_model_integration(monkeypatch):
    monkeypatch.setenv("MODEL_PROVIDER_MAP", "gpt-4=ollama,foo-*=stub")
    monkeypatch.setenv("LLM_PROVIDER", "stub")
    # Ensure resolution returns a provider instance without crashing
    from app.providers.base import LLMProvider

    provider = resolve_provider_for_model("gpt-4")
    assert isinstance(provider, LLMProvider)
    provider2 = resolve_provider_for_model("foo-7b")
    assert isinstance(provider2, LLMProvider)
