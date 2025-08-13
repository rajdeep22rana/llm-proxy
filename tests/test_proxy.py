from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_proxy_stub():
    response = client.post("/proxy", json={})
    assert response.status_code == 200
    assert response.json() == {"message": "stub"}
