import importlib
from fastapi.testclient import TestClient


def build_client(monkeypatch, origins: str) -> TestClient:
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", origins)
    # Reload app to apply new env config
    import app.main as main

    importlib.reload(main)
    return TestClient(main.app)


def test_preflight_allows_configured_origin(monkeypatch):
    origin = "http://example.com"
    client = build_client(monkeypatch, origin)
    r = client.options(
        "/proxy",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
        },
    )
    assert r.status_code in (200, 204)
    assert r.headers.get("access-control-allow-origin") == origin


def test_simple_get_includes_cors_headers(monkeypatch):
    origin = "http://frontend.local"
    client = build_client(monkeypatch, origin)
    r = client.get("/healthz", headers={"Origin": origin})
    assert r.status_code == 200
    assert r.headers.get("access-control-allow-origin") == origin
