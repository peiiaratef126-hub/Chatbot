import json
import pytest
from app.schemas.chat import ChatRequest, ChatMessage
from app.services.rag_pipeline import RAGPipeline

@pytest.fixture
def rag_pipeline():
    return RAGPipeline()

def test_order_status_tool_structure(rag_pipeline):
    """Verify ERP tool returns expected normalized order status dictionary."""
    res = rag_pipeline._execute_order_status_tool("  ord-99214  ")
    assert res["order_id"] == "ORD-99214"
    assert res["status"] == "In Transit - Out for Delivery"
    assert res["carrier"] == "UPS Expedited"
    assert res["signature_required"] is False

def test_escalation_tool_structure(rag_pipeline):
    """Verify CRM escalation tool creates properly formatted ticket."""
    res = rag_pipeline._execute_escalation_tool("Lawsuit threat over billing", brand="AppleSupport")
    assert res["ticket_id"].startswith("ESC-")
    assert res["brand"] == "AppleSupport"
    assert res["priority"] == "High"
    assert res["queue"] == "Tier 2 Senior Resolution Specialist"
    assert res["status"] == "Assigned to Human Agent"

@pytest.mark.asyncio
async def test_order_tracking_stream_events(rag_pipeline):
    """Verify stream triggers order_status_checker tool when order number is provided."""
    req = ChatRequest(
        message="Where is my shipment #ORDER-772184?",
        brand="AmazonHelp",
        history=[]
    )
    events = []
    async for chunk in rag_pipeline.execute_stream(req):
        if chunk.startswith("data: "):
            payload = json.loads(chunk[6:].strip())
            events.append(payload)

    # Check for tool_call and tool_result events
    tool_calls = [e for e in events if e.get("type") == "tool_call"]
    assert any(tc.get("tool") in ["check_order_status", "order_status_checker"] for tc in tool_calls)

    tool_results = [e for e in events if e.get("type") == "tool_result"]
    assert any(tr.get("tool") in ["check_order_status", "order_status_checker"] for tr in tool_results)

    # Verify metrics event
    metrics_event = next(e for e in events if e.get("type") == "metrics")
    assert "latency_ms" in metrics_event["metrics"]
    assert "tokens_per_sec" in metrics_event["metrics"]

@pytest.mark.asyncio
async def test_escalation_stream_events(rag_pipeline):
    """Verify stream triggers escalate_to_human tool when urgency keywords are detected."""
    req = ChatRequest(
        message="This is fraud and I demand a supervisor immediately!",
        brand="Uber_Support",
        history=[]
    )
    events = []
    async for chunk in rag_pipeline.execute_stream(req):
        if chunk.startswith("data: "):
            payload = json.loads(chunk[6:].strip())
            events.append(payload)

    tool_calls = [e for e in events if e.get("type") == "tool_call"]
    assert any(tc.get("tool") == "escalate_to_human" for tc in tool_calls)

    tool_results = [e for e in events if e.get("type") == "tool_result"]
    esc_result = next(tr for tr in tool_results if tr.get("tool") == "escalate_to_human")
    assert esc_result["output"]["ticket_id"].startswith("ESC-")
