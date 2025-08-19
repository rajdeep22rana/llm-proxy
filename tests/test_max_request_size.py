import importlib
from fastapi.testclient import TestClient


def build_client(monkeypatch, max_bytes: int) -> TestClient:
    monkeypatch.setenv("MAX_REQUEST_BYTES", str(max_bytes))
    # Force stub provider to avoid outbound HTTP during tests
    monkeypatch.setenv("LLM_PROVIDER", "stub")
    import app.main as main

    importlib.reload(main)
    return TestClient(main.app)


def test_rejects_large_body(monkeypatch):
    client = build_client(monkeypatch, 5)
    headers = {"authorization": "x", "content-length": "6"}
    r = client.post(
        "/proxy",
        headers=headers,
        json={"model": "m", "messages": [{"role": "user", "content": "123"}]},
    )
    assert r.status_code == 413


def test_allows_within_limit(monkeypatch):
    client = build_client(monkeypatch, 1000000)
    headers = {"authorization": "x"}
    r = client.post(
        "/proxy",
        headers=headers,
        json={"model": "m", "messages": [{"role": "user", "content": "ok"}]},
    )
    assert r.status_code == 200
