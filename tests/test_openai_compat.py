import asyncio
import types
import pytest

from app.providers.openai_compat import OpenAICompatibleProvider


class _FakeResponse:
    def __init__(
        self, data=None, raise_error: Exception | None = None, status_code: int = 200
    ):
        self._data = data or {}
        self._raise_error = raise_error
        self.status_code = status_code

    def raise_for_status(self):
        if self._raise_error:
            raise self._raise_error

    def json(self):
        return self._data


class _FakeAsyncStreamContext:
    def __init__(
        self, lines, raise_error: Exception | None = None, status_code: int = 200
    ):
        self._lines = lines
        self._raise_error = raise_error
        self.status_code = status_code

    async def __aenter__(self):
        if self._raise_error:
            raise self._raise_error
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def raise_for_status(self):
        if self._raise_error:
            raise self._raise_error

    async def aiter_lines(self):
        for line in self._lines:
            # Simulate async streaming
            await asyncio.sleep(0)
            yield line


class _FakeAsyncClient:
    def __init__(self, base_url=None, timeout=None, **kwargs):
        # record for assertions
        self.base_url = base_url
        self.timeout = timeout
        self.kwargs = kwargs
        # injectable behavior
        self._next_response: _FakeResponse | None = None
        self._stream_lines: list[str] | None = None
        self._stream_error: Exception | None = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, path, headers=None, json=None):
        # capture last headers for assertions
        self.last_headers = headers or {}
        return self._next_response or _FakeResponse({})

    def stream(self, method, path, headers=None, json=None):
        self.last_headers = headers or {}
        return _FakeAsyncStreamContext(self._stream_lines or [], self._stream_error)


@pytest.mark.asyncio
async def test_chat_maps_response_and_defaults(monkeypatch):
    fake_client = _FakeAsyncClient()
    fake_client._next_response = _FakeResponse(
        {
            "id": "abc123",
            "object": "chat.completion",
            "created": 123,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "hi"},
                    "finish_reason": "stop",
                }
            ],
            # omit usage to hit defaults
        }
    )

    def _client_factory(*args, **kwargs):
        # ignore args, return our instance
        return fake_client

    monkeypatch.setenv("OPENAI_COMPAT_BASE_URL", "http://unit-test.local/v1")
    monkeypatch.setenv("OPENAI_COMPAT_API_KEY", "env-key")
    monkeypatch.setenv("LLM_PROVIDER", "stub")
    monkeypatch.setattr(
        "app.providers.openai_compat.httpx.AsyncClient", _client_factory
    )

    provider = OpenAICompatibleProvider()
    req = types.SimpleNamespace(
        model="m", messages=[types.SimpleNamespace(role="user", content="hello")]
    )
    resp = await provider.chat(req, authorization="Bearer inbound")

    assert resp.id == "abc123"
    assert resp.object == "chat.completion"
    assert resp.created == 123
    assert len(resp.choices) == 1
    assert resp.choices[0].message.content == "hi"
    # defaults used when usage omitted
    assert resp.usage.total_tokens == 0
    # header precedence: inbound auth forwarded
    assert fake_client.last_headers.get("Authorization") == "Bearer inbound"


@pytest.mark.asyncio
async def test_chat_empty_choices_gets_default(monkeypatch):
    fake_client = _FakeAsyncClient()
    fake_client._next_response = _FakeResponse({"choices": []})

    monkeypatch.setattr(
        "app.providers.openai_compat.httpx.AsyncClient", lambda *a, **k: fake_client
    )

    provider = OpenAICompatibleProvider()
    req = types.SimpleNamespace(
        model="m", messages=[types.SimpleNamespace(role="user", content="hello")]
    )
    result = await provider.chat(req, authorization="x")
    assert len(result.choices) == 1
    assert result.choices[0].message.role == "assistant"


@pytest.mark.asyncio
async def test_headers_use_env_key_when_no_inbound(monkeypatch):
    fake_client = _FakeAsyncClient()
    fake_client._next_response = _FakeResponse(
        {"choices": [{"index": 0, "message": {"role": "assistant", "content": ""}}]}
    )

    monkeypatch.setenv("OPENAI_COMPAT_API_KEY", "sekret")
    monkeypatch.setattr(
        "app.providers.openai_compat.httpx.AsyncClient", lambda *a, **k: fake_client
    )

    provider = OpenAICompatibleProvider()
    req = types.SimpleNamespace(
        model="m", messages=[types.SimpleNamespace(role="user", content="hi")]
    )
    await provider.chat(req, authorization="")
    assert fake_client.last_headers.get("Authorization") == "Bearer sekret"


@pytest.mark.asyncio
async def test_chat_stream_yields_text_chunks(monkeypatch):
    lines = [
        "",  # heartbeat
        'data: {"choices":[{"delta":{"content":"hel"}}]}',
        "data: not-json",
        '{"choices":[{"delta":{"content":"lo"}}]}',
        "data: [DONE]",
    ]
    fake_client = _FakeAsyncClient()
    fake_client._stream_lines = lines

    monkeypatch.setattr(
        "app.providers.openai_compat.httpx.AsyncClient", lambda *a, **k: fake_client
    )

    provider = OpenAICompatibleProvider()
    req = types.SimpleNamespace(
        model="m", messages=[types.SimpleNamespace(role="user", content="hi")]
    )
    chunks = []
    async for part in provider.chat_stream(req, authorization="x"):
        chunks.append(part)
    assert "".join(chunks) == "hello"


@pytest.mark.asyncio
async def test_chat_raises_http_error(monkeypatch):
    class _HTTPError(Exception):
        pass

    fake_client = _FakeAsyncClient()
    fake_client._next_response = _FakeResponse({}, raise_error=_HTTPError("boom"))

    monkeypatch.setattr(
        "app.providers.openai_compat.httpx.AsyncClient", lambda *a, **k: fake_client
    )

    provider = OpenAICompatibleProvider()
    req = types.SimpleNamespace(
        model="m", messages=[types.SimpleNamespace(role="user", content="hi")]
    )
    with pytest.raises(_HTTPError):
        await provider.chat(req, authorization="x")


def test_base_url_from_env(monkeypatch):
    fake_client = _FakeAsyncClient()

    def _client_factory(base_url=None, timeout=None, **kwargs):
        # record base_url given by provider
        fake_client.base_url = base_url
        return fake_client

    monkeypatch.setenv("OPENAI_COMPAT_BASE_URL", "http://example.local/api/v1/")
    monkeypatch.setattr(
        "app.providers.openai_compat.httpx.AsyncClient", _client_factory
    )
    provider = OpenAICompatibleProvider()

    # call a sync part to trigger __init__ but not network
    assert provider.base_url == "http://example.local/api/v1"


def test_non_stream_timeout_from_env(monkeypatch):
    fake_client = _FakeAsyncClient()

    def _client_factory(base_url=None, timeout=None, **kwargs):
        fake_client.base_url = base_url
        fake_client.timeout = timeout
        return fake_client

    monkeypatch.setenv("OPENAI_COMPAT_TIMEOUT_SECONDS", "123.5")
    monkeypatch.setattr(
        "app.providers.openai_compat.httpx.AsyncClient", _client_factory
    )
    provider = OpenAICompatibleProvider()

    # Exercise chat() enough to instantiate client and pass through timeout
    import types

    fake_client._next_response = _FakeResponse({"choices": [{}]})
    req = types.SimpleNamespace(
        model="m", messages=[types.SimpleNamespace(role="user", content="hi")]
    )
    # We don't assert the return; focus on timeout propagation
    import asyncio
    asyncio.run(provider.chat(req, authorization="x"))
    assert fake_client.timeout == 123.5
