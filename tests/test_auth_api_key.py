import importlib
from fastapi.testclient import TestClient


def build_client(monkeypatch, enabled: bool, keys: str | None):
    monkeypatch.setenv("API_KEY_AUTH_ENABLED", "true" if enabled else "false")
    if keys is not None:
        monkeypatch.setenv("API_KEYS", keys)
    else:
        monkeypatch.delenv("API_KEYS", raising=False)
    import app.main as main

    importlib.reload(main)
    return TestClient(main.app)


def reset_env(monkeypatch):
    monkeypatch.delenv("API_KEY_AUTH_ENABLED", raising=False)
    monkeypatch.delenv("API_KEYS", raising=False)


def test_auth_disabled_allows_requests(monkeypatch):
    try:
        client = build_client(monkeypatch, enabled=False, keys=None)
        r = client.get("/healthz")
        assert r.status_code == 200
    finally:
        reset_env(monkeypatch)


def test_auth_enabled_rejects_without_key(monkeypatch):
    try:
        client = build_client(monkeypatch, enabled=True, keys="k1,k2")
        r = client.get("/healthz")
        assert r.status_code == 401
        # request id should be present
        assert "x-request-id" in r.headers
        assert r.headers.get("www-authenticate") == "X-API-Key"
    finally:
        reset_env(monkeypatch)


def test_auth_enabled_accepts_with_valid_key(monkeypatch):
    try:
        client = build_client(monkeypatch, enabled=True, keys="k1,k2")
        r = client.get("/healthz", headers={"x-api-key": "k2"})
        assert r.status_code == 200
    finally:
        reset_env(monkeypatch)
