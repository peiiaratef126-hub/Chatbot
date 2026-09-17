import pytest
import asyncio
import json
from fastapi.testclient import TestClient

from app.main import app
from app.config import get_settings
from app.schemas.chat import ChatRequest, ChatMessage
from app.services.vector_service import VectorService
from app.services.llm_service import LLMService
from app.services.rag_pipeline import RAGPipeline

client = TestClient(app)

def test_health_endpoint():
    """Verify GET /api/health returns 200 with complete diagnostics."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "environment" in data
    assert "mock_mode" in data
    assert "vector_db_connected" in data
    assert "indexed_documents_count" in data
    assert data["indexed_documents_count"] > 0

def test_root_endpoint():
    """Verify GET / returns 200 and points to endpoints."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "operational"
    assert "/api/chat" in data["endpoints"]["chat"]

def test_sample_kb_endpoint():
    """Verify GET /api/kb/sample returns list of articles."""
    response = client.get("/api/kb/sample")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] > 0
    assert len(data["brands"]) > 0
    assert len(data["sample_articles"]) > 0

def test_vector_service_similarity():
    """Verify VectorService returns appropriate citations for test queries."""
    vs = VectorService()
    results = vs._search_in_memory(
        query="My battery drains fast on my phone",
        brand="AppleSupport",
        top_k=3,
        threshold=0.20
    )
    assert len(results) > 0
    assert results[0].brand == "AppleSupport"
    assert results[0].score > 0.0

def test_greeting_intent_detection():
    """Verify LLMService detects greetings accurately."""
    llm = LLMService()
    assert llm.is_trivial_greeting("Hello") is True
    assert llm.is_trivial_greeting("Hi there!") is True
    assert llm.is_trivial_greeting("Good morning") is True
    assert llm.is_trivial_greeting("How can I cancel my subscription and get a refund?") is False

@pytest.mark.asyncio
async def test_rag_pipeline_greeting_stream():
    """Verify greeting fast-path stream yields thought, tokens, metrics, and done."""
    pipeline = RAGPipeline()
    req = ChatRequest(message="Hello!", brand="AppleSupport")
    events = []
    async for chunk in pipeline.execute_stream(req):
        for line in chunk.strip().split("\n"):
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))

    event_types = [e["type"] for e in events]
    assert "thought" in event_types
    assert "token" in event_types
    assert "metrics" in event_types
    assert "done" in event_types

@pytest.mark.asyncio
async def test_rag_pipeline_rag_stream():
    """Verify knowledge retrieval RAG stream yields citation, tokens, and metrics."""
    pipeline = RAGPipeline()
    req = ChatRequest(message="Where is my refund for a returned item?", brand="AmazonHelp")
    events = []
    async for chunk in pipeline.execute_stream(req):
        for line in chunk.strip().split("\n"):
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))

    event_types = [e["type"] for e in events]
    assert "thought" in event_types
    assert "tool_call" in event_types
    assert "tool_result" in event_types
    assert "token" in event_types
    assert "metrics" in event_types
    assert "done" in event_types

def test_chat_endpoint_sse():
    """Verify POST /api/chat returns 200 with text/event-stream content type."""
    payload = {
        "message": "Hi, how are you?",
        "history": [],
        "brand": "AppleSupport"
    }
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    assert "X-Accel-Buffering" in response.headers
    assert response.headers["X-Accel-Buffering"] == "no"
