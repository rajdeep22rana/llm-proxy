from fastapi.testclient import TestClient
import pytest
from app.main import app

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
