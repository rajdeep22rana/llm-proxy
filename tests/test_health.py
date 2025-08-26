from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_healthz():
    response = client.get("/healthz")
    assert response.status_code == 200
    body = response.json()
    # Minimal contract: status present and ok when healthy
    assert body["status"] in {"ok", "degraded"}
    # Uptime should be present and non-negative (can be very small)
    assert "uptime_seconds" in body
    assert body["uptime_seconds"] is None or body["uptime_seconds"] >= 0
    # Optional diagnostics present
    assert "version" in body
    assert "rate_limit" in body and isinstance(body["rate_limit"], dict)
    assert "logging" in body and isinstance(body["logging"], dict)
    assert "cors" in body and isinstance(body["cors"], dict)
