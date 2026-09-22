from typing import List, Optional, Literal, Dict, Any, Union
from pydantic import BaseModel, Field

class ChatMessage(BaseModel):
    """Represents an individual message within the conversational thread."""
    role: Literal["user", "assistant", "system"] = Field(..., description="Message role")
    content: str = Field(..., description="Message body text")

class ChatRequest(BaseModel):
    """Payload sent by frontend to initiate chat completion."""
    message: str = Field(..., min_length=1, description="Latest user question or support inquiry")
    history: List[ChatMessage] = Field(default_factory=list, description="Prior conversation context")
    brand: Optional[str] = Field(default=None, description="Optional target brand filter (e.g. AppleSupport, AmazonHelp)")
    session_id: Optional[str] = Field(default=None, description="Optional conversational session ID")
    message_id: Optional[str] = Field(default=None, description="Optional client-generated message ID")
    stream: bool = Field(default=True, description="Whether to stream response via SSE")

class KnowledgeCitation(BaseModel):
    """Grounded knowledge chunk retrieved from vector database."""
    doc_id: Union[int, str] = Field(..., description="Unique document ID in vector index")
    brand: str = Field(..., description="Associated enterprise brand")
    category: str = Field(..., description="Support issue category")
    query: str = Field(..., description="Canonical inquiry or problem statement")
    resolution: str = Field(..., description="Official verified resolution advice")
    score: float = Field(..., description="Relevance / similarity score (0.0 to 1.0)")
    reranked: bool = Field(default=False, description="Whether score was calculated by cross-encoder reranker")

class StreamEvent(BaseModel):
    """Structured SSE event streamed back to client."""
    type: Literal[
        "thought", "tool_call", "tool_result", "citation",
        "token", "metrics", "error", "done", "session", "guardrail"
    ] = Field(..., description="Type of event in the RAG generation lifecycle")
    content: Optional[str] = Field(default=None, description="Thought, guardrail or error content")
    tool: Optional[str] = Field(default=None, description="Name of the invoked tool")
    input: Optional[Dict[str, Any]] = Field(default=None, description="Tool input arguments")
    output: Optional[Dict[str, Any]] = Field(default=None, description="Tool execution outcome")
    citation: Optional[KnowledgeCitation] = Field(default=None, description="Knowledge citation object")
    token: Optional[str] = Field(default=None, description="Text token chunk")
    metrics: Optional[Dict[str, Any]] = Field(default=None, description="Latency, token speed, and source metrics")
    session_id: Optional[str] = Field(default=None, description="Session ID event payload")
    done: bool = Field(default=False, description="Whether this marks stream completion")

class FeedbackRequest(BaseModel):
    """Payload for submitting user thumbs-up/down feedback."""
    session_id: str = Field(..., description="Active session UUID")
    message_id: str = Field(..., description="Target assistant message ID")
    rating: Literal["up", "down"] = Field(..., description="Feedback rating")
    comment: Optional[str] = Field(default=None, description="Optional feedback explanation or tag")

class FeedbackResponse(BaseModel):
    """Acknowledgment response for recorded feedback."""
    status: str = Field(default="success")
    message: str = Field(default="Feedback recorded")

class SessionHistoryResponse(BaseModel):
    """Multi-turn session history payload."""
    session_id: str
    brand: Optional[str] = None
    created_at: str
    messages: List[Dict[str, Any]]

class AdminEscalationItem(BaseModel):
    """Item structure for human escalation audit log."""
    ticket_id: str
    session_id: Optional[str] = None
    brand: str
    query: str
    reason: str
    urgency: str
    created_at: str

class AdminEscalationsResponse(BaseModel):
    """List of all customer support escalations."""
    total: int
    escalations: List[AdminEscalationItem]

class AdminFeedbackResponse(BaseModel):
    """List of user feedback records."""
    total: int
    feedback: List[Dict[str, Any]]

class HealthResponse(BaseModel):
    """Detailed service health and runtime diagnostic information."""
    status: str = Field(default="healthy", description="Overall service status")
    version: str = Field(default="1.0.0", description="Backend application version")
    environment: str = Field(..., description="Active environment")
    mock_mode: bool = Field(..., description="Whether running in offline/mock mode")
    groq_model: str = Field(..., description="Configured Groq model identifier")
    vector_db_connected: bool = Field(..., description="Vector database connectivity state")
    vector_db_backend: str = Field(..., description="Vector backend type: qdrant_cloud or in_memory_sample_kb")
    indexed_documents_count: int = Field(..., description="Count of active documents in knowledge base")
    uptime_seconds: float = Field(default=0.0, description="Process uptime in seconds")

class SampleDocResponse(BaseModel):
    """Response containing sample support articles."""
    total: int
    brands: List[str]
    sample_articles: List[KnowledgeCitation]
