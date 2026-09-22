import logging
from typing import Optional
from fastapi import APIRouter, Depends, Query

from app.schemas.chat import (
    AdminEscalationsResponse,
    AdminEscalationItem,
    AdminFeedbackResponse
)
from app.services.session_service import SessionService, get_session_service

logger = logging.getLogger("chatbot.routers.admin")
router = APIRouter(prefix="/api/admin", tags=["Admin & Supervision"])

@router.get("/escalations", response_model=AdminEscalationsResponse)
async def list_escalations(
    limit: int = Query(default=50, ge=1, le=200),
    session_service: SessionService = Depends(get_session_service)
):
    """
    Returns audit log of customer service inquiries escalated to human supervisors.
    """
    raw_escalations = await session_service.get_escalations(limit=limit)
    items = [
        AdminEscalationItem(
            ticket_id=r["ticket_id"],
            session_id=r.get("session_id"),
            brand=r["brand"],
            query=r["query"],
            reason=r["reason"],
            urgency=r.get("urgency", "High"),
            created_at=r["created_at"]
        )
        for r in raw_escalations
    ]
    return AdminEscalationsResponse(total=len(items), escalations=items)

@router.get("/feedback", response_model=AdminFeedbackResponse)
async def list_feedback(
    negative_only: bool = Query(default=False, description="Filter for downvotes only"),
    limit: int = Query(default=50, ge=1, le=200),
    session_service: SessionService = Depends(get_session_service)
):
    """
    Returns customer ratings and qualitative comments for RAG quality evaluation.
    """
    feedback_records = await session_service.get_feedback(negative_only=negative_only, limit=limit)
    return AdminFeedbackResponse(total=len(feedback_records), feedback=feedback_records)
