from fastapi.testclient import TestClient
from app.main import app

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
