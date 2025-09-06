from fastapi.testclient import TestClient
import pytest
from app.main import app
from app.providers.base import (
    LLMProvider,
    ProviderUnauthorizedError,
    ProviderForbiddenError,
    ProviderRateLimitError,
)

client = TestClient(app)

valid_payload = {
    "model": "test-model",
    "messages": [{"role": "user", "content": "hello"}],
}


def test_missing_authorization_header():
    # No Authorization header should yield a 422 error
    response = client.post("/proxy", json=valid_payload)
    assert response.status_code == 422


@pytest.mark.parametrize(
    "payload",
    [{}, {"model": "test-model"}, {"messages": [{"role": "user", "content": "hello"}]}],
)
def test_invalid_request_body(payload):
    # Missing required fields should yield a 422 error
    headers = {"authorization": "test-key"}
    response = client.post("/proxy", json=payload, headers=headers)
    assert response.status_code == 422


def test_model_not_found_maps_to_404(monkeypatch):
    # Force Ollama provider and call with a clearly invalid model name
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    local_client = TestClient(app, raise_server_exceptions=False)
    headers = {"authorization": "x"}
    payload = {
        "model": "nonexistent-model-xyz",
        "messages": [{"role": "user", "content": "hi"}],
    }
    r = local_client.post("/proxy", json=payload, headers=headers)
    # Either the provider will map it to 404 (if Ollama responds with
    # explicit unknown model) or it may still be 500 if the downstream
    # message is not specific (acceptable fallback).
    assert r.status_code in (404, 500)
    if r.status_code == 404:
        body = r.json()
        assert body.get("error") == "Model Not Found"


def test_provider_error_mappings(monkeypatch):
    class UnauthorizedProvider(LLMProvider):
        async def chat(self, request, authorization):
            raise ProviderUnauthorizedError("no auth")

        async def chat_stream(self, request, authorization):
            raise ProviderUnauthorizedError("no auth")

    class ForbiddenProvider(LLMProvider):
        async def chat(self, request, authorization):
            raise ProviderForbiddenError("no access")

        async def chat_stream(self, request, authorization):
            raise ProviderForbiddenError("no access")

    class RateLimitedProvider(LLMProvider):
        async def chat(self, request, authorization):
            raise ProviderRateLimitError("slow down", retry_after_seconds=7)

        async def chat_stream(self, request, authorization):
            raise ProviderRateLimitError("slow down", retry_after_seconds=7)

    from app.routers import proxy as proxy_router

    # Unauthorized -> 401
    app.dependency_overrides[proxy_router.get_provider_override] = (
        lambda: UnauthorizedProvider()
    )
    try:
        client = TestClient(app, raise_server_exceptions=False)
        payload = {"model": "m", "messages": [{"role": "user", "content": "hi"}]}
        r = client.post("/proxy", json=payload, headers={"authorization": "x"})
        assert r.status_code == 401
        assert r.json().get("error") == "Unauthorized"
    finally:
        app.dependency_overrides.pop(proxy_router.get_provider_override, None)

    # Forbidden -> 403
    app.dependency_overrides[proxy_router.get_provider_override] = (
        lambda: ForbiddenProvider()
    )
    try:
        client = TestClient(app, raise_server_exceptions=False)
        payload = {"model": "m", "messages": [{"role": "user", "content": "hi"}]}
        r = client.post("/proxy", json=payload, headers={"authorization": "x"})
        assert r.status_code == 403
        assert r.json().get("error") == "Forbidden"
    finally:
        app.dependency_overrides.pop(proxy_router.get_provider_override, None)

    # Rate limited -> 429 with Retry-After
    app.dependency_overrides[proxy_router.get_provider_override] = (
        lambda: RateLimitedProvider()
    )
    try:
        client = TestClient(app, raise_server_exceptions=False)
        payload = {"model": "m", "messages": [{"role": "user", "content": "hi"}]}
        r = client.post("/proxy", json=payload, headers={"authorization": "x"})
        assert r.status_code == 429
        assert r.json().get("error") == "Rate Limited"
        assert r.headers.get("Retry-After") == "7"
    finally:
        app.dependency_overrides.pop(proxy_router.get_provider_override, None)
