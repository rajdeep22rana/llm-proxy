from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_proxy_stub():
    request_payload = {
        "model": "test-model",
        "messages": [{"role": "user", "content": "hello"}],
    }
    headers = {"authorization": "test-key"}
    response = client.post("/proxy", json=request_payload, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "stub"
    assert body["object"] == "chat.completion"
    assert isinstance(body["created"], int)
    assert isinstance(body["choices"], list) and len(body["choices"]) == 1
    choice = body["choices"][0]
    assert choice["index"] == 0
    assert choice["message"] == {"role": "assistant", "content": "stub response"}
    assert choice["finish_reason"] == "stop"
    assert body["usage"] == {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
    }
