from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_request_id_generated_when_missing():
    r = client.get("/healthz")
    assert r.status_code == 200
    assert "x-request-id" in r.headers
    assert r.headers["x-request-id"]


def test_request_id_propagated_when_present():
    headers = {"x-request-id": "abc-123"}
    r = client.get("/healthz", headers=headers)
    assert r.status_code == 200
    assert r.headers["x-request-id"] == "abc-123"
