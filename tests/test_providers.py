from app.providers.registry import get_provider_by_name
from app.providers.stub import StubProvider


def test_default_provider(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    provider = get_provider_by_name(None)
    assert isinstance(provider, StubProvider)


def test_unknown_provider():
    provider = get_provider_by_name("unknown")
    assert isinstance(provider, StubProvider)
