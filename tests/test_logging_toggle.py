import importlib
from fastapi.testclient import TestClient


def test_logging_disabled_by_default(monkeypatch):
    # Ensure env is unset -> logging disabled path exercised
    monkeypatch.delenv("LOG_REQUESTS", raising=False)
    import app.main as main

    importlib.reload(main)
    client = TestClient(main.app)
    r = client.get("/healthz")
    assert r.status_code == 200


def test_logging_enabled_path(monkeypatch):
    # Enable logging via env -> initialize logger path
    monkeypatch.setenv("LOG_REQUESTS", "true")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    import app.main as main

    importlib.reload(main)
    client = TestClient(main.app)
    r = client.get("/healthz")
    assert r.status_code == 200
