from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_metrics_increments_after_request():
    # hit an endpoint to generate some metrics
    r1 = client.get("/healthz")
    assert r1.status_code == 200

    metrics = client.get("/metrics")
    assert metrics.status_code == 200
    body = metrics.text
    # ensure total counter for /healthz exists
    assert 'http_requests_total{method="GET",path="/healthz",status="200"}' in body


def test_latency_histogram_buckets_present():
    metrics = client.get("/metrics")
    assert metrics.status_code == 200
    body = metrics.text
    # basic check for histogram bucket lines
    assert "http_request_duration_seconds_bucket" in body
    assert "http_request_duration_seconds_sum" in body
    assert "http_request_duration_seconds_count" in body
