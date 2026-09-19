import json
import logging
import math
import os
import re
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from app.config import get_settings
from app.schemas.chat import KnowledgeCitation

logger = logging.getLogger("chatbot.vector_service")

class VectorService:
    """
    Manages semantic vector retrieval against Qdrant Cloud with
    instant zero-dependency in-memory fallback.
    """

    def __init__(self):
        self.settings = get_settings()
        self.qdrant_client = None
        self.embedder = None
        self.is_connected_to_qdrant = False
        self.backend_type = "in_memory_sample_kb"
        self.local_docs: List[Dict[str, Any]] = []
        self._load_local_sample_docs()
        self._init_qdrant_if_configured()

    def _load_local_sample_docs(self):
        """Loads representative customer support knowledge articles."""
        candidate_paths = [
            Path(__file__).resolve().parent.parent.parent.parent / "scripts" / "data" / "sample_kb.json",
            Path(__file__).resolve().parent.parent.parent / "scripts" / "data" / "sample_kb.json",
            Path("scripts/data/sample_kb.json"),
            Path("/content/sample_kb.json")
        ]
        
        loaded = False
        for p in candidate_paths:
            if p.exists():
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        self.local_docs = json.load(f)
                    logger.info(f"Loaded {len(self.local_docs)} sample articles from {p}")
                    loaded = True
                    break
                except Exception as e:
                    logger.warning(f"Failed loading {p}: {e}")

        if not loaded or not self.local_docs:
            logger.info("Initializing embedded default knowledge base articles.")
            self.local_docs = [
                {
                    "doc_id": 1,
                    "brand": "AppleSupport",
                    "category": "Technical Support",
                    "query": "iPhone battery drains rapidly after update",
                    "resolution": "Check Settings > Battery > Battery Health. Optimize Background App Refresh and allow 48 hours for indexing.",
                    "text": "AppleSupport iPhone battery rapid drain after iOS update battery health background refresh"
                },
                {
                    "doc_id": 2,
                    "brand": "AmazonHelp",
                    "category": "Orders & Delivery",
                    "query": "Package marked as delivered but missing",
                    "resolution": "Check around delivery areas, porch, and with neighbors. Carriers can scan up to 24h early. If not found after 36h, request replacement in Your Orders.",
                    "text": "AmazonHelp package marked delivered not arrived missing porch carrier replacement"
                },
                {
                    "doc_id": 3,
                    "brand": "Uber_Support",
                    "category": "Billing & Payments",
                    "query": "Dispute cleaning fee or unexpected charge",
                    "resolution": "Go to Activity > Select Trip > Help > Review my fees and fares. Submit photos to dispute cleaning assessments.",
                    "text": "Uber_Support dispute unexpected cleaning fee receipt fare adjustment"
                },
                {
                    "doc_id": 4,
                    "brand": "SpotifyCares",
                    "category": "Technical Support",
                    "query": "Music stops playing when screen locks",
                    "resolution": "Disable battery saver for Spotify. On iOS toggle Background App Refresh; on Android exclude from aggressive battery management.",
                    "text": "SpotifyCares playback stops screen lock background audio battery optimization"
                },
                {
                    "doc_id": 5,
                    "brand": "Delta",
                    "category": "Reservations & Travel",
                    "query": "Flight delayed or baggage missing",
                    "resolution": "Report missing baggage at Baggage Service Office for a File Reference. Track status online or in Fly Delta app.",
                    "text": "Delta flight delay cancellation baggage claim baggage service office compensation"
                },
                {
                    "doc_id": 6,
                    "brand": "NikeSupport",
                    "category": "Orders & Delivery",
                    "query": "60-day return policy and shoe exchange",
                    "resolution": "Nike Members can return items within 60 days even if worn for a 100% refund or exchange using prepaid UPS label.",
                    "text": "NikeSupport 60-day return trial policy exchange prepaid return label worn shoes"
                }
            ]

    def _init_qdrant_if_configured(self):
        """Attempts to initialize remote Qdrant Cloud client."""
        if not self.settings.QDRANT_URL:
            logger.info("No QDRANT_URL configured. Running in high-speed in-memory vector mode.")
            return

        try:
            from qdrant_client import QdrantClient
            self.qdrant_client = QdrantClient(
                url=self.settings.QDRANT_URL,
                api_key=self.settings.QDRANT_API_KEY or None,
                timeout=15.0
            )
            # Verify connectivity
            collections = self.qdrant_client.get_collections()
            self.is_connected_to_qdrant = True
            self.backend_type = "qdrant_cloud"
            logger.info(f"Connected to Qdrant Cloud: {self.settings.QDRANT_URL} (Collections: {len(collections.collections)})")

            # Initialize embedder for real semantic retrieval
            try:
                from fastembed import TextEmbedding
                self.embedder = TextEmbedding(self.settings.EMBEDDING_MODEL_NAME)
                logger.info(f"FastEmbed initialized with model: {self.settings.EMBEDDING_MODEL_NAME}")
            except Exception:
                try:
                    from sentence_transformers import SentenceTransformer
                    self.embedder = SentenceTransformer(self.settings.EMBEDDING_MODEL_NAME)
                    logger.info("SentenceTransformer initialized.")
                except Exception:
                    self.embedder = None
        except Exception as e:
            logger.warning(f"Could not connect to Qdrant Cloud ({e}). Reverting to in-memory fallback.")
            self.is_connected_to_qdrant = False
            self.backend_type = "in_memory_sample_kb"

    def _tokenize(self, text: str) -> List[str]:
        """Simple, fast tokenization for in-memory cosine ranking."""
        return re.findall(r'\b[a-z0-9]{2,}\b', text.lower())

    def _compute_in_memory_similarity(self, query: str, doc_text: str) -> float:
        """Computes BM25/Cosine hybrid similarity score without external dependencies."""
        q_tokens = self._tokenize(query)
        d_tokens = self._tokenize(doc_text)
        
        if not q_tokens or not d_tokens:
            return 0.0

        q_counts: Dict[str, int] = {}
        for t in q_tokens:
            q_counts[t] = q_counts.get(t, 0) + 1

        d_counts: Dict[str, int] = {}
        for t in d_tokens:
            d_counts[t] = d_counts.get(t, 0) + 1

        # Calculate dot product
        intersection = set(q_counts.keys()) & set(d_counts.keys())
        if not intersection:
            return 0.0

        dot_product = sum(q_counts[t] * d_counts[t] for t in intersection)
        q_norm = math.sqrt(sum(c * c for c in q_counts.values()))
        d_norm = math.sqrt(sum(c * c for c in d_counts.values()))

        cosine = dot_product / (q_norm * d_norm)
        # Add coverage boost
        coverage = len(intersection) / len(q_counts)
        hybrid_score = 0.6 * cosine + 0.4 * coverage
        return min(0.99, hybrid_score)

    async def search(
        self,
        query: str,
        brand: Optional[str] = None,
        top_k: Optional[int] = None,
        score_threshold: Optional[float] = None
    ) -> List[KnowledgeCitation]:
        """
        Retrieves top relevant knowledge base articles for a query.
        Filters by brand if specified and applies score threshold.
        """
        limit = top_k or self.settings.TOP_K
        threshold = score_threshold or self.settings.SCORE_THRESHOLD

        # If connected to Qdrant Cloud, query remote collection
        if self.is_connected_to_qdrant and self.qdrant_client:
            try:
                return await self._search_qdrant(query, brand, limit, threshold)
            except Exception as e:
                logger.error(f"Qdrant query failed: {e}. Falling back to in-memory search.")

        # In-Memory Search Fallback
        return self._search_in_memory(query, brand, limit, threshold)

    def _search_in_memory(
        self,
        query: str,
        brand: Optional[str],
        top_k: int,
        threshold: float
    ) -> List[KnowledgeCitation]:
        """Executes zero-latency in-memory ranking."""
        scored_docs: List[Tuple[float, Dict[str, Any]]] = []

        for doc in self.local_docs:
            # Brand filtering
            if brand and doc.get("brand", "").lower() != brand.lower():
                continue

            doc_corpus = f"{doc.get('brand', '')} {doc.get('category', '')} {doc.get('query', '')} {doc.get('resolution', '')}"
            score = self._compute_in_memory_similarity(query, doc_corpus)

            # Extra boost if exact brand is mentioned in query
            if doc.get("brand", "").lower() in query.lower():
                score = min(0.98, score + 0.15)

            if score >= threshold:
                scored_docs.append((score, doc))

        # Sort descending by similarity score
        scored_docs.sort(key=lambda x: x[0], reverse=True)

        results: List[KnowledgeCitation] = []
        for score, doc in scored_docs[:top_k]:
            results.append(
                KnowledgeCitation(
                    doc_id=doc.get("doc_id", 0),
                    brand=doc.get("brand", "Unknown"),
                    category=doc.get("category", "General"),
                    query=doc.get("query", ""),
                    resolution=doc.get("resolution", ""),
                    score=round(score, 4)
                )
            )
        return results

    async def _search_qdrant(
        self,
        query: str,
        brand: Optional[str],
        top_k: int,
        threshold: float
    ) -> List[KnowledgeCitation]:
        """Queries remote Qdrant Cloud collection."""
        from qdrant_client.http import models

        query_filter = None
        if brand:
            query_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="brand",
                        match=models.MatchValue(value=brand)
                    )
                ]
            )

        # Generate dense query embedding vector
        query_vector = [0.0] * 384
        if self.embedder is not None:
            try:
                if hasattr(self.embedder, "embed"):
                    query_vector = list(self.embedder.embed([query]))[0].tolist()
                else:
                    query_vector = self.embedder.encode(query, normalize_embeddings=True).tolist()
            except Exception as e_emb:
                logger.warning(f"Error computing query vector: {e_emb}")

        # Cross-version compatibility for qdrant-client (query_points vs search)
        if hasattr(self.qdrant_client, "query_points"):
            res = self.qdrant_client.query_points(
                collection_name=self.settings.QDRANT_COLLECTION,
                query=query_vector,
                query_filter=query_filter,
                limit=top_k,
                score_threshold=threshold
            )
            hits = res.points
        else:
            hits = self.qdrant_client.search(
                collection_name=self.settings.QDRANT_COLLECTION,
                query_vector=query_vector,
                query_filter=query_filter,
                limit=top_k,
                score_threshold=threshold
            )

        citations: List[KnowledgeCitation] = []
        for hit in hits:
            payload = hit.payload or {}
            citations.append(
                KnowledgeCitation(
                    doc_id=hit.id,
                    brand=payload.get("brand", "Unknown"),
                    category=payload.get("category", "General"),
                    query=payload.get("query", ""),
                    resolution=payload.get("resolution", ""),
                    score=round(hit.score, 4)
                )
            )
        return citations

    def get_status(self) -> Dict[str, Any]:
        """Returns vector database status and metadata."""
        count = len(self.local_docs)
        if self.is_connected_to_qdrant and self.qdrant_client:
            try:
                col_info = self.qdrant_client.get_collection(self.settings.QDRANT_COLLECTION)
                count = col_info.points_count if col_info.points_count is not None else count
            except Exception:
                pass

        return {
            "connected": self.is_connected_to_qdrant,
            "backend": self.backend_type,
            "indexed_count": count,
            "collection_name": self.settings.QDRANT_COLLECTION
        }

_vector_service_instance: Optional[VectorService] = None

def get_vector_service() -> VectorService:
    global _vector_service_instance
    if _vector_service_instance is None:
        _vector_service_instance = VectorService()
    return _vector_service_instance
