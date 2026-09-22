import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.schemas.chat import (
    ChatRequest,
    StreamEvent,
    FeedbackRequest,
    FeedbackResponse,
    SessionHistoryResponse
)
from app.services.rag_pipeline import RAGPipeline, get_rag_pipeline
from app.services.session_service import SessionService, get_session_service

logger = logging.getLogger("chatbot.routers.chat")
router = APIRouter(prefix="/api", tags=["Chat & Retrieval"])

@router.post("/chat")
async def chat_endpoint(
    request: ChatRequest,
    rag_pipeline: RAGPipeline = Depends(get_rag_pipeline)
):
    """
    Main conversational endpoint streaming Server-Sent Events (SSE).
    Orchestrates RAG retrieval, tool execution, guardrails, and LLM token generation.
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="User message cannot be empty.")

    async def event_generator():
        try:
            async for sse_chunk in rag_pipeline.execute_stream(request):
                yield sse_chunk
        except Exception as e:
            logger.error(f"Unhandled exception in chat stream: {e}", exc_info=True)
            err_event = StreamEvent(
                type="error",
                content=f"Stream encountered an unexpected error: {str(e)}"
            )
            yield f"data: {err_event.model_dump_json()}\n\n"
            yield f"data: {StreamEvent(type='done', done=True).model_dump_json()}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream; charset=utf-8",
            "X-Accel-Buffering": "no"  # Prevents Nginx/proxy buffer stalling
        }
    )

@router.get("/chat/history/{session_id}", response_model=SessionHistoryResponse)
async def get_chat_history(
    session_id: str,
    session_service: SessionService = Depends(get_session_service)
):
    """
    Retrieves full multi-turn conversational history and grounded citations for a given session.
    """
    history = await session_service.get_session_history(session_id)
    return SessionHistoryResponse(**history)

@router.post("/chat/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    payload: FeedbackRequest,
    session_service: SessionService = Depends(get_session_service)
):
    """
    Records customer thumbs-up / thumbs-down ratings with optional commentary
    for quality monitoring and future offline DPO dataset extraction.
    """
    success = await session_service.save_feedback(
        session_id=payload.session_id,
        message_id=payload.message_id,
        rating=payload.rating,
        comment=payload.comment
    )
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save feedback.")
    return FeedbackResponse(status="success", message="Feedback recorded successfully")
