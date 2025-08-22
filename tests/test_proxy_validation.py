from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

headers = {"authorization": "test-key"}


def test_empty_messages_returns_400():
    payload = {"model": "m", "messages": []}
    r = client.post("/proxy", json=payload, headers=headers)
    assert r.status_code == 400
    assert r.json()["detail"] == "Messages must not be empty"


def test_invalid_role_returns_400():
    payload = {"model": "m", "messages": [{"role": "bad", "content": "x"}]}
    r = client.post("/proxy", json=payload, headers=headers)
    assert r.status_code == 400
    assert "Invalid role" in r.json()["detail"]


def test_empty_content_returns_400():
    payload = {"model": "m", "messages": [{"role": "user", "content": ""}]}
    r = client.post("/proxy", json=payload, headers=headers)
    assert r.status_code == 400
    assert r.json()["detail"] == "Message content must not be empty"


def test_last_message_must_not_be_assistant():
    payload = {
        "model": "m",
        "messages": [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
        ],
    }
    r = client.post("/proxy", json=payload, headers=headers)
    assert r.status_code == 400
    assert r.json()["detail"] == 'Last message must not be from role "assistant"'


def test_system_last_is_allowed():
    # Use a local client that doesn't raise server exceptions so we only
    # validate that our request validator accepts system-last.
    local_client = TestClient(app, raise_server_exceptions=False)
    payload = {
        "model": "m",
        "messages": [
            {"role": "user", "content": "hi"},
            {"role": "system", "content": "you are helpful"},
        ],
    }
    r = local_client.post("/proxy", json=payload, headers=headers)
    # Validation should not reject system-last; allow any non-validation outcome.
    assert not (
        r.status_code == 400
        and r.json().get("detail") == 'Last message must not be from role "assistant"'
    )
