import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)

def test_root_endpoint_metadata(client):
    """Verify landing endpoint contains system documentation and status."""
    res = client.get("/")
    assert res.status_code == 200
    data = res.json()
    assert data["service"] == "Customer Support RAG Chatbot API"
    assert "endpoints" in data
    assert "chat" in data["endpoints"]
    assert "health" in data["endpoints"]

def test_sentry_debug_triggers_exception(client):
    """Verify /sentry-debug intentionally triggers ZeroDivisionError for telemetry."""
    res = client.get("/sentry-debug")
    assert res.status_code == 500

def test_chat_endpoint_empty_message_validation(client):
    """Verify empty message payload returns 400 error."""
    res = client.post("/api/chat", json={"message": "   ", "history": [], "brand": None})
    assert res.status_code == 400
    assert "empty" in res.json()["detail"].lower()

def test_chat_endpoint_invalid_json_validation(client):
    """Verify malformed payload returns 422 Unprocessable Entity."""
    res = client.post("/api/chat", json={"invalid_field": 123})
    assert res.status_code == 422

def test_chat_endpoint_cors_headers(client):
    """Verify CORS preflight request returns allowed origins and methods."""
    headers = {
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Content-Type"
    }
    res = client.options("/api/chat", headers=headers)
    assert res.status_code == 200
    assert "access-control-allow-origin" in res.headers
