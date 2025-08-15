import importlib
from fastapi.testclient import TestClient


def build_client(
    monkeypatch, enabled: bool, window: int, max_requests: int
) -> TestClient:
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true" if enabled else "false")
    monkeypatch.setenv("RATE_LIMIT_WINDOW_SECONDS", str(window))
    monkeypatch.setenv("RATE_LIMIT_MAX_REQUESTS", str(max_requests))
    import app.main as main

    importlib.reload(main)
    return TestClient(main.app)


def reset_app(monkeypatch):
    # Clear env and reload so rate limiting returns to defaults (disabled)
    monkeypatch.delenv("RATE_LIMIT_ENABLED", raising=False)
    monkeypatch.delenv("RATE_LIMIT_WINDOW_SECONDS", raising=False)
    monkeypatch.delenv("RATE_LIMIT_MAX_REQUESTS", raising=False)
    import app.main as main

    importlib.reload(main)


def test_rate_limit_disabled_allows_requests(monkeypatch):
    try:
        client = build_client(monkeypatch, enabled=False, window=60, max_requests=1)
        headers = {"authorization": "k"}
        for _ in range(5):
            r = client.get("/healthz", headers=headers)
            assert r.status_code == 200
    finally:
        reset_app(monkeypatch)


def test_rate_limit_enforced(monkeypatch):
    try:
        client = build_client(monkeypatch, enabled=True, window=60, max_requests=2)
        headers = {"authorization": "key-1"}
        # first two succeed
        assert client.get("/healthz", headers=headers).status_code == 200
        assert client.get("/healthz", headers=headers).status_code == 200
        # third within window should be 429
        r3 = client.get("/healthz", headers=headers)
        assert r3.status_code == 429
        assert r3.headers.get("Retry-After") == "60"
    finally:
        reset_app(monkeypatch)


def test_rate_limit_separate_keys(monkeypatch):
    try:
        client = build_client(monkeypatch, enabled=True, window=60, max_requests=1)
        # two different auth headers get separate buckets
        assert client.get("/healthz", headers={"authorization": "a"}).status_code == 200
        assert client.get("/healthz", headers={"authorization": "b"}).status_code == 200
    finally:
        reset_app(monkeypatch)
