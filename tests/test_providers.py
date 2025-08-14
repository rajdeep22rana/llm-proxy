import pytest
from app.providers.llm import get_llm_provider, StubProvider


def test_default_provider(monkeypatch):
    # Without LLM_PROVIDER env var, should default to StubProvider
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    provider = get_llm_provider()
    assert isinstance(provider, StubProvider)


def test_unknown_provider(monkeypatch):
    # Unknown provider names should raise RuntimeError
    monkeypatch.setenv("LLM_PROVIDER", "unknown")
    with pytest.raises(RuntimeError) as excinfo:
        get_llm_provider()
    assert "Unknown LLM_PROVIDER" in str(excinfo.value)
