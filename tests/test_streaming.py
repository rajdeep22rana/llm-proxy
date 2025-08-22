from fastapi.testclient import TestClient
from app.main import app
from app.providers.base import LLMProvider
from app.schemas.chat import ChatRequest, ChatResponse
from app.routers import proxy as proxy_router

client = TestClient(app)


def test_streaming_sends_sse_chunks():
    payload = {"model": "m", "messages": [{"role": "user", "content": "hi"}]}
    headers = {"authorization": "x"}
    with client.stream("POST", "/proxy/stream", json=payload, headers=headers) as r:
        assert r.status_code == 200
        body = b"".join(r.iter_bytes())
    text = body.decode("utf-8")
    assert "data: stub " in text
    assert "data: response" in text
    assert "data: [DONE]" in text


def test_streaming_error_emits_error_and_done():
    class RaisingStreamProvider(LLMProvider):
        async def chat(self, request: ChatRequest, authorization: str) -> ChatResponse:
            raise RuntimeError("not used")

        async def chat_stream(self, request: ChatRequest, authorization: str):
            yield "hello"
            raise RuntimeError("kaboom")

    app.dependency_overrides[proxy_router.get_provider_override] = (
        lambda: RaisingStreamProvider()
    )
    try:
        payload = {"model": "m", "messages": [{"role": "user", "content": "hi"}]}
        headers = {"authorization": "x"}
        with client.stream("POST", "/proxy/stream", json=payload, headers=headers) as r:
            assert r.status_code == 200
            body = b"".join(r.iter_bytes())
        text = body.decode("utf-8")
        assert "data: hello" in text
        assert 'data: {"error": "stream_error"' in text
        assert "data: [DONE]" in text
    finally:
        app.dependency_overrides.pop(proxy_router.get_provider_override, None)
