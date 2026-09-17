import time
from fastapi import APIRouter, Depends
from app.config import Settings, get_settings
from app.schemas.chat import HealthResponse, SampleDocResponse, KnowledgeCitation
from app.services.vector_service import VectorService, get_vector_service

router = APIRouter(tags=["Health & System"])
_START_TIME = time.time()

@router.get("/api/health", response_model=HealthResponse)
async def health_check(
    settings: Settings = Depends(get_settings),
    vector_service: VectorService = Depends(get_vector_service)
):
    """
    Returns real-time operational metrics, vector database state,
    and configured model identifiers.
    """
    v_status = vector_service.get_status()
    uptime = time.time() - _START_TIME
    
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        environment=settings.ENVIRONMENT,
        mock_mode=settings.is_mock_mode,
        groq_model=settings.GROQ_MODEL,
        vector_db_connected=v_status["connected"],
        vector_db_backend=v_status["backend"],
        indexed_documents_count=v_status["indexed_count"],
        uptime_seconds=round(uptime, 2)
    )

@router.get("/api/kb/sample", response_model=SampleDocResponse)
async def get_sample_kb_articles(
    vector_service: VectorService = Depends(get_vector_service)
):
    """
    Returns representative sample articles currently loaded into
    the vector retrieval service.
    """
    docs = vector_service.local_docs
    brands = sorted(list(set(d.get("brand", "Unknown") for d in docs)))
    
    sample_citations = [
        KnowledgeCitation(
            doc_id=d.get("doc_id", 0),
            brand=d.get("brand", ""),
            category=d.get("category", "General"),
            query=d.get("query", ""),
            resolution=d.get("resolution", ""),
            score=1.0
        )
        for d in docs[:12]
    ]
    
    return SampleDocResponse(
        total=len(docs),
        brands=brands,
        sample_articles=sample_citations
    )

@router.get("/")
async def root():
    """Root landing endpoint with system status overview."""
    settings = get_settings()
    return {
        "service": "Customer Support RAG Chatbot API",
        "status": "operational",
        "mode": "Zero-Cost Mock Mode" if settings.is_mock_mode else "Groq Cloud Live Mode",
        "docs_url": "/docs",
        "endpoints": {
            "chat": "POST /api/chat",
            "health": "GET /api/health",
            "kb_sample": "GET /api/kb/sample"
        }
    }
