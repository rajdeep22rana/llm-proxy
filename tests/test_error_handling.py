from fastapi.testclient import TestClient
from app.main import app
from app.providers.llm import LLMProvider
from app.schemas.chat import ChatRequest, ChatResponse


class RaisingProvider(LLMProvider):
    async def chat(self, request: ChatRequest, authorization: str) -> ChatResponse:
        raise RuntimeError("boom")


def test_unhandled_exception_returns_500_with_request_id(monkeypatch):
    # override the provider dependency to use the raising provider
    from app.routers import proxy as proxy_router

    app.dependency_overrides[proxy_router.get_llm_provider] = lambda: RaisingProvider()

    client = TestClient(app, raise_server_exceptions=False)
    payload = {"model": "m", "messages": [{"role": "user", "content": "hi"}]}
    try:
        r = client.post("/proxy", json=payload, headers={"authorization": "x"})
        assert r.status_code == 500
        # request id present in headers
        assert "x-request-id" in r.headers
        rid = r.headers["x-request-id"]
        assert rid
        # and in JSON body
        body = r.json()
        assert body.get("error") == "Internal Server Error"
        assert body.get("request_id") == rid
    finally:
        # cleanup override
        app.dependency_overrides.pop(proxy_router.get_llm_provider, None)
