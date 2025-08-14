from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_metrics_endpoint_available():
    r = client.get("/metrics")
    assert r.status_code == 200
    # content type of the exposition format
    assert r.headers.get("content-type", "").startswith("text/plain")
    # Ensure at least one of our metric names exists
    assert b"http_requests_total" in r.content
