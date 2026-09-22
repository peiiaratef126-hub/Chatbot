import os
from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

SUPPORTED_BRANDS: List[str] = [
    "AppleSupport",
    "AmazonHelp",
    "Uber_Support",
    "SpotifyCares",
    "Delta",
    "NikeSupport",
]

class Settings(BaseSettings):
    """Global configuration settings loaded from environment variables or .env file."""
    
    ENVIRONMENT: str = Field(default="development", description="Runtime environment: development, staging, production")
    HOST: str = Field(default="0.0.0.0", description="FastAPI host binding")
    PORT: int = Field(default=7860, description="Server port (7860 for HF Spaces, 8000 for Render/local)")
    
    # CORS Configuration
    CORS_ORIGINS: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000,http://localhost:7860,https://*.vercel.app",
        description="Comma-separated list of allowed CORS origins"
    )
    
    # Groq Cloud API
    GROQ_API_KEY: str = Field(default="", description="Groq API key for llama-3.1-8b-instant inference")
    GROQ_MODEL: str = Field(default="llama-3.1-8b-instant", description="Target Groq model identifier")
    GROQ_BASE_URL: str = Field(default="https://api.groq.com/openai/v1", description="Groq OpenAI-compatible base URL")
    
    # Qdrant Cloud Vector DB
    QDRANT_URL: str = Field(default="", description="Qdrant Cloud cluster endpoint")
    QDRANT_API_KEY: str = Field(default="", description="Qdrant Cloud API authorization key")
    QDRANT_COLLECTION: str = Field(default="customer_support_kb", description="Vector collection name")
    
    # Embedding and Retrieval
    EMBEDDING_MODEL_NAME: str = Field(default="BAAI/bge-small-en-v1.5", description="Local or cloud embedding model name")
    SCORE_THRESHOLD: float = Field(default=0.60, description="Minimum cosine similarity score to qualify as citation")
    TOP_K: int = Field(default=4, description="Maximum number of context chunks to retrieve")

    # Hybrid Search & FlashRank Reranker (Milestone 1)
    ENABLE_RERANKER: bool = Field(default=True, description="Enable FlashRank cross-encoder reranker")
    RERANKER_MODEL_NAME: str = Field(default="ms-marco-TinyBERT-L-2-v2", description="FlashRank model identifier")
    CANDIDATE_TOP_K: int = Field(default=10, description="Number of candidate chunks retrieved before reranking")
    RERANK_TOP_N: int = Field(default=3, description="Number of top reranked chunks to retain")

    # Safety Guardrails & PII Sanitizer (Milestone 2 & Milestone 3)
    ENABLE_GUARDRAILS: bool = Field(default=True, description="Enable PII masking and prompt injection detection")

    # Strict Bilingual Support (Arabic & English Only - Milestone 1)
    ENABLE_LANGUAGE_FILTER: bool = Field(default=True, description="Strict bilingual AR/EN enforcement")
    SUPPORTED_LANGUAGES: List[str] = Field(default=["ar", "en"], description="List of officially supported language codes")

    # Corrective RAG (CRAG) & Query Rewriting (Milestone 6)
    ENABLE_CRAG: bool = Field(default=True, description="Enable Corrective RAG query rewriting fallback")
    CRAG_CONFIDENCE_THRESHOLD: float = Field(default=0.65, description="Confidence threshold triggering query reformulation")

    # Persistence & Session Storage (Milestone 3 & 8)
    DATABASE_PATH: str = Field(default="chatbot.db", description="Local SQLite database file path")
    
    # ReAct & Fallback Behavior
    MOCK_MODE: bool = Field(default=False, description="Force mock responses when external APIs are unavailable")
    MAX_REACT_ITERATIONS: int = Field(default=2, description="Mandatory upper bound on ReAct agent loop iterations")

    # Sentry Observability
    SENTRY_DSN: str = Field(default="", description="Sentry DSN endpoint for error and performance monitoring")
    SENTRY_ENVIRONMENT: str = Field(default="development", description="Sentry environment tag (development, production)")
    SENTRY_TRACES_SAMPLE_RATE: float = Field(default=1.0, description="Sentry transaction trace sample rate")
    SENTRY_PROFILES_SAMPLE_RATE: float = Field(default=1.0, description="Sentry profile sample rate")

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def cors_origin_list(self) -> List[str]:
        """Parse comma-separated CORS origins into a sanitized list without wildcard fallback."""
        if not self.CORS_ORIGINS:
            return ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:7860"]
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def is_mock_mode(self) -> bool:
        """Determines if the backend should run in mock mode."""
        if self.MOCK_MODE:
            return True
        return not bool(self.GROQ_API_KEY and self.GROQ_API_KEY.strip())

@lru_cache
def get_settings() -> Settings:
    """Return cached singleton instance of Settings."""
    return Settings()
