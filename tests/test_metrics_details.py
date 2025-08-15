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


def test_metrics_records_500_for_errors():
    # override provider to raise so we produce a 500
    from app.providers.llm import LLMProvider
    from app.schemas.chat import ChatRequest, ChatResponse
    from app.routers import proxy as proxy_router

    class RaisingProvider(LLMProvider):
        async def chat(self, request: ChatRequest, authorization: str) -> ChatResponse:
            raise RuntimeError("boom")

    app.dependency_overrides[proxy_router.get_llm_provider] = lambda: RaisingProvider()
    try:
        error_client = TestClient(app, raise_server_exceptions=False)
        r = error_client.post(
            "/proxy",
            json={"model": "m", "messages": [{"role": "user", "content": "hi"}]},
            headers={"authorization": "x"},
        )
        assert r.status_code == 500
        # now fetch metrics and ensure a 500 counter exists for POST /proxy or /proxy/
        m = error_client.get("/metrics")
        assert m.status_code == 200
        lines = m.text.splitlines()

        def has_500_for(path_label: str) -> bool:
            return any(
                line.startswith("http_requests_total{")
                and 'method="POST"' in line
                and f'path="{path_label}"' in line
                and 'status="500"' in line
                for line in lines
            )

        assert has_500_for("/proxy/") or has_500_for("/proxy"), m.text
    finally:
        app.dependency_overrides.pop(proxy_router.get_llm_provider, None)
