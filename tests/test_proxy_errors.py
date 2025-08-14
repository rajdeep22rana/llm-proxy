from fastapi.testclient import TestClient
import pytest
from app.main import app

client = TestClient(app)

valid_payload = {
    "model": "test-model",
    "messages": [{"role": "user", "content": "hello"}],
}


def test_missing_authorization_header():
    # No Authorization header should yield a 422 error
    response = client.post("/proxy", json=valid_payload)
    assert response.status_code == 422


@pytest.mark.parametrize(
    "payload",
    [{}, {"model": "test-model"}, {"messages": [{"role": "user", "content": "hello"}]}],
)
def test_invalid_request_body(payload):
    # Missing required fields should yield a 422 error
    headers = {"authorization": "test-key"}
    response = client.post("/proxy", json=payload, headers=headers)
    assert response.status_code == 422
