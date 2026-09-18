import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sentry_sdk

from app.config import get_settings
from app.routers.chat import router as chat_router
from app.routers.health import router as health_router
from app.services.llm_service import get_llm_service
from app.services.vector_service import get_vector_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("chatbot.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for startup diagnostics and graceful resource termination."""
    settings = get_settings()
    logger.info("=" * 60)
    logger.info("🚀 Starting Customer Support RAG Chatbot Backend")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Port: {settings.PORT} (Hosting target ready)")
    logger.info(f"Groq Model: {settings.GROQ_MODEL}")
    logger.info(f"Mock Mode Active: {settings.is_mock_mode}")
    
    # Pre-initialize services
    v_service = get_vector_service()
    v_status = v_service.get_status()
    logger.info(f"Vector DB Backend: {v_status['backend']} (Indexed Docs: {v_status['indexed_count']})")
    logger.info("=" * 60)

    yield

    # Clean shutdown
    logger.info("Shutting down backend services...")
    llm = get_llm_service()
    await llm.close()
    logger.info("Shutdown complete.")

settings = get_settings()

# Initialize Sentry SDK before FastAPI app instantiation
if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.SENTRY_ENVIRONMENT or settings.ENVIRONMENT,
        send_default_pii=True,
        enable_logs=True,
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        profile_session_sample_rate=settings.SENTRY_PROFILES_SAMPLE_RATE,
        profile_lifecycle="trace",
    )
    logger.info("🛡️ Sentry SDK initialized successfully")

app = FastAPI(
    title="Customer Support RAG Chatbot API",
    description=(
        "Production-grade, zero-cost Customer Support Agentic RAG Chatbot backend. "
        "Powered by Groq Cloud (Llama 3.1 300 tok/sec), Qdrant Cloud semantic indexing, "
        "and Server-Sent Events (SSE) streaming."
    ),
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS for Vercel, localhost, and custom domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Sentry Verification Endpoint
@app.get("/sentry-debug")
async def trigger_sentry_error():
    """Trigger an intentional ZeroDivisionError to verify Sentry event ingestion."""
    logger.info("Triggering intentional test exception for Sentry verification...")
    division_by_zero = 1 / 0
    return {"status": "unreachable", "result": division_by_zero}

# Register routers
app.include_router(health_router)
app.include_router(chat_router)
