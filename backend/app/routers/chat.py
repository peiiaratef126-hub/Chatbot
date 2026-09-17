import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.schemas.chat import ChatRequest, StreamEvent
from app.services.rag_pipeline import RAGPipeline, get_rag_pipeline

logger = logging.getLogger("chatbot.routers.chat")
router = APIRouter(prefix="/api", tags=["Chat & Retrieval"])

@router.post("/chat")
async def chat_endpoint(
    request: ChatRequest,
    rag_pipeline: RAGPipeline = Depends(get_rag_pipeline)
):
    """
    Main conversational endpoint streaming Server-Sent Events (SSE).
    Orchestrates RAG retrieval, tool execution, and LLM token generation.
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
